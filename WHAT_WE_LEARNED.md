# What We Learned

Feedback from building DocTwin and DocDrift on OpenMinion `0.1.23` (PyPI),
Python 3.12, Windows 11, `openai` preset with `gpt-4.1-mini`. Each item gives
what we saw, the evidence, and what we would change. Paths are relative to the
installed `openminion` package unless noted.

**Status key.** *Confirmed*: reproduced, with the cause found in source.
*Observed*: reproduced, but the cause is not fully traced. *Known*: already
reported to OpenMinion; we add our data. *Caveat*: works as documented, but
surprised us.

**Terms.** A *turn* is one `Agent.run` call. A *canned reply* is a fixed text
built into OpenMinion that comes back instead of a model answer. *Upstream*
means the OpenMinion project, and numbers like #719 are issues in its GitHub
repository.

## The short version

What we would change, most useful first:

1. **Send the `output_type` schema to the model** (A1, upstream #853). Today the
   schema is only used to check the reply afterwards.
2. **Report the real validation error** (A2). Done: our fix shipped in
   openminion 0.1.24.
3. **Do not return a refused turn as a `completed` run** (A3, upstream #804).
   Callers cannot tell the canned text from an answer.
4. **Make a tool turn cheaper** (A5). One question with one tool costs about 7
   provider calls.
5. **Offer a small scoped memory API** (A8), so apps like this do not need a
   side file.
6. **Portal: answer schema-invalid tool arguments with a 4xx, not a 502**, and
   look at the multi-minute stalls (Part D).

What worked with no workaround at all is in Part C.

---

## Part A · OpenMinion SDK findings

### A1. `Agent(output_type=...)` never tells the model about the schema (Confirmed; tracked upstream as [#853](https://github.com/openminion/openminion/issues/853))

**Seen.** Our first real runs failed with `AgentOutputValidationError` in 2 of
2 claim turns. The model answered in prose or invented its own keys
(`claims_verification` instead of `claims`).

**Why.** `output_type` is used only after the reply comes back
(`api/agent.py:253-284`, `_coerce_output`). `_build_payload`
(`api/agent.py:158-194`) sends no schema and no JSON mode. `instructions` do
reach the provider, but inside a much longer system prompt that the runtime
builds (5,278 to 17,763 characters), under the heading `[IDENTITY]`. We saw
this by wrapping `ProviderHTTPClient.urlopen` to capture the request bodies.
That prompt has its own
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

### A2. `AgentOutputValidationError` hides the real cause (Confirmed; reported as [#803](https://github.com/openminion/openminion/issues/803), fixed by our PR [#810](https://github.com/openminion/openminion/pull/810))

Our fix was merged into OpenMinion's `dev` branch on 2026-11-20 and released
in 0.1.24 (see below).

When the raw reply is not JSON, `_coerce_output` recovers the first JSON object
and validates it again. If that also fails, it raises the **first** error.
Replies always start with `"<agent>: "` (A4), so the message always says
`Invalid JSON: expected value at line 1 column 1`. In our case the real cause
was `Field required: claims`.

Fix: keep the recovered object's `ValidationError`.
[`upstream/0001-agent-output-validation-error-cause.patch`](upstream/0001-agent-output-validation-error-cause.patch).
`tests/api/test_agent.py` passes 50/50 with the patch, and the new test fails on
0.1.23. Posted text: [`issue-1`](upstream/issue-1-output-validation-error-cause.md).

**Released and verified.** openminion 0.1.24 on PyPI (2026-11-21) contains the fix. We ran
the maintainer's acceptance controls on the installed packages with a controlled
runtime ([`upstream/verify_803_release.py`](upstream/verify_803_release.py)): on 0.1.23
a schema-invalid reply that starts with the agent prefix still reports
`json_invalid`, and on 0.1.24 it reports the missing field. The other four test
cases (a schema-invalid reply without the prefix, a non-JSON reply, and two
valid replies) give the same result on both versions. Posted on #803:
[`upstream/issue-1-release-check.md`](upstream/issue-1-release-check.md).

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
not a general SDK input limit: when a task already exists, or when the model
writes the task update, a different code path runs.
The maintainer asked for a bounded fix that carries a truthful structured
outcome through the API/SDK before output coercion. The issue is open under
maintainer investigation. We re-checked through the SDK on current `dev` with a
controlled provider and posted a bounded proposal
([`upstream/issue-2-followup-proposal.md`](upstream/issue-2-followup-proposal.md)).

This hit DocTwin hard. In our first translation run, 10 of 36 turns failed, and
every failed reply we inspected was this text. #719 reports the same canned
reply, but with a different trigger: an invalid `task_update`, not input length.
DocTwin now keeps requests under 11,000 characters, splits batches, sends long
sections in paragraph parts, and treats the canned text as a failure. Posted text:
[`issue-2`](upstream/issue-2-long-input-canned-reply.md).

Separately (*Observed*): 1 of 38 turns in a later run got the same canned reply
for a 6,066-character message. We could not reproduce it in a one-session
versus fresh-session probe. That fits #719's random trigger. It happened once
more in the sync recorded for the demo video: the first attempt at one short
section got the canned reply, and the retry passed
([`demo/logs/sync-report.md`](demo/logs/sync-report.md)).

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

### A6. `tools=None` still exposes the runtime's default tools (Caveat; #269 closed)

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

**B1. One model reviewing itself approves everything.** In DocDrift run 1 the triage
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

**B5. "Supported" is weaker than it looks.** DocDrift's claims agent sometimes
backs a claim with loose evidence, for example the same line for five different
defaults. Only `contradicted` verdicts are escalated, so this never creates
false issues. Even so, "supported" means no contradiction was found, not that
the claim is proven.

**B6. Protection rules need tests on real docs, not just on toy strings.**
Reading the published preview by eye, we found English leaking into a
translation. In the source, the inline code `agent.run("yes", thread_id=…)`
is split across two lines. Our pattern for inline code only looked within one
line, so it missed it and matched a later pair of backticks around ordinary
prose instead. That prose was "protected" and never translated. The gates could not see it, because every placeholder was in place.
We fixed the pattern, added a regression test, and wrote
`scripts/invalidate_protect_change.py`, which found exactly the 2 affected
sections and queued them for re-translation. The same review found that quoted
program output (`"Confirmation denied. The action was not run."`) was being
translated, even though users see it in English. Straight-quoted full
sentences are now protected too. The reviewer subagent also lets through
literal word choices a native speaker would fix (for example "address one agent"
→ "alamat satu agent"). Gates catch structure, not style.

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

## Part D · Cortensor Portal (hosted inference) findings

Tested 2026-11-21 and 2026-11-23 with a free-plan Portal account, OpenMinion 0.1.23, preset
`cortensor-portal` (profile `docdrift-portal`). Setup followed the Portal's own
in-app Quick start (`portal.cortensor.network/portal/docs`).

**What the Portal docs say today.** Base URL `https://api.cortensor.app`. The
OpenAI route is `POST /v1/chat/completions` and the Anthropic route is
`POST /v1/messages`. Auth is `Authorization: Bearer ctp_…`. Aliases: `gemma4`
(Gemma 4 E4B), `oss-20b` (the launch model), `qwen` (Qwen 3.5 9B), and
`oss-120b`, which is listed as "supported, no capacity" and rejects live
requests. Compatibility routes are "text-only requests today". The free plan
uses rolling 2-hour and 7-day windows; the Usage page first showed enforced
token caps of 200,000 per 2 h and 2,000,000 per 7 days, and later "cap not
published yet". Request counts (100 per 2 h, 1,000 per 7 days) are recorded,
not enforced.

**Direct API checks (small requests, no OpenMinion).** All on `oss-20b`:

| Request | Result | Latency |
| --- | --- | --- |
| plain chat, `max_tokens: 16` | 200, `finish_reason: length`, **empty content** (the reasoning model spent all 16 tokens before answering) | 17.4 s |
| one tool, `tool_choice` auto | 200, `finish_reason: tool_calls`, 1 tool call | 19.9 s |
| forced named `tool_choice` | 200, 1 tool call | 24.9 s |
| 5,000-char system prompt, `max_tokens: 512` | 200, 1 tool call, 1,111 prompt tokens | 35.1 s |
| same, no `max_tokens` | 200, 1 tool call | 23.1 s |

Native tool calling works, including forced `tool_choice`. "Text-only" means
no multimodal input, not "no tools". Successful responses carry an
`x-request-id` (`gw-…`).

**OpenMinion on Portal (one `Agent.run` with one `@tool` and `output_type`).**

| Run | Provider requests | Outcome |
| --- | --- | --- |
| 1 | 1: stalled 478.5 s, then "Server disconnected without sending a response" | `TurnTimeoutError` at the 480 s turn budget |
| 2 | 4: **502 Bad Gateway** (39.0 s), 200 (40.0 s), 200 (89.4 s), read timeout (310.2 s) | `TurnTimeoutError` at 480 s |
| 3 | `brain.auto_fact_extraction.enabled: false` and a 900 s turn timeout. Only 1 request this time (the extraction call is gone), but it stalled 481.7 s | `ProviderError: TIMEOUT` (the provider's 480 s read timeout) |
| 4 | same, plus `http_connection_reuse_enabled: false` and a 900 s provider timeout. No stall: the turn ended at 76.1 s | `ProviderError`: Portal returned **HTTP 502 "Model tool arguments do not match the advertised schema."** (`gw-743094d3-…`) |
| 5 | same settings, model `gemma4`. No stall: the turn ended at 60.1 s | the canned "could not safely update the task conditions" reply. This is OpenMinion #719's trigger (an invalid optional `task_update` from a smaller model), reproduced here on Portal with `gemma4` |
| 6 | `gemma4` with **no tools** (`tools=[]`), glossary in the prompt. The turn ended at 120.0 s | invalid output: the model answered in prose ("I will use the web search tool…"), even though no tool was offered |
| 7 | `oss-20b`, no tools, connection reuse off, 900 s provider timeout | **stalled 904.1 s**, then `ProviderError` (read timeout). So stalls also happen without connection reuse |
| 8 (2026-11-23) | a full **DocTwin sync** of one section: `oss-20b`, no tools, fact extraction off, connection reuse off, 900 s timeouts. Each `Agent.run` made **1 provider request** | **completed**. Translator 254.5 s, reviewer subagent 170.0 s, 435 s from start to finish (the rest is startup and the DocDrift check). Gates, reviewer and DocDrift passed; code block identical ([`evidence/portal/doctwin-sync-oss-20b/`](evidence/portal/doctwin-sync-oss-20b/)) |
| 9 (2026-11-23) | the same DocTwin sync on `gemma4` | the translator **stalled in all 3 attempts**, 900 s each with no response. DocTwin kept the section in English and wrote nothing wrong; 45 min wall time ([`evidence/portal/doctwin-sync-gemma4/`](evidence/portal/doctwin-sync-gemma4/)) |

**Bottom line (2026-11-21, before the successful run 8).** None of the first seven OpenMinion runs produced a valid
structured result on Portal. Every failure had a different, logged cause:
stalls, a gateway 502 on tool arguments, #719's task-update reply, and prose
instead of JSON. Each Portal feature works when called directly, and Portal
can serve OpenMinion's exact request. What did not work yet was OpenMinion's
turn of several requests on top of Portal's current latency and stability. DocTwin's sync therefore runs on the `openai` profile. The Portal
profile (`docdrift-portal`) stays in the repo, config-only, for when capacity
improves (`oss-120b` is listed as "no capacity" today).

**Update (2026-11-23): a complete sync on Portal.** Two days later, run 7's
settings worked inside a real DocTwin sync (run 8). With no tools and fact
extraction off, each `Agent.run` made exactly one provider request, so one slow
request no longer used up the turn budget. The translator took 254.5 s and the
reviewer 170.0 s. The gates, the reviewer and DocDrift all passed, and the code
block came out byte-identical. We cannot tell whether Portal got faster or we
were lucky: run 7 had the same settings and stalled. Right after, the same
sync on `gemma4` (run 9) stalled on all three attempts. DocTwin then did what
it should: it kept the section in English and wrote nothing wrong.

The translation is correct but plainer than `gpt-4.1-mini`'s
([`section.md`](evidence/portal/doctwin-sync-oss-20b/section.md)). The heading drops "Kembali", so "reuse"
becomes "use", and "retries", "prompts" and "Set" stay in English. The
reviewer subagent, also on `oss-20b`, accepted it. On Portal, keep the gates
and expect to fix style by hand.

**Replaying OpenMinion's exact request.** We captured the body OpenMinion
sends without sending it (8,674-char system prompt, one tool,
`tool_choice: auto`; 2,223 prompt tokens). Sent directly to Portal, the same
body **succeeded**: in 69.6 s (`gw-7135194f-…`), and in 124.1 s with
`max_tokens: 2048` (`gw-9a878a49-…`). Both returned the right
`glossary_lookup` call. The request is valid, and Portal can serve it. What
broke the OpenMinion turns was latency variance (17–124 s per request) plus
occasional stalls of 8 minutes or more, which hit 4 of our first 7 OpenMinion runs.

The same captured body on other aliases: `gemma4` returned the right tool call
in 62.5 s (`gw-eb63dad5-…`), while `qwen` stalled until our 300 s client
timeout.

**Two things worth the Portal team's attention.**
1. *Stalls.* Our direct `oss-20b` requests (7 of 7: the 5 checks above and the
   2 replays) completed. OpenMinion's
   requests stalled in 4 of the first 7 runs (1, 2, 3 and 7), for 5–15
   minutes, with no response or a disconnect. One run with connection reuse
   off did not stall, which first suggested reuse was the cause. Run 7 then
   stalled 904 s with reuse off. The stalls look intermittent and
   server-side, not tied to the client's connection handling.
2. *Schema-invalid tool arguments come back as 502.* The gateway validates the
   model's tool-call arguments against the advertised schema, and on a
   mismatch it returns `502` ("Model tool arguments do not match the
   advertised schema."). A 502 reads as an outage of the model backend, and
   on the free plan such failures still count toward the quota. A structured 4xx or 422
   error, or a gateway-side retry, would let clients like OpenMinion tell a
   model mistake from an outage.

**What this means.** Each Portal request takes 17–124 s for `oss-20b`, and
occasional 502s and multi-minute stalls happen. OpenMinion turns one
`Agent.run` into several provider requests (A5), and per its docs it does not
retry Portal requests because resubmission is not idempotent. So a single
tool-using turn can take longer than the default 480 s turn budget, even
though every individual feature works when called directly. For builders:
disable `auto_fact_extraction`, give Portal turns a longer timeout, keep
one Portal request in flight at a time, as the OpenMinion docs recommend, and
leave tools out where you can. One provider request per turn is what let
run 8 finish. `docdrift init --provider cortensor-portal` now applies these
settings.

---

## Runs

### DocTwin (Bahasa Indonesia, 7 OpenMinion doc files)

| Run | Source | Sections | Sent to the model | Result | Turns OK | Model time |
| --- | --- | --- | --- | --- | --- | --- |
| initial (before the A3 fixes) | v0.1.18 | 47 | 47 | 46 translated, but sections in 4 batches were never reviewed (B4) | 26/36 | 19 min |
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
project: across the 74 turns in the committed sync reports, a turn that called
the glossary tool used about 45,000 tokens (median) and a turn that did not
used about 13,000, and the length of the text made little difference.
`brain.auto_fact_extraction.enabled: false` (`docs/turn-budgets.md`) removes
one of those calls. In the demo sync (fact extraction off, no tool call), each
successful turn used about 4,500 tokens.

### DocDrift (OpenMinion docs v0.1.23 vs installed 0.1.23)

| Run | Change | Triage (5 candidates) | Claims (supported / contradicted / unverifiable) | Turns OK |
| --- | --- | --- | --- | --- |
| 1 | baseline | 4 wrong `real_drift`, all confirmed by the reviewer | 13 / 0 / 6 | 17/17 |
| 2 | usage facts + skeptical reviewer | 5/5 correct `out_of_scope` | 10 / 0 / 9 | 9/10 |
| 3 | better search tools and prompt | 5/5 correct | 16 / 0 / 3 | 9/9 |

Against older installs, the same docs show real drift: 0.1.15 lacks
`HTTPTransport` (`docs/a2a-remote.md:72`), and 0.1.10 also lacks
`openminion tasks show --runs-limit` (`docs/system-operations.md:215`).
Archived reports: [`evidence/docdrift/`](evidence/docdrift/).
