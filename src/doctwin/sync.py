"""Incremental translation sync: only changed sections reach the model.

Work is done in *units*: a section, or a paragraph group of a large section.
Every request stays well under OpenMinion's 12,000-character task-context
limit, because longer user messages come back as a canned "could not safely
update the task conditions" reply instead of an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from docdrift.agents import AgentSettings, RunLog

from . import agents, gates
from .glossary import Glossary
from .ledger import Ledger, SectionState, sha
from .segment import PLACEHOLDER, Protected, Section, protect, split_sections

DEFAULT_FILES = (
    "README.md",
    "docs/getting-started.md",
    "docs/runtime-surfaces.md",
    "docs/turn-budgets.md",
    "docs/provider-capabilities.md",
    "docs/configuration-compatibility.md",
    "examples/sdk/README.md",
)
WORD = re.compile(r"\w+")
FENCED = re.compile(r"^(\s*)(`{3,}|~{3,}).*?^\1\2\s*$", re.MULTILINE | re.DOTALL)
REVIEW_MARK = "<!-- doctwin: needs review -->"
PART_CHARS = 2800  # sections longer than this are split at blank lines
CHUNK_CHARS = 5200  # source + previous translation per translation turn


@dataclass
class SectionOutcome:
    file: str
    key: str
    action: str  # unchanged | copied | translated | needs_review | unreviewed | source_fallback | reviewed
    attempts: int = 0
    gate_errors: list[str] = field(default_factory=list)
    review_issues: list[str] = field(default_factory=list)
    words: int = 0
    parts: int = 1


@dataclass
class FileOutcome:
    file: str
    status: str  # written | unchanged | human_edited | missing_source | dry_run
    sections: int = 0
    removed: list[str] = field(default_factory=list)
    code_blocks_identical: bool | None = None


@dataclass
class SyncResult:
    lang: str
    source_ref: str
    files: list[FileOutcome] = field(default_factory=list)
    sections: list[SectionOutcome] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    glossary_added: list[str] = field(default_factory=list)


def _words(text: str) -> int:
    return len(WORD.findall(PLACEHOLDER.sub(" ", text)))


def _has_prose(section: Section) -> bool:
    return bool(re.search(r"[A-Za-z]{2}", PLACEHOLDER.sub(" ", protect(section.text).text)))


def _split_ws(text: str) -> tuple[str, str, str]:
    body = text.strip()
    if not body:
        return text, "", ""
    start = text.index(body[0])
    return text[:start], body, text[start + len(body):]


def _units(section_key: str, text: str) -> list[dict]:
    """Split a protected section into paragraph groups of at most PART_CHARS."""

    if len(text) <= PART_CHARS:
        groups = [text]
    else:
        pieces = re.split(r"(\n{2,})", text)
        groups, buf = [], ""
        for i in range(0, len(pieces), 2):
            para = pieces[i] + (pieces[i + 1] if i + 1 < len(pieces) else "")
            if buf and len(buf) + len(para) > PART_CHARS:
                groups.append(buf)
                buf = ""
            buf += para
        if buf:
            groups.append(buf)
    units = []
    for n, group in enumerate(groups, 1):
        lead, body, trail = _split_ws(group)
        key = section_key if len(groups) == 1 else f"{section_key}::p{n}"
        units.append({"key": key, "section": section_key, "text": body, "lead": lead, "trail": trail})
    return units


def _chunks(units: list[dict], max_chars: int) -> list[list[dict]]:
    out: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for unit in units:
        cost = len(unit["text"]) + len(unit.get("previous", ""))
        if current and size + cost > max_chars:
            out.append(current)
            current, size = [], 0
        current.append(unit)
        size += cost
    if current:
        out.append(current)
    return out


def _code_blocks(text: str) -> list[str]:
    return [m.group(0) for m in FENCED.finditer(text)]


def sync(
    *,
    source: Path,
    source_ref: str,
    out: Path,
    lang: str,
    files: list[str],
    settings: AgentSettings,
    log: RunLog,
    approve_term: Callable[[str, dict, str], bool] | None,
    max_chars: int = CHUNK_CHARS,
    dry_run: bool = False,
    force: bool = False,
    max_chunks: int | None = None,
    progress: Callable[[str], None] = print,
) -> SyncResult:
    ledger = Ledger.load(out / ".doctwin" / "ledger.json", lang)
    glossary = Glossary.load(out / f"glossary.{lang}.json", lang)
    agents.GLOSSARY = glossary
    result = SyncResult(lang=lang, source_ref=source_ref)
    proposals: dict[str, agents.TermProposal] = {}
    budget = {"chunks": 0, "max": max_chunks}

    for file in files:
        src_path = source / file
        if not src_path.exists():
            result.files.append(FileOutcome(file, "missing_source"))
            continue
        markdown = src_path.read_text(encoding="utf-8")
        sections = split_sections(markdown)
        out_path = out / file
        recorded = ledger.files.get(file, {}).get("written_digest", "")
        if out_path.exists() and recorded and sha(out_path.read_text(encoding="utf-8")) != recorded and not force:
            progress(f"  {file}: the translated file was edited by a human since the last sync; leaving it alone (use --force)")
            result.files.append(FileOutcome(file, "human_edited", len(sections)))
            continue

        protected = {s.key: protect(s.text) for s in sections}
        work: list[dict] = []
        review_only: list[Section] = []
        for s in sections:
            state = ledger.section(file, s.key)
            same_source = bool(state and state.source_digest == s.digest)
            if same_source and state.status == "ok":
                result.sections.append(SectionOutcome(file, s.key, "unchanged", words=_words(protected[s.key].text)))
                continue
            if same_source and state.status == "unreviewed":
                review_only.append(s)
                continue
            if not _has_prose(s):
                ledger.put(file, s.key, SectionState(s.digest, s.text, "ok", ["no prose; copied"]))
                result.sections.append(SectionOutcome(file, s.key, "copied"))
                continue
            units = _units(s.key, protected[s.key].text)
            if state and len(units) == 1:
                previous = protect(state.text.replace(REVIEW_MARK + "\n", "")).text.strip()
                if len(previous) + len(units[0]["text"]) <= max_chars:
                    units[0]["previous"] = previous
            work.extend(units)

        n_sections = len({u["section"] for u in work})
        progress(
            f"  {file}: {len(sections)} sections, {n_sections} to translate"
            f"{f' ({len(work)} parts)' if len(work) != n_sections else ''}, {len(review_only)} to re-review, "
            f"{len(sections) - n_sections - len(review_only)} reused"
        )
        unit_state = UnitResults()
        units_of: dict[str, list[dict]] = {}
        for unit in work:
            units_of.setdefault(unit["section"], []).append(unit)
        finalized: set[str] = set()
        by_key = {s.key: s for s in sections}
        for chunk in _chunks(work, max_chars):
            if budget["max"] is not None and budget["chunks"] >= budget["max"]:
                progress("  chunk budget reached; remaining sections stay as they were")
                break
            budget["chunks"] += 1
            _translate_chunk(file, chunk, glossary, settings, log, lang, unit_state, proposals, progress)
            # A large section can span chunks: finalize it only when all of its parts are done.
            for section_key, units in units_of.items():
                if section_key not in finalized and all(u["key"] in unit_state.attempts for u in units):
                    _finalize(file, by_key[section_key], units, protected[section_key], unit_state, ledger, result)
                    finalized.add(section_key)
            ledger.source_ref = source_ref
            if not dry_run:
                ledger.save()  # survive interruptions between chunks
        if review_only:
            _review_existing(file, review_only, protected, ledger, settings, log, lang, result, progress)

        removed = ledger.prune(file, {s.key for s in sections})
        assembled = []
        for s in sections:
            state = ledger.section(file, s.key)
            assembled.append(state.text if state and state.source_digest == s.digest else s.text)
        text = "".join(assembled)
        identical = _code_blocks(text) == _code_blocks(markdown)
        if dry_run:
            status = "dry_run"
        elif out_path.exists() and out_path.read_text(encoding="utf-8") == text:
            status = "unchanged"
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            status = "written"
        if not dry_run:
            ledger.files.setdefault(file, {"written_digest": "", "sections": {}})["written_digest"] = sha(text)
        result.files.append(FileOutcome(file, status, len(sections), removed, identical))

    known = {t.lower() for t in glossary.terms}
    new_terms = [p for k, p in proposals.items() if k.lower() not in known]
    result.proposals = [p.model_dump() for p in new_terms]
    if new_terms and approve_term is not None and not dry_run:
        before = set(glossary.terms)
        progress(f"  glossary: {len(new_terms)} proposed term(s); each addition needs your approval")
        agents.propose_terms(settings, log, lang, new_terms, approve_term)
        reloaded = Glossary.load(glossary.path, lang)
        result.glossary_added = sorted(set(reloaded.terms) - before)

    ledger.source_ref = source_ref
    if not dry_run:
        ledger.save()
    return result


def _review_units(settings, log, lang, label, pairs: list[dict]) -> dict[str, agents.SectionReview]:
    """Review in batches that fit the request limit; split a failed batch until single units."""

    verdicts: dict[str, agents.SectionReview] = {}
    queue = [pairs]
    while queue:
        batch = queue.pop(0)
        size = sum(len(p["source"]) + len(p["translation"]) for p in batch)
        if len(batch) > 1 and size > agents.REVIEW_CHARS:
            mid = len(batch) // 2
            queue[:0] = [batch[:mid], batch[mid:]]
            continue
        verdict = agents.review(settings, log, lang, label, batch)
        if verdict is None:
            if len(batch) > 1:
                mid = len(batch) // 2
                queue[:0] = [batch[:mid], batch[mid:]]
            continue  # a single unit that cannot be reviewed stays unreviewed
        keys = {p["key"] for p in batch}
        for r in verdict.sections:
            if r.key in keys:
                verdicts[r.key] = r
    return verdicts


@dataclass
class UnitResults:
    """Per-file results for translation units, collected across chunks."""

    attempts: dict[str, int] = field(default_factory=dict)
    accepted: dict[str, str] = field(default_factory=dict)
    gate_errors: dict[str, list[str]] = field(default_factory=dict)
    verdicts: dict = field(default_factory=dict)
    issues: dict[str, list[str]] = field(default_factory=dict)


def _translate_chunk(file, chunk, glossary, settings, log, lang, state: UnitResults, proposals, progress):
    names = []
    for u in chunk:
        name = u["section"].split("#")[0].split("/")[-1] + (f"::{u['key'].split('::')[1]}" if "::" in u["key"] else "")
        names.append(name)
    label = f"{file} [{', '.join(names)}]"
    entries: dict[str, dict] = {}
    for unit in chunk:
        entries.update(glossary.terms_in(unit["text"]))

    attempts = {u["key"]: 0 for u in chunk}
    gate_errors: dict[str, list[str]] = {}
    accepted: dict[str, str] = {}
    pending = list(chunk)
    feedback: dict[str, list[str]] = {}
    for _ in range(2):  # first try + one retry with concrete feedback
        if not pending:
            break
        batch = agents.translate(settings, log, lang, label, pending, entries, feedback or None)
        returned = {s.key: s.text for s in batch.sections} if batch else {}
        if batch:
            for p in batch.new_terms:
                proposals.setdefault(p.source.strip(), p)
        still = []
        for unit in pending:
            key = unit["key"]
            attempts[key] += 1
            text = returned.get(key)
            errors = ["missing from the model's output"] if text is None else gates.check(Protected(unit["text"]), text.strip(), glossary)
            if errors:
                gate_errors[key] = errors
                feedback[key] = errors
                still.append(unit)
            else:
                gate_errors.pop(key, None)
                accepted[key] = text.strip()
        pending = still

    # A unit the model left out of a batch twice gets one attempt on its own.
    for unit in [u for u in pending if gate_errors.get(u["key"]) == ["missing from the model's output"]]:
        key = unit["key"]
        solo = agents.translate(settings, log, lang, f"{label} (solo {key.split('#')[0].split('/')[-1]})", [unit], entries, None)
        attempts[key] += 1
        text = next((s.text for s in solo.sections if s.key == key), None) if solo else None
        errors = ["missing from the model's output"] if text is None else gates.check(Protected(unit["text"]), text.strip(), glossary)
        if errors:
            gate_errors[key] = errors
        else:
            gate_errors.pop(key, None)
            accepted[key] = text.strip()

    pairs =[{"key": k, "source": u["text"], "translation": accepted[k]} for u in chunk if (k := u["key"]) in accepted]
    verdicts = _review_units(settings, log, lang, label, pairs) if pairs else {}
    issues = {k: (v.issues or ["reviewer flagged without detail"]) for k, v in verdicts.items() if not v.faithful}

    if issues:  # one repair attempt for units the reviewer rejected
        retry = [dict(u, previous=accepted[u["key"]]) for u in chunk if u["key"] in issues]
        batch = agents.translate(settings, log, lang, label + " (review fix)", retry, entries, issues)
        if batch:
            fixed = {s.key: s.text for s in batch.sections}
            recheck = []
            for unit in retry:
                key = unit["key"]
                attempts[key] += 1
                text = (fixed.get(key) or "").strip()
                if text and not gates.check(Protected(unit["text"]), text, glossary):
                    accepted[key] = text
                    recheck.append({"key": key, "source": unit["text"], "translation": text})
            for key, v in _review_units(settings, log, lang, label + " (recheck)", recheck).items():
                verdicts[key] = v
                if v.faithful:
                    issues.pop(key, None)
                else:
                    issues[key] = v.issues or issues[key]

    state.attempts.update(attempts)
    state.accepted.update(accepted)
    state.gate_errors.update(gate_errors)
    state.verdicts.update(verdicts)
    state.issues.update(issues)
    done = sum(1 for k in attempts if k in accepted)
    progress(
        f"    {label}: {done}/{len(chunk)} accepted, {len(issues)} need review, "
        f"{sum(1 for p in pairs if p['key'] not in verdicts)} unreviewed, {len(chunk) - done} kept in English"
    )


def _finalize(file, section, units, protected_section, state: UnitResults, ledger, result):
    """Write one section to the ledger once every one of its parts has been processed."""

    keys = [u["key"] for u in units]
    words = sum(_words(u["text"]) for u in units)
    tries = max(state.attempts.get(k, 0) for k in keys)
    if all(k in state.accepted for k in keys):
        body = "".join(u["lead"] + state.accepted[u["key"]] + u["trail"] for u in units)
        restored = protected_section.restore(body)
        unit_issues = [i for k in keys for i in state.issues.get(k, [])]
        unreviewed = [k for k in keys if k not in state.verdicts]
        if unit_issues:
            marked = _mark(restored, bool(section.heading))
            ledger.put(file, section.key, SectionState(section.digest, marked, "needs_review", unit_issues))
            action = "needs_review"
        elif unreviewed:
            ledger.put(file, section.key, SectionState(section.digest, restored, "unreviewed", ["reviewer returned no verdict"]))
            action = "unreviewed"
        else:
            ledger.put(file, section.key, SectionState(section.digest, restored, "ok"))
            action = "translated"
        result.sections.append(SectionOutcome(file, section.key, action, tries, [], unit_issues, words, len(units)))
    else:
        errs = [e for k in keys for e in state.gate_errors.get(k, ["not translated in this run"])]
        ledger.put(file, section.key, SectionState(section.digest, section.text, "source_fallback", errs))
        result.sections.append(SectionOutcome(file, section.key, "source_fallback", tries, errs, [], words, len(units)))


def _review_existing(file, sections, protected, ledger, settings, log, lang, result, progress):
    """Re-run only the reviewer for translations that were never reviewed."""

    pairs = []
    for s in sections:
        state = ledger.section(file, s.key)
        pairs.append({"key": s.key, "source": protected[s.key].text.strip(), "translation": protect(state.text).text.strip()})
    verdicts = _review_units(settings, log, lang, f"{file} (re-review)", pairs)
    for s in sections:
        state = ledger.section(file, s.key)
        v = verdicts.get(s.key)
        if v is None:
            result.sections.append(SectionOutcome(file, s.key, "unreviewed", 0, [], ["reviewer returned no verdict"]))
            continue
        if v.faithful:
            state.status, state.notes = "ok", []
            result.sections.append(SectionOutcome(file, s.key, "reviewed"))
        else:
            state.status, state.notes = "needs_review", v.issues
            state.text = _mark(state.text, bool(s.heading))
            result.sections.append(SectionOutcome(file, s.key, "needs_review", 0, [], v.issues))
        ledger.put(file, s.key, state)
    progress(f"    {file}: re-reviewed {len(verdicts)}/{len(sections)}")


def _mark(text: str, has_heading: bool) -> str:
    if not has_heading:
        return f"{REVIEW_MARK}\n{text}"
    first, _, rest = text.partition("\n")
    return f"{first}\n{REVIEW_MARK}\n{rest}"
