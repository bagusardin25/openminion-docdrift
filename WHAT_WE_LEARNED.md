# What We Learned

Feedback from building DocDrift on OpenMinion `0.1.23` (PyPI), Python 3.12,
Windows 11, `openai` preset with `gpt-4.1-mini`. Every item says what we saw,
the evidence, and what we would change. File paths are relative to the
installed `openminion` package unless noted.

**Status key.** *Confirmed*: reproduced, root cause found in source.
*Observed*: reproduced; cause not fully traced. *Documented gotcha*: works as
the docs say, but tripped us up.

---

## 1. `Agent(output_type=...)` never tells the model about the schema (Confirmed)

**What we saw.** Our first real runs failed with `AgentOutputValidationError`
in 2 of 2 claim-verification turns. The model answered in prose, or used its
own keys (`claims_verification` instead of `claims`).

**Why.** `output_type` is used only after the reply arrives, in
`api/agent.py:253-284` (`_coerce_output`). `_build_payload`
(`api/agent.py:158-194`) sends no schema and no JSON mode. `instructions`
*are* sent: we captured the request bodies in-process (wrapping
`ProviderHTTPClient.urlopen`) and found them under `[IDENTITY]`. But they sit
inside a 5,278–17,763 character runtime system prompt that has its own
answer-format contracts (for example a "Tool-calling contract" and "provide the
full user-facing final answer and populate the structured confidence…").

**Measured** with a minimal probe (`instructions` asking for a 2-key JSON
object, `output_type` set):

| Agent | Schema-valid replies |
| --- | --- |
| no `tools=` | 0 / 4 |
| one `@tool` | 2 / 4 |
| schema repeated in the **user message** (DocDrift's workaround) | 13 / 13 structured turns in the first full run, with no repair turn needed |

**Suggested change.** When `output_type` is a Pydantic model, append its JSON
Schema as the last system block or to the final-answer step. When the provider
profile declares `supports_json`, also send the provider's JSON/schema mode.
Until then, the SDK README could say that `instructions` must spell out the
JSON shape. The examples already do this implicitly (`structured_output.py`).

## 2. `AgentOutputValidationError` hides the real cause (Confirmed, fix PR ready)

When the raw reply is not JSON, `_coerce_output` recovers the first JSON object
and validates it again. If that also fails, it raises the **first** error.
Replies always start with `"<agent>: "` (see §3), so the message is always
`Invalid JSON: expected value at line 1 column 1`. In our case the real cause
was `Field required: claims`.

Fix: keep the recovered object's `ValidationError`.
[`submission/upstream/0001-agent-output-validation-error-cause.patch`](submission/upstream/0001-agent-output-validation-error-cause.patch)
adds one regression test. `tests/api/test_agent.py` passes 50/50 with the
patch, and the new test fails on 0.1.23.

## 3. `result.text` starts with `"<agent_id>: "` (Confirmed)

`services/brain/post_execution/postprocess_response.py:276` builds
`f"{agent_name}: {response_text}"`. `Agent.run()` sets `deliver: False`, yet the
envelope prefix still reaches `AgentRunResult.text`. For example:
`'docdrift: The hex code of teal is #008080.'`. Applications that show or parse
`result.text` have to strip it. `_extract_json_object` hides the prefix for
JSON, which makes §2 worse.

**Suggested change:** keep the channel envelope out of `result.text`, or expose
the unprefixed text separately.

## 4. A one-tool question costs about 7 provider calls (Observed)

Our wire capture of one `Agent.run("What is the hex code of teal?")` with a
single `@tool` counted 7 HTTP requests: the tool-contract turn, a
"freshness-routing classifier", tool-result continuations, a confidence/final
composition step, and a closing identity turn. Without tools it was 2 calls.
That is fine on paid OpenAI, but it matters for free-tier rate limits and for
Cortensor Portal, which the docs describe as slow and serial
(`docs/getting-started.md`).

**Suggested change:** document the per-turn call budget and expose a switch for
the auxiliary classifier steps in SDK runs.

## 5. `tools=None` still exposes the runtime's default tools (Documented gotcha)

`docs/runtime-surfaces.md:55` documents this: `tools=None` keeps the default
tool exposure and `tools=[]` disables it. Even so, an agent that only wants
structured output still gets the tool-calling contract in its system prompt. In
our probe that contract competed with the output format. The `output_type`
docs could recommend `tools=[]` for pure structured-output agents.

## 6. `OPENMINION_TRACE_REQUESTS=1` wrote no trace files for SDK runs (Observed)

With `OPENMINION_TRACE_REQUESTS=1` (and `OPENMINION_TRACE_REQUESTS_DIR`) set in
the process environment, `resolve_environment_config()` reports the flag as
`True`. Yet a full `Agent.run()` wrote no `*-http.json` file under
`OPENMINION_HOME`, the trace dir, `~/.openminion`, or the temp dir. The
provider transport passes `env=env_owner` to `trace_http_json_request`
(`modules/llm/providers/transport/http.py`), not the process env. We did not
confirm whether that is the cause. We fell back to wrapping
`ProviderHTTPClient.urlopen` to see request bodies.

## 7. Agent quality: one model reviewing itself rubber-stamps (Lesson for builders)

Our first full run triaged five env-var candidates. The triage agent called 4
of them `real_drift`, and the reviewer subagent (same model) **confirmed all
4**. Every one was wrong. All of the variables live in `tests/`, `.github/`, or
are built from a prefix constant
(`tests/e2e/runners/run_blockchain_testnet_write.py:38`). The agents made only
1–2 tool calls each and never looked at the repo's test tree.

What fixed it:
- **Facts are computed deterministically and handed to the model.** DocDrift
  now records where each name is used in the checkout, including prefix
  constants. The model judges; it no longer has to find the facts.
- **The reviewer is told to disprove.** Its instructions list the alternative
  explanations it must rule out (test/CI/maintainer-only names,
  contributor-facing pages, renamed APIs) before agreeing.

Re-run results after the fix: see [Runs](#runs) below.

**The model searched source code for doc sentences.** The claims agent marked
"The task has at most 128 conditions and a 12000-character content limit"
(`docs/task-context.md:54`) as *unverifiable*. The claim is true:
`modules/brain/schemas/task_context.py:37` has `max_length=128` and
`modules/brain/constants.py:21` has `TASK_CONTEXT_MAX_CHARS = 12_000`. Per-turn
tool-call logging showed why: its queries were whole sentences
(`search_package_source('task has at most 128 conditions')`). It also could not
have matched `12000` against `12_000`. We fixed our tools (number searches also
try the underscore form, and sentence-shaped queries that miss return a hint)
and the prompt (search identifiers and literals, at least two queries per
claim). After that the agent searched `128`, `12000` and opened the right
files, though it still chose different claims to report. With `gpt-4.1-mini`,
claim selection and verdicts vary between runs: two claims supported with exact
file:line in run 1 came back *unverifiable* in run 2.

**"Supported" is weaker than it looks.** The claims agent sometimes backs a
claim with loose evidence. For example, it cited `Agent.close()` for a claim
about provider client lifetime. DocDrift only escalates `contradicted` verdicts,
so this does not create false issues, but supported claims should be read as
"no contradiction found", not "proven".

## 8. What worked well

- **Docs quality.** All 145 shell and 20 Python snippets in the v0.1.23 docs
  match the installed CLI and package. Drift appears only when the same docs
  are used with older releases: 0.1.15 lacks `HTTPTransport`
  (`docs/a2a-remote.md:72`), and 0.1.10 also lacks
  `openminion tasks show --runs-limit` (`docs/system-operations.md:215`).
- **Permissions and approval.** `READ_ONLY` + `idempotent` tools never
  prompted. The default-scope write tool hit `approval_callback` every time.
  `docdrift approval-check` passed 6/6 (deny → no file and the runtime says
  "Confirmation denied. The action was not run."; approve → file written). In
  the first full run, 1 of 4 issue-writer turns ended without calling the
  forced tool and without an approval prompt. We did not capture that reply and
  could not reproduce it.
- **Provider setup.** `openminion setup --provider openai` stored only
  `api_key_env`. No file under `.openminion/` contains the key.
- **`subagent`** gave the reviewer its own instructions, tools, output type and
  timeout in one call.
- **Diagnostics.** `ProviderError`, `TurnTimeoutError` and `run_id` were enough
  to build a per-turn diagnostics table without touching internals.

## Runs

All runs: openminion 0.1.23 vs docs tag v0.1.23 (`695ba66`), 165 snippets,
5 deterministic candidates (all `unknown_env_var`), `gpt-4.1-mini`.

| Run | Change | Triage (5 candidates) | Reviewer | Claims (supported / contradicted / unverifiable) | Turns OK | Model time |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | 4 real_drift, 1 out_of_scope (**4 wrong**) | confirmed 4/4 (**all wrong**) | 13 / 0 / 6 | 17/17 | 6.3 min |
| 2 | usage facts in candidates, skeptical reviewer | 5 out_of_scope (**all correct**) | nothing to review | 10 / 0 / 9 | 9/10 (1 repaired by the JSON repair turn) | 5.5 min |
| 3 | better search tools + prompt; `task-context` section swapped for `getting-started#Persistent action-policy defaults` | 5 out_of_scope (**all correct**) | nothing to review | 16 / 0 / 3 | 9/9, no repair turn | 4.1 min |

Archived reports: [`out/history/`](out/history/). Latest: [`out/report.md`](out/report.md).

**Spot checks of run 3 by hand.**
- Two of the three *unverifiable* claims are in fact supported by source.
  "`24` iterations, `64` tool calls" (`docs/turn-budgets.md:14`) matches
  `modules/brain/config.py:43-44` (`ADAPTIVE_MAX_ITERATIONS = 24`,
  `ADAPTIVE_MAX_TOOL_CALLS = 64`). The 128-condition / 12,000-character limit
  from run 2 is the other.
- The five *supported* claims in `getting-started#Persistent action-policy
  defaults` all cite the same line (`api/core/infrastructure.py:291`), which is
  where the policy service is built, not where each default lives. The
  defaults themselves are correct: `openminion config init` writes
  `"mode": "auto"`, `"default_action": "require_confirm"` and
  `"allow_read_only_without_prompt": true`.

**Net result for OpenMinion 0.1.23.** We found no doc drift. The CLI and
Python snippets all match the installed package. Every flagged env var belongs
to the repo's test suite. No checked claim is contradicted. The useful output
of this project is therefore the SDK feedback in §1–§6, the fix PR for §2, and
a checker that does catch drift when the docs and the installed version
diverge (0.1.10 / 0.1.15 rows in the README).
