"""The model-backed half of DocDrift, built on the OpenMinion 0.1 Python SDK.

Three roles share one OpenMinion session per run:

* triage   - decides whether each deterministic candidate is real drift
* claims   - pulls checkable claims out of prose and verifies them in source
* reviewer - a bounded `subagent` that re-checks every negative verdict

Every role returns Pydantic-validated output (`output_type=`), and all
evidence comes from READ_ONLY tools in `docdrift.tools`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from openminion import (
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
    subagent,
)
from pydantic import BaseModel, Field

from .tools import CTX, EVIDENCE_TOOLS, write_issue_draft


# --------------------------------------------------------------------------
# Structured outputs
# --------------------------------------------------------------------------
class TriageItem(BaseModel):
    candidate_id: str
    verdict: Literal["real_drift", "out_of_scope", "false_positive"]
    reason: str
    evidence: list[str] = Field(default_factory=list)
    suggested_fix: str = ""


class TriageBatch(BaseModel):
    items: list[TriageItem]


class Claim(BaseModel):
    quote: str
    line: int
    verdict: Literal["supported", "contradicted", "unverifiable"]
    evidence: list[str] = Field(default_factory=list)
    suggested_fix: str = ""


class ClaimReport(BaseModel):
    claims: list[Claim]


class Review(BaseModel):
    agree: bool
    reason: str


# --------------------------------------------------------------------------
# Diagnostics: every model turn is recorded so the report can show what
# worked, what failed, and how long it took.
# --------------------------------------------------------------------------
@dataclass
class TurnRecord:
    role: str
    label: str
    ok: bool
    seconds: float
    tool_calls: int
    run_id: str = ""
    error: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    calls: list[str] = field(default_factory=list)


@dataclass
class RunLog:
    session_id: str
    turns: list[TurnRecord] = field(default_factory=list)


def _stats_dict(stats: Any) -> dict[str, Any]:
    if stats is None:
        return {}
    if hasattr(stats, "model_dump"):
        return stats.model_dump()
    if hasattr(stats, "__dict__"):
        return {k: v for k, v in vars(stats).items() if not k.startswith("_")}
    return {"value": str(stats)}


# OpenMinion 0.1.23 answers a user message longer than 12,000 characters with this
# canned text and run_state="completed" instead of raising (see WHAT_WE_LEARNED §7).
CAPACITY_REFUSAL = "could not safely update the task conditions"
MAX_REQUEST_CHARS = 11_500
CAPACITY_ERROR = (
    "task-context capacity refusal: OpenMinion returned its canned 'could not safely update the "
    "task conditions' reply (input over the 12,000-character task limit) as a completed run"
)


def format_reminder(model: type[BaseModel]) -> str:
    schema = json.dumps(model.model_json_schema(), separators=(",", ":"))
    keys = ", ".join(model.model_fields)
    return (
        "OUTPUT FORMAT (mandatory): your final reply is exactly one JSON object with the "
        f"top-level keys {keys}, valid against this JSON Schema. No prose, no Markdown.\n{schema}"
    )


def _real_validation_error(agent: Agent, exc: AgentOutputValidationError) -> str:
    """Report why the recovered JSON failed, not just why the raw text failed.

    OpenMinion strips prose around a JSON object before validating again, but if
    that second attempt fails it re-raises the FIRST error ("Invalid JSON at
    line 1 column 1"), hiding the real schema problem.
    """

    from openminion.api.agent import _extract_json_object  # private; diagnostics only

    raw = exc.raw_text or ""
    obj = _extract_json_object(raw)
    model = getattr(agent, "output_type", None)
    if obj and model is not None:
        try:
            model.model_validate_json(obj)
        except Exception as inner:  # noqa: BLE001
            return f"recovered JSON object failed schema validation: {str(inner)[:400]}"
    if obj is None and "{" in raw:
        return "reply contains '{' but no decodable JSON object (truncated or malformed JSON)"
    return str(exc)[:300]


def _attach_calls(log: "RunLog", before: int) -> None:
    if log.turns:
        log.turns[-1].calls = CTX.calls[before:]


def _run(
    log: RunLog,
    agent: Agent,
    role: str,
    label: str,
    message: str,
    *,
    timeout: float,
    retries: int = 1,
    approval_callback: Callable[[str, dict, str], bool] | None = None,
):
    """Run one turn, retrying once on rate limits or invalid JSON, and record diagnostics."""

    output_type = getattr(agent, "output_type", None)
    if output_type is not None:
        # Instructions land under [IDENTITY] inside a 5-17K char runtime system
        # prompt with its own answer-format contract; the user turn is where the
        # format request actually wins.
        message = f"{message}\n\n{format_reminder(output_type)}"
    original = message
    attempt = 0
    while True:
        attempt += 1
        before = len(CTX.calls)
        started = time.monotonic()
        try:
            result = agent.run(
                message,
                session_id=log.session_id,
                timeout_seconds=timeout,
                approval_callback=approval_callback,
            )
        except ProviderError as exc:
            seconds = time.monotonic() - started
            log.turns.append(
                TurnRecord(role, label, False, seconds, len(CTX.calls) - before, error=f"ProviderError {exc.code}: {exc.message}")
            )
            _attach_calls(log, before)
            if attempt <= retries and "rate" in f"{exc.code} {exc.message}".lower():
                time.sleep(30)
                continue
            return None
        except TurnTimeoutError as exc:
            log.turns.append(TurnRecord(role, label, False, time.monotonic() - started, len(CTX.calls) - before, error=f"TurnTimeoutError: {exc}"))
            _attach_calls(log, before)
            return None
        except AgentOutputValidationError as exc:
            log.turns.append(
                TurnRecord(
                    role,
                    label,
                    False,
                    time.monotonic() - started,
                    len(CTX.calls) - before,
                    error=f"AgentOutputValidationError: {_real_validation_error(agent, exc)}",
                    raw=(exc.raw_text or "")[:8000],
                )
            )
            _attach_calls(log, before)
            if CAPACITY_REFUSAL in (exc.raw_text or ""):
                # A longer repair message would hit the same limit; let the caller split.
                log.turns[-1].error = CAPACITY_ERROR
                return None
            if attempt <= retries:
                # Repair turn: keep the evidence the model already gathered and
                # ask only for the JSON, instead of redoing every tool call.
                repair = (
                    f"{original}\n\nYou already investigated this. Your previous final reply was "
                    f"prose, not JSON. Here it is:\n<<<\n{(exc.raw_text or '')[:6000]}\n>>>\n"
                    "Convert it into the required JSON object now. Do not call tools."
                )
                if len(repair) > MAX_REQUEST_CHARS:
                    return None  # the repair itself would exceed the task-context limit
                message = repair
                continue
            return None
        refused = CAPACITY_REFUSAL in (result.text or "")
        log.turns.append(
            TurnRecord(
                role,
                label,
                not refused,
                time.monotonic() - started,
                len(CTX.calls) - before,
                run_id=str(result.run_id or ""),
                error=CAPACITY_ERROR if refused else "",
                stats=_stats_dict(result.stats),
                raw=(result.text or "")[:1500],
            )
        )
        _attach_calls(log, before)
        return None if refused else result


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
TRIAGE_INSTRUCTIONS = """You are DocDrift's triage reviewer for the OpenMinion documentation.

A deterministic checker compared the docs in a source checkout with the
INSTALLED openminion package and flagged candidates. For each candidate decide:

- real_drift: a reader following this doc with the installed package would hit
  an error, a missing option, or behaviour that differs from what is written.
- out_of_scope: the doc is accurate for its audience but describes the
  repository's own test suite, maintainer scripts, CI, or a source-checkout-only
  workflow, so the installed package is not expected to contain it.
- false_positive: the checker misread the snippet (placeholders, pseudo-code,
  shell syntax, an optional extra that is documented as optional).

Rules:
- Each candidate's `detail` may include deterministic "Source checkout usage"
  facts computed by DocDrift. Trust them: a name used only under tests/,
  scripts/ or .github/ (or built from a prefix constant there) is a setting of
  the repository's own test suite or CI, so the doc is out_of_scope unless the
  page tells end users to set it for the installed package.
- Read the doc around the mention (read_doc) to see who the page is written for
  before deciding.
- Gather evidence with the tools before deciding. Use search_repo_checkout to see
  whether a name lives only under tests/ or scripts/.
- Write each evidence item as "<tool>: <what it showed>".
- suggested_fix is a one-line doc change for real_drift, otherwise "".
- Return one item per candidate id, as JSON matching the schema. No prose."""

CLAIMS_INSTRUCTIONS = """You are DocDrift's claim verifier for the OpenMinion documentation.

You receive one section of a doc, with absolute line numbers. Extract up to
{max_claims} concrete, checkable claims about how the INSTALLED openminion
package behaves: default values, timeouts, limits, setting/flag/env names, which
providers or features are supported, file locations, error codes.
Skip roadmap language, opinions, and claims about external services.

How to search: source code does not contain doc sentences. Search for the
identifiers, setting names, numbers and error strings a claim mentions, for
example 'max_length=128', '12000' (number searches also try '12_000'),
'session_context_token_budget', or a class name. Try at least two different
short queries before calling a claim unverifiable, and open the file around a
hit with read_package_file to confirm.

Verify each claim with the tools against the installed package source:
- supported: you found code that matches the claim.
- contradicted: you found code that disagrees. Quote the disagreeing code.
- unverifiable: you could not locate the relevant code after a real search.

Write each evidence item as "<tool>: <file:line or result>". `line` is the
absolute doc line of the claim. suggested_fix is a one-line doc change for
contradicted claims, otherwise "". Return JSON matching the schema. No prose."""

REVIEWER_INSTRUCTIONS = """You are an independent, skeptical reviewer. Another agent
says the OpenMinion docs disagree with the installed package. Your job is to try
to DISPROVE that before anyone files an issue.

Check at least these alternative explanations with the tools:
1. The name or command belongs to the repository's tests/, scripts/, CI
   (.github/) or a maintainer workflow, not the installed package
   (search_repo_checkout, and look for prefix constants that build names).
2. The doc page is written for contributors running a source checkout
   (read_doc around the mention).
3. The behaviour exists under a different name or module (search_package_source).

Set agree=true only if every alternative is ruled out by your own evidence.
Give a two-sentence reason that cites what you found. Return JSON only."""

ISSUE_INSTRUCTIONS = """You write GitHub issues for the OpenMinion maintainers.
Given one confirmed documentation drift finding, call write_issue_draft exactly
once. Use the finding id as finding_id. The body must contain these Markdown
sections: Summary, Where (doc path and line), Expected (what the doc says),
Actual (what the installed package does, with file:line evidence),
Environment (openminion version, OS), Suggested doc fix. Keep it under 250 words
and do not invent evidence that is not in the finding."""


# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------
@dataclass
class AgentSettings:
    config_path: str
    agent_id: str | None
    timeout: float = 300.0
    pace_seconds: float = 0.0


def with_schema(instructions: str, model: type[BaseModel]) -> str:
    """Put the JSON schema in the prompt.

    OpenMinion 0.1.23's `Agent(output_type=...)` validates the reply after the
    fact but never sends the schema to the provider (api/agent.py
    `_build_payload` vs `_coerce_output`), so the model has to be told.
    """

    schema = json.dumps(model.model_json_schema(), separators=(",", ":"))
    return (
        f"{instructions}\n\nYour FINAL message must be exactly one JSON object that "
        f"validates against this JSON Schema, with no Markdown fences and no prose "
        f"before or after it:\n{schema}"
    )


def _agent(settings: AgentSettings, **kwargs) -> Agent:
    output_type = kwargs.get("output_type")
    if output_type is not None and "instructions" in kwargs:
        kwargs["instructions"] = with_schema(kwargs["instructions"], output_type)
    return Agent(config_path=settings.config_path, agent_id=settings.agent_id, **kwargs)


def triage(settings: AgentSettings, log: RunLog, batches: dict[str, list[dict]], version: str) -> list[TriageItem]:
    items: list[TriageItem] = []
    with _agent(
        settings,
        name="docdrift-triage",
        instructions=TRIAGE_INSTRUCTIONS,
        tools=EVIDENCE_TOOLS,
        output_type=TriageBatch,
    ) as agent:
        for path, candidates in batches.items():
            message = (
                f"Installed openminion version: {version}\nDoc: {path}\n"
                f"Candidates:\n{json.dumps(candidates, indent=2)}"
            )
            result = _run(log, agent, "triage", path, message, timeout=settings.timeout)
            if result is not None:
                known = {c["id"] for c in candidates}
                items.extend(i for i in result.output.items if i.candidate_id in known)
            time.sleep(settings.pace_seconds)
    return items


def verify_claims(settings: AgentSettings, log: RunLog, sections: list[tuple[str, str]], version: str, max_claims: int) -> dict[str, list[Claim]]:
    out: dict[str, list[Claim]] = {}
    with _agent(
        settings,
        name="docdrift-claims",
        instructions=CLAIMS_INSTRUCTIONS.format(max_claims=max_claims),
        tools=EVIDENCE_TOOLS,
        output_type=ClaimReport,
    ) as agent:
        for label, text in sections:
            message = f"Installed openminion version: {version}\nSection: {label}\n\n{text}"
            result = _run(log, agent, "claims", label, message, timeout=settings.timeout)
            if result is not None:
                out[label] = result.output.claims[:max_claims]
            time.sleep(settings.pace_seconds)
    return out


def review(settings: AgentSettings, log: RunLog, findings: list[tuple[str, dict]]) -> dict[str, Review]:
    """Have a bounded subagent re-check each negative verdict independently."""

    verdicts: dict[str, Review] = {}
    if not findings:
        return verdicts
    with _agent(settings, name="docdrift-coordinator") as parent:
        reviewer = subagent(
            parent,
            name="docdrift-reviewer",
            instructions=with_schema(REVIEWER_INSTRUCTIONS, Review),
            tools=EVIDENCE_TOOLS,
            output_type=Review,
            timeout_seconds=int(settings.timeout),
        )
        for key, finding in findings:
            result = _run(log, reviewer, "reviewer", key, json.dumps(finding, indent=2), timeout=settings.timeout)
            if result is not None:
                verdicts[key] = result.output
            time.sleep(settings.pace_seconds)
    return verdicts


def draft_issues(
    settings: AgentSettings,
    log: RunLog,
    findings: list[tuple[str, dict]],
    approval_callback: Callable[[str, dict, str], bool],
) -> list:
    with _agent(
        settings,
        name="docdrift-issue-writer",
        instructions=ISSUE_INSTRUCTIONS,
        tools=[write_issue_draft],
        forced_tools=["write_issue_draft"],
    ) as agent:
        results = []
        for key, finding in findings:
            results.append(
                _run(
                    log,
                    agent,
                    "issue",
                    key,
                    json.dumps({"finding_id": key, **finding}, indent=2),
                    timeout=settings.timeout,
                    retries=0,
                    approval_callback=approval_callback,
                )
            )
            time.sleep(settings.pace_seconds)
        return results
