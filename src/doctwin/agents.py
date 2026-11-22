"""OpenMinion agents for DocTwin: translator, reviewer subagent, glossary keeper.

They reuse DocDrift's turn runner (`docdrift.agents._run`), which carries the
structured-output workarounds and per-turn diagnostics we built there.
"""

from __future__ import annotations

import json
import time
from typing import Callable

from openminion import subagent, tool
from pydantic import BaseModel, Field

from docdrift.agents import AgentSettings, RunLog, _agent, _run, format_reminder, with_schema
from docdrift.tools import CTX

from .glossary import Glossary

# OpenMinion 0.1.23 caps the task objective (the user message) at 12,000
# characters (modules/brain/constants.py TASK_CONTEXT_MAX_CHARS). Longer input is
# answered with a canned "could not safely update the task conditions" reply and
# run_state="completed", so requests are kept below this, schema reminder included.
REQUEST_LIMIT = 11_000
REVIEW_CHARS = 7_000  # source + translation characters per review turn

# --------------------------------------------------------------------------
# Structured outputs
# --------------------------------------------------------------------------


class SectionText(BaseModel):
    key: str
    text: str


class TermProposal(BaseModel):
    source: str
    target: str
    reason: str


class TranslationBatch(BaseModel):
    sections: list[SectionText]
    new_terms: list[TermProposal] = Field(default_factory=list)


class SectionReview(BaseModel):
    key: str
    faithful: bool
    issues: list[str] = Field(default_factory=list)


class ReviewBatch(BaseModel):
    sections: list[SectionReview]


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
GLOSSARY: Glossary | None = None  # set by the sync before any turn runs
# Off for providers whose tool calling is unreliable (see WHAT_WE_LEARNED Part D);
# the relevant glossary entries are in every prompt either way.
USE_TOOLS = True


@tool(min_scope="READ_ONLY", idempotent=True)
def glossary_lookup(term: str) -> str:
    """Look up how a term must be translated. Returns the approved target or 'not in glossary'."""

    CTX.calls.append(f"glossary_lookup({term!r})")
    if GLOSSARY is None:
        return "glossary not loaded"
    for source, entry in GLOSSARY.terms.items():
        if source.lower() == term.strip().lower():
            return f"{source} -> {entry['target']} ({entry.get('note', '')})"
    return "not in glossary"


@tool(description="Add an approved terminology decision to the project glossary file.")
def add_glossary_term(source: str, target: str, reason: str) -> str:
    """Writes the glossary file, so the action policy asks the operator first."""

    CTX.calls.append(f"add_glossary_term({source!r} -> {target!r})")
    if GLOSSARY is None:
        return "glossary not loaded"
    if not source.strip() or not target.strip() or len(source) > 60 or len(target) > 60:
        return "refused: source and target must be 1-60 characters"
    GLOSSARY.add(source.strip(), target.strip(), reason.strip()[:200])
    return f"added {source} -> {target}"


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
LANG_NAMES = {"id": "Indonesian (Bahasa Indonesia)", "es": "Spanish", "pt": "Portuguese (Brazil)", "vi": "Vietnamese", "zh": "Simplified Chinese"}

TRANSLATOR = """You translate software documentation from English into {lang}.

Each input section is Markdown in which code, inline code, URLs and HTML were
replaced by placeholders such as ⟦CODE1⟧, ⟦IC2⟧, ⟦URL3⟧. Rules:

1. Copy every placeholder exactly once, unchanged. Never translate, merge,
   reorder across sentences, or invent placeholders. Do not add code fences.
2. Keep the Markdown structure: same heading level, same number of list items,
   same table rows and columns, same paragraphs.
3. Keep every number exactly as written, including its decimal point: 33.76
   stays 33.76 and 0.0393 stays 0.0393, even where {lang} would normally use a
   decimal comma (readers compare these values with code and logs). Keep
   product names, command names and identifiers.
   Keep quoted program output verbatim in English, for example messages such
   as "Confirmation denied. The action was not run." that a user will see on
   screen exactly like that.
4. Follow the glossary exactly. Use glossary_lookup for any term you are unsure
   about. If an important technical term has no glossary entry, translate it
   sensibly and add it to new_terms with a one-line reason.
5. Write natural, clear, neutral technical {lang} for developers. Prefer short
   sentences. Do not add explanations that are not in the source.
6. When a previous translation of a section is given, keep its wording where
   the source did not change, so readers see a stable text.

Return every input key exactly once."""

REVIEWER = """You are a skeptical bilingual reviewer (English -> {lang}). For each
section, compare the translation with the source and decide whether a developer
reading only the translation would understand exactly what the source says.

Look for: meaning changes, dropped or added sentences, flipped negations
("not", "never", "only", "must", "cannot"), changed conditions or numbers,
wrong technical terms, and mistranslated warnings. Ignore style preferences and
placeholders (⟦...⟧ are code and must not be judged).

Set faithful=false only for real problems a reader could act on wrongly, and
list each problem as a short, concrete issue that quotes the source phrase."""

KEEPER = """You maintain a translation glossary for {lang}. You receive one
proposed term. Call add_glossary_term exactly once with the proposed source and
target and a short reason. A human approves or rejects the write."""


# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------
def _glossary_block(entries: dict[str, dict[str, str]]) -> str:
    if not entries:
        return "(no glossary terms in these sections)"
    return "\n".join(f"- {term} -> {e['target']}" for term, e in sorted(entries.items()))


def translate(
    settings: AgentSettings,
    log: RunLog,
    lang: str,
    label: str,
    items: list[dict],
    glossary_entries: dict[str, dict[str, str]],
    feedback: dict[str, list[str]] | None = None,
) -> TranslationBatch | None:
    """items: [{"key", "text", "previous"?}] with placeholders in place."""

    lang_name = LANG_NAMES.get(lang, lang)
    message = _translate_message(lang_name, label, items, glossary_entries, feedback)
    if len(message) + len(format_reminder(TranslationBatch)) > REQUEST_LIMIT and len(items) > 1:
        mid = len(items) // 2
        first = translate(settings, log, lang, label, items[:mid], glossary_entries, feedback)
        second = translate(settings, log, lang, label, items[mid:], glossary_entries, feedback)
        parts = [b for b in (first, second) if b is not None]
        if not parts:
            return None
        return TranslationBatch(
            sections=[s for b in parts for s in b.sections], new_terms=[t for b in parts for t in b.new_terms]
        )
    with _agent(
        settings,
        name="doctwin-translator",
        instructions=TRANSLATOR.format(lang=lang_name),
        tools=[glossary_lookup] if USE_TOOLS else [],
        output_type=TranslationBatch,
    ) as agent:
        result = _run(log, agent, "translate", label, message, timeout=settings.timeout)
    time.sleep(settings.pace_seconds)
    return result.output if result is not None else None


def _translate_message(lang_name, label, items, glossary_entries, feedback) -> str:
    payload = []
    for item in items:
        entry = {"key": item["key"], "text": item["text"]}
        if item.get("previous"):
            entry["previous_translation"] = item["previous"]
        if feedback and feedback.get(item["key"]):
            entry["fix_these_problems_from_last_attempt"] = feedback[item["key"]]
        payload.append(entry)
    return (
        f"Target language: {lang_name}\nDocument: {label}\n\nGlossary for these sections:\n"
        f"{_glossary_block(glossary_entries)}\n\nSections (JSON):\n{json.dumps(payload, ensure_ascii=False)}"
    )


def review(settings: AgentSettings, log: RunLog, lang: str, label: str, pairs: list[dict]) -> ReviewBatch | None:
    """pairs: [{"key", "source", "translation"}]. Runs as a bounded subagent."""

    lang_name = LANG_NAMES.get(lang, lang)
    message = f"Target language: {lang_name}\nDocument: {label}\n\n{json.dumps(pairs, ensure_ascii=False)}"
    if len(message) + len(format_reminder(ReviewBatch)) > REQUEST_LIMIT:
        return None  # caller splits the batch; nothing is sent
    with _agent(settings, name="doctwin-coordinator", tools=[]) as parent:
        reviewer = subagent(
            parent,
            name="doctwin-reviewer",
            instructions=with_schema(REVIEWER.format(lang=lang_name), ReviewBatch),
            tools=[glossary_lookup] if USE_TOOLS else [],
            output_type=ReviewBatch,
            timeout_seconds=int(settings.timeout),
        )
        result = _run(log, reviewer, "review", label, message, timeout=settings.timeout)
    time.sleep(settings.pace_seconds)
    return result.output if result is not None else None


def propose_terms(
    settings: AgentSettings,
    log: RunLog,
    lang: str,
    proposals: list[TermProposal],
    approval_callback: Callable[[str, dict, str], bool],
) -> None:
    lang_name = LANG_NAMES.get(lang, lang)
    with _agent(
        settings,
        name="doctwin-glossary-keeper",
        instructions=KEEPER.format(lang=lang_name),
        tools=[add_glossary_term],
        forced_tools=["add_glossary_term"],
    ) as agent:
        for p in proposals:
            _run(
                log,
                agent,
                "glossary",
                p.source,
                json.dumps(p.model_dump(), ensure_ascii=False),
                timeout=settings.timeout,
                retries=0,
                approval_callback=approval_callback,
            )
            time.sleep(settings.pace_seconds)
