# Building Blocks Tested

Which OpenMinion building blocks DocTwin and DocDrift use, what worked, and
what did not. The details and evidence for each row are in
[WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md).

**Tested with:** OpenMinion `0.1.23` from PyPI · Python 3.12 · Windows 11 ·
provider preset `openai` with `gpt-4.1-mini`, plus Cortensor Portal · DocTwin +
DocDrift `0.1.0`.

**How to read it.** ✅ worked as documented · ⚠️ worked with a workaround ·
❌ did not work · ➖ evaluated, not used. Codes like A3 or B1 are items in
WHAT_WE_LEARNED.md. Numbers like #719 are issues in the OpenMinion GitHub
repository. A *canned reply* is a fixed text built into OpenMinion that comes
back instead of a model answer.

| Building block | How we used it | Result | Notes |
| --- | --- | --- | --- |
| **Agent execution** (`Agent.run`) | DocTwin: translator, reviewer, glossary keeper. DocDrift: triage, claims, reviewer, issue writer | ⚠️ | Works, with a workaround. Input over 12,000 characters returns a canned reply as a *completed* run (A3), so DocTwin keeps every request under 11,000 characters and detects that reply. |
| **Models / provider presets** | `openminion setup --provider openai`; Gemini and `cortensor-portal` are config-only switches | ✅ | Only `api_key_env` is stored; no file under `.openminion/` contains the key. |
| **Tools** (`@tool`) | `glossary_lookup`, six DocDrift evidence tools, two write tools | ✅ | The translator called `glossary_lookup` on its own (for example for "transport capabilities", "fallback profiles"). |
| **Permissions** (`min_scope`, action policy) | evidence tools `READ_ONLY` + `idempotent`; write tools at default `WRITE_SAFE` | ✅ | Read-only tools never prompted; every write reached the callback. |
| **Human approval** (`approval_callback`) | glossary additions (`add_glossary_term`), issue drafts (`write_issue_draft`) | ✅ | `docdrift approval-check` 6/6. A real sync asked once per proposed term (5 in one run). Denied → nothing written. |
| **Forced tools** (`forced_tools=`) | glossary keeper and issue writer must call their write tool | ✅ | 1 of 4 issue-writer turns in one early run ended without the tool call (not reproduced). |
| **Structured output** (`output_type=`) | Pydantic batches for translation, review, triage, claims | ⚠️ | The schema is never sent to the model (A1). Workaround: schema in the user turn + one JSON repair turn. Validation errors point at the wrong cause (A2; our fix shipped in 0.1.24). |
| **Delegation** (`subagent`) | DocTwin reviewer and DocDrift reviewer | ✅ | Own instructions, tools, output type and timeout. A reviewer on the same model approved everything until we gave it facts and asked it to disprove (B1). |
| **Sessions / threads** | one `session_id` per sync or run, a new thread per turn | ✅ | A one-session vs fresh-session probe showed no difference. State stays in the project (`OPENMINION_HOME`). |
| **Task context** (implicit) | not used directly, but every run goes through it | ⚠️ | Hidden limit: a 12,000-character objective bound causes A3, and the SDK docs do not mention it. DocTwin works around it by keeping requests short. Our PR [#869](https://github.com/openminion/openminion/pull/869), merged into `dev`, now gives this rejection its own reason and a truthful question. |
| **Diagnostics** (`ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`, `run_id`, `stats`) | per-turn table in every report: seconds, tool calls with arguments, errors, reply | ⚠️ | A2 makes validation errors misleading. `OPENMINION_TRACE_REQUESTS=1` wrote nothing for SDK runs (A7). |
| **CLI surface** | `--help` for all 58 command paths in the docs | ✅ | All 145 shell snippets in the v0.1.23 docs match the installed CLI. |
| **Memory** | wanted for the glossary | ➖ | No `Agent`-level scoped put/get. `MemoryBundle` is only an export/import format (A8). The glossary is a JSON file behind an approval-gated tool. |
| **Skills / tasks / scheduling** | — | ➖ | A sync is one pass; scheduling is left to the user's CI or cron. |
| **Handoffs** (`Handoff`) | — | ➖ | `subagent` fit better because the reviewer returns to the coordinator. |
| **Cortensor Portal** | preset `cortensor-portal`, profile `docdrift-portal` (`uv run docdrift init --provider cortensor-portal --model oss-20b --agent docdrift-portal`), free-plan key | ⚠️ | Works for a one-section sync, slowly, with no tools and fact extraction off: 435 s on `oss-20b`, gates and reviewer passed ([evidence](evidence/portal/doctwin-sync-oss-20b/)). Direct API calls work, tool calls included (17–124 s each). Seven earlier OpenMinion turns failed, each for a logged reason: stalls, HTTP 502 on tool arguments, #719, prose instead of JSON. Part D has the details. |
| **Gemma4** (via Portal) | `gemma4` alias | ❌ | Did not work inside OpenMinion; direct API calls did (a tool call in 62.5 s). Inside OpenMinion it hit #719's canned reply, answered in prose without tools, and a full DocTwin sync stalled on all 3 attempts (900 s each). DocTwin kept that section in English ([evidence](evidence/portal/doctwin-sync-gemma4/)). |
