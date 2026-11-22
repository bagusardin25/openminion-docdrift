# Building Blocks Tested

OpenMinion `0.1.23` from PyPI · Python 3.12 · Windows 11 · provider preset
`openai` with `gpt-4.1-mini` · DocTwin + DocDrift `0.1.0`.

✅ worked as documented · ⚠️ worked with a workaround · ❌ did not work ·
➖ evaluated, not used. Section numbers refer to [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md).

| Building block | How we used it | Result | Notes |
| --- | --- | --- | --- |
| **Agent execution** (`Agent.run`) | DocTwin: translator, reviewer, glossary keeper. DocDrift: triage, claims, reviewer, issue writer | ⚠️ | Works. Input over 12,000 characters returns a canned reply as a *completed* run (A3), so DocTwin budgets every request and detects the text. |
| **Models / provider presets** | `openminion setup --provider openai`; Gemini and `cortensor-portal` are config-only switches | ✅ | Only `api_key_env` is stored; no file under `.openminion/` contains the key. |
| **Tools** (`@tool`) | `glossary_lookup`, six DocDrift evidence tools, two write tools | ✅ | The translator called `glossary_lookup` on its own (for example for "transport capabilities", "fallback profiles"). |
| **Permissions** (`min_scope`, action policy) | evidence tools `READ_ONLY` + `idempotent`; write tools at default `WRITE_SAFE` | ✅ | Read-only tools never prompted; every write reached the callback. |
| **Human approval** (`approval_callback`) | glossary additions (`add_glossary_term`), issue drafts (`write_issue_draft`) | ✅ | `docdrift approval-check` 6/6. A real sync asked once per proposed term (5 in one run). Denied → nothing written. |
| **Forced tools** (`forced_tools=`) | glossary keeper and issue writer must call their write tool | ✅ | 1 of 4 issue-writer turns in one early run ended without the tool call (not reproduced). |
| **Structured output** (`output_type=`) | Pydantic batches for translation, review, triage, claims | ⚠️ | The schema is never sent to the model (A1). Workaround: schema in the user turn + one JSON repair turn. Validation errors point at the wrong cause (A2, fix PR ready). |
| **Delegation** (`subagent`) | DocTwin reviewer and DocDrift reviewer | ✅ | Own instructions, tools, output type and timeout. Same-model self-review rubber-stamped until we gave it facts and asked it to disprove (B1). |
| **Sessions / threads** | one `session_id` per sync or run, a new thread per turn | ✅ | A one-session vs fresh-session probe showed no difference. State stays in the project (`OPENMINION_HOME`). |
| **Task context** (implicit) | not used directly | ❌ | Its 12,000-character objective limit is what A3 hits, and it is not mentioned in the SDK docs. |
| **Diagnostics** (`ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`, `run_id`, `stats`) | per-turn table in every report: seconds, tool calls with arguments, errors, reply | ⚠️ | A2 makes validation errors misleading. `OPENMINION_TRACE_REQUESTS=1` wrote nothing for SDK runs (A7). |
| **CLI surface** | `--help` for all 58 command paths in the docs | ✅ | All 145 shell snippets in the v0.1.23 docs match the installed CLI. |
| **Memory** | wanted for the glossary | ➖ | No `Agent`-level scoped put/get. `MemoryBundle` is portability only (A8). The glossary is a JSON file behind an approval-gated tool. |
| **Skills / tasks / scheduling** | — | ➖ | A sync is one pass; scheduling is left to the user's CI or cron. |
| **Handoffs** (`Handoff`) | — | ➖ | `subagent` fit better because the reviewer returns to the coordinator. |
| **Cortensor Portal** | preset `cortensor-portal`, separate profile `docdrift-portal` (`uv run docdrift init --provider cortensor-portal --model oss-20b --agent docdrift-portal`), free-plan key | ❌ end to end / ✅ direct API | Direct API calls work: tool calls, forced `tool_choice`, and OpenMinion's exact captured request all succeed in 17–124 s. Seven full OpenMinion turns on `oss-20b` and `gemma4` (with and without tools) produced no valid result, each for a logged reason: stalls, gateway 502 on tool arguments, #719, prose instead of JSON. See [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md) Part D. |
| **Gemma4** (via Portal) | `gemma4` alias | ⚠️ | A direct tool call worked in 62.5 s. Inside OpenMinion it hit #719's canned task-update reply, and without tools it answered in prose. |
