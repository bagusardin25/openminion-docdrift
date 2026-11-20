# What We Learned

Feedback from building DocTwin and DocDrift on OpenMinion `0.1.23` (PyPI),
Python 3.12, Windows 11, `openai` preset with `gpt-4.1-mini`. Each item gives
what we saw, the evidence, and what we would change. Paths are relative to the
installed `openminion` package unless noted.

**Status key.** *Confirmed*: reproduced, with the cause found in source.
*Observed*: reproduced, but the cause is not fully traced. *Known*: already
reported upstream; we add our data. *Gotcha*: works as documented, but tripped
us up.

---

## Part A · OpenMinion SDK findings

### A1. `Agent(output_type=...)` never tells the model about the schema (Confirmed, not reported upstream yet)

**Seen.** Our first real runs failed with `AgentOutputValidationError` in 2 of
2 claim turns. The model answered in prose or invented its own keys
(`claims_verification` instead of `claims`).

**Why.** `output_type` is used only after the reply comes back
(`api/agent.py:253-284`, `_coerce_output`). `_build_payload`
(`api/agent.py:158-194`) sends no schema and no JSON mode. `instructions` do
reach the provider. We captured the request bodies by wrapping
`ProviderHTTPClient.urlopen`, and the instructions sit under `[IDENTITY]`
inside a 5,278–17,763-character runtime system prompt. That prompt has its own
answer-format contracts ("Tool-calling contract", "provide the full
user-facing final answer and populate the structured confidence…").

| Agent (probe: 2-key JSON) | Schema-valid replies |
| --- | --- |
| no `tools=` | 0 / 4 |
| one `@tool` | 2 / 4 |
| schema repeated in the **user message** (our workaround, `docdrift.agents.format_reminder`) | 13/13 (DocDrift run 1), 9/9 (run 3), 37/38 turns in the DocTwin initial sync |

**Change.** When `output_type` is a Pydantic model, append its JSON Schema as
the last system block or to the final-answer step. Also send the provider's
JSON/schema mode when the profile declares `supports_json`. At minimum,
document that `instructions` must describe the JSON shape.

### A2. `AgentOutputValidationError` hides the real cause (Confirmed, reported as [#803](https://github.com/openminion/openminion/issues/803), fixed by our PR [#810](https://github.com/openminion/openminion/pull/810), merged into `dev` 2026-11-20)

When the raw reply is not JSON, `_coerce_output` recovers the first JSON object
and validates it again. If that also fails, it raises the **first** error.
Replies always start with `"<agent>: "` (A4), so the message always says
`Invalid JSON: expected value at line 1 column 1`. In our case the real cause
was `Field required: claims`.

Fix: keep the recovered object's `ValidationError`.
[`submission/upstream/0001-agent-output-validation-error-cause.patch`](submission/upstream/0001-agent-output-validation-error-cause.patch).
`tests/api/test_agent.py` passes 50/50 with the patch, and the new test fails on
0.1.23. Posted text: [`issue-1`](submission/upstream/issue-1-output-validation-error-cause.md).

### A3. A user message over 12,000 characters returns a canned reply as a *completed* run (Confirmed, reported as [#804](https://github.com/openminion/openminion/issues/804))

`Agent.run()` with a 12,492-character message returns *"I could not safely
update the task conditions. Please restate the current task and its required
conditions."* with `run_state="completed"` and `respond_kind="assistant"`. At
11,492 characters the model answers normally. Callers cannot tell the refusal
from an answer. With `output_type` set it shows up as A2's misleading
`Invalid JSON`.

**Corrected by the maintainer on #804.** We first wrote that the model is never
asked. That is wrong. In the maintainer's controlled test of `runner._decide`,
the provider is called once at both 12,000 and 12,001 characters. For a new
task with no active task context, the runtime then seeds the verbatim message as
the task objective, and `ResolvedTaskContext`'s 12,000-character bound
(`TASK_CONTEXT_MAX_CHARS`, `modules/brain/constants.py:21`;
`modules/brain/schemas/task_context.py:35`) rejects that seed. The turn becomes
`invalid_task_context_update` / clarify, which returns the restate text. This is
not a general SDK input limit: the existing-task and model-update paths differ.
The maintainer asked for a bounded fix that carries a truthful structured
outcome through the API/SDK before output coercion. The issue is open under
maintainer investigation.

This hit DocTwin hard. In our first translation run, 10 of 36 turns failed, and
every failed reply we inspected was this text. The visible symptom matches #719,
but the trigger is different: input length, not an invalid `task_update`.
DocTwin now keeps requests under 11,000 characters, splits batches, sends long
sections in paragraph parts, and treats the canned text as a failure. Posted text:
[`issue-2`](submission/upstream/issue-2-long-input-canned-reply.md).

Separately (*Observed*): 1 of 38 turns in a later run got the same canned reply
for a 6,066-character message. We could not reproduce it in a one-session
versus fresh-session probe. That fits #719's random trigger.

### A4. `result.text` starts with `"<agent_id>: "` (Known: #567)

`services/brain/post_execution/postprocess_response.py:276` builds
`f"{agent_name}: {response_text}"`, and that prefix reaches
`AgentRunResult.text` even with `deliver: False`. #567 reported this on 0.1.17.
It is still present in 0.1.23.

### A5. A one-tool question costs about 7 provider calls (Observed; related #777)

A wire capture of one `Agent.run("What is the hex code of teal?")` with one
`@tool` counted 7 HTTP requests: tool-contract turn, freshness classifier,
tool-result continuations, confidence/final composition, closing identity turn.
Without tools it was 2. #777 measures the same redundancy. For DocTwin this is
the main cost driver: a ~6,000-character translation turn takes about 60 s.

### A6. `tools=None` still exposes the runtime's default tools (Gotcha; #269 closed)

This is documented (`docs/runtime-surfaces.md:55`). But a pure
structured-output agent still gets the tool-calling contract in its system
prompt, and in our probe that contract competed with the output format.
DocTwin passes explicit tool lists everywhere, `[]` included.

### A7. `OPENMINION_TRACE_REQUESTS=1` wrote no trace files for SDK runs (Observed)

The flag resolves `True` from the process environment, but a full `Agent.run()`
wrote no `*-http.json` file anywhere we looked (`OPENMINION_HOME`, the trace
dir, `~/.openminion`, temp). The transport passes `env=env_owner`
(`modules/llm/providers/transport/http.py`), not the process env. We did not
confirm whether that is the cause.

### A8. No SDK-level memory API for a small, scoped fact store (Design feedback)

We wanted the glossary in OpenMinion memory. The public `MemoryBundle` is a
portability format (`modules/memory/portability/`). We found no `Agent`-level
way to write a scoped fact ("`library` → `library`") and read it back
deterministically in later runs. DocTwin keeps the glossary as a reviewable
JSON file, changed only through an approval-gated `@tool`. A
`agent.memory.put/get(namespace, key)` facade would let apps like this use
OpenMinion memory instead of a side file.

---

## Part B · Lessons for building reliable agents on OpenMinion

**B1. One model reviewing itself rubber-stamps.** In DocDrift run 1 the triage
agent called 4 of 5 env-var candidates `real_drift`, and the reviewer subagent
(same model) confirmed all 4. All 4 were wrong: the variables live in `tests/`
or `.github/`, or are built from a prefix constant
(`tests/e2e/runners/run_blockchain_testnet_write.py:38`). Two changes fixed it:
deterministic facts handed to the model (where each name is used), and a
reviewer told to *disprove*. After that, 5/5 were correct in runs 2 and 3.

**B2. Models search source code for doc sentences.** The claims agent marked
"at most 128 conditions and a 12000-character content limit" *unverifiable*.
Its queries were whole sentences, and `12000` never matches `12_000`. Number
searches now also try the underscore form, and a sentence-shaped query that
misses returns a hint. With `gpt-4.1-mini`, claim selection still varies from
run to run.

**B3. Translation needs hard gates, not trust.** What the gates and checks
caught in DocTwin's real runs:
- the model dropping a section's trailing newline, which glued the next heading
  onto a paragraph (`…surface.### 3. API runtime`). Whitespace around every
  section is now restored from the source;
- **decimal points localized** (`33.76` → `33,76`) in a table of measurements.
  The number gate rejected it and the section stayed in English instead of
  shipping changed values. The prompt now says to keep decimal points;
- "Library callers" translated as "Pemanggil *perpustakaan*" (a building). A
  glossary entry (`library` → `library`) plus the glossary gate now block it;
- a section left out of the model's batch output twice. It now gets one solo
  attempt.

**B4. A failed reviewer must not mean "approved".** Early on, a review turn
that failed (A3) left its sections accepted *unreviewed* but reported as
"translated". DocTwin now splits failed review batches down to single units and
records any unit still without a verdict as `unreviewed`. The next sync
re-runs only the reviewer for those.

**B6. Protection rules need tests on real docs, not just on toy strings.**
Reading the published preview by eye, we found English leaking into a
translation: `` `agent.run("yes",⏎ thread_id=…)` `` is inline code that wraps
onto a second line. Our single-line inline-code pattern instead paired the
backticks around `; a plain later `, so that prose was "protected" and never
translated. The gates could not see it, because every placeholder was in place.
We fixed the pattern, added a regression test, and wrote
`scripts/invalidate_protect_change.py`, which found exactly the 2 affected
sections and queued them for re-translation. The same review found that quoted
program output (`"Confirmation denied. The action was not run."`) was being
translated, even though users see it in English. Straight-quoted full
sentences are now protected too. The reviewer subagent also lets through
literal word choices a native speaker would fix (for example "address one agent"
→ "alamat satu agent"). Gates catch structure, not style.

**B5. "Supported" is weaker than it looks.** DocDrift's claims agent sometimes
backs a claim with loose evidence, for example the same line for five different
defaults. Only `contradicted` verdicts are escalated, so this never creates
false issues. Even so, "supported" means no contradiction was found, not that
the claim is proven.

---

## Part C · What worked well

- **Permissions and approval.** `READ_ONLY` + `idempotent` tools never prompted.
  Default-scope write tools (`add_glossary_term`, `write_issue_draft`) always
  reached `approval_callback`. `docdrift approval-check` passed 6/6 (deny → no
  file and "Confirmation denied. The action was not run."; approve → written).
- **`subagent`** gave the reviewer its own instructions, tools, output type and
  timeout in one call.
- **Provider setup.** `openminion setup --provider openai` stored only
  `api_key_env`; no file under `.openminion/` contains the key. Switching to
  Gemini or Cortensor Portal is config-only.
- **Diagnostics.** `ProviderError`, `TurnTimeoutError`, `run_id` and `stats`
  were enough for a per-turn diagnostics table in every report.
- **Docs quality.** All 145 shell and 20 Python snippets in the v0.1.23 docs
  match the installed CLI and package (DocDrift).

---

## Runs

### DocTwin (Bahasa Indonesia, 7 OpenMinion doc files)

| Run | Source | Sections | Sent to the model | Result | Turns OK | Model time |
| --- | --- | --- | --- | --- | --- | --- |
| initial (before the A3 fixes) | v0.1.18 | 47 | 47 | 46 translated, but sections in 4 chunks were never reviewed (B4) | 26/36 | 19 min |
| initial (fixed) | v0.1.18 | 47 | 47 | 45 translated, 2 kept in English (decimal commas; a section the model dropped twice) | 37/38 | 19.4 min |
| update | v0.1.18 → v0.1.23 | 54 | 14 | 14 translated, 40 reused, 0 need review, 0 in English; the 2 sections refused before now pass | 30/33 (all 3 failures recovered by retries) | 11.0 min |
| fix | v0.1.23 | 54 | 3 | re-translated the 2 sections hit by the inline-code bug (B6), then 1 more for quoted program output | all OK | ~2 min |

Code blocks were byte-identical to the source in every file of every run, and
DocDrift found no broken command or import in the output. Heading counts
matched the source in all 7 files.

**Cost note.** All runs together used about 5.1 million tokens on
`gpt-4.1-mini` (OpenAI usage page). The main reason is A5: every `Agent.run`
turns into ~7 provider calls, each carrying a 5,000–17,000-character runtime
system prompt. Debugging runs did the rest. For anyone budgeting a similar
project: a translation turn costs roughly 20–40k tokens regardless of how short
the text is. `brain.auto_fact_extraction.enabled: false`
(`docs/turn-budgets.md`) removes one of those calls.

### DocDrift (OpenMinion docs v0.1.23 vs installed 0.1.23)

| Run | Change | Triage (5 candidates) | Claims (supported / contradicted / unverifiable) | Turns OK |
| --- | --- | --- | --- | --- |
| 1 | baseline | 4 wrong `real_drift`, all confirmed by the reviewer | 13 / 0 / 6 | 17/17 |
| 2 | usage facts + skeptical reviewer | 5/5 correct `out_of_scope` | 10 / 0 / 9 | 9/10 |
| 3 | better search tools and prompt | 5/5 correct | 16 / 0 / 3 | 9/9 |

Against older installs, the same docs show real drift: 0.1.15 lacks
`HTTPTransport` (`docs/a2a-remote.md:72`), and 0.1.10 also lacks
`openminion tasks show --runs-limit` (`docs/system-operations.md:215`).
Archived reports: [`out/history/`](out/history/).
