# Building Blocks Tested

OpenMinion `0.1.23` from PyPI · Python 3.12 · Windows 11 · provider preset
`openai` with `gpt-4.1-mini` · DocDrift `0.1.0`.

Legend: ✅ worked as documented · ⚠️ worked with a workaround · ❌ did not work ·
➖ not used.

| Building block | Used how | Result | Notes |
| --- | --- | --- | --- |
| **Agent execution** (`Agent.run`) | 4 roles, one OpenMinion session per DocDrift run | ✅ | Context manager closes the runtime cleanly. |
| **Models / provider presets** | `openminion setup --provider openai`, config-only switch to Gemini or Cortensor Portal | ✅ | The key stays in `.env`. `agents.json` stores only `api_key_env`; we checked that no file under `.openminion/` contains the key. |
| **Tools** (`@tool`) | 6 evidence tools, 1 write tool | ✅ | Docstrings become tool descriptions. Typed params work. |
| **Permissions** (`min_scope`, action policy) | evidence tools `READ_ONLY` + `idempotent`; write tool at default `WRITE_SAFE` | ✅ | Read-only tools never prompted. The write tool always reached `approval_callback`. |
| **Human approval** (`approval_callback`) | operator `y/N` before each issue draft | ✅ | `docdrift approval-check` passed 6/6: deny → "Confirmation denied. The action was not run." and no file; approve → file written. In run 1, 1 of 4 forced-tool turns ended without calling the tool (not reproduced). |
| **Structured output** (`output_type=`) | Pydantic models for triage, claims, review | ⚠️ | The schema is never sent to the provider. Compliance was 0/4 without tools and 2/4 with tools in a probe. After we put the schema in the user turn: 13/13 (run 1), 9/10 plus 1 fixed by our repair turn (run 2), 9/9 (run 3). See [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md) §1. |
| **Delegation** (`subagent`) | bounded reviewer that re-checks every negative verdict | ✅ | Own instructions, tools, output type and timeout. |
| **Forced tools** (`forced_tools=`) | issue writer must call `write_issue_draft` first | ✅ | |
| **Sessions / threads** | `session_id=docdrift-<timestamp>`, new thread per item | ✅ | State stays in the project via `OPENMINION_HOME` / `OPENMINION_DATA_ROOT`. |
| **Diagnostics** (`ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`, `result.stats`, `run_id`) | every turn's seconds, tool calls (with arguments), errors and reply are logged into `report.json` | ⚠️ | `AgentOutputValidationError` reports the wrong cause after JSON recovery (§2). `OPENMINION_TRACE_REQUESTS=1` wrote no trace files for SDK runs (§6). |
| **CLI surface** | `--help` for every documented command (58 command paths) | ✅ | All 145 shell snippets in the v0.1.23 docs match the installed CLI. |
| **Memory** | — | ➖ | Not needed. Each run is independent; the previous `report.json` is used to mark new findings. |
| **Skills / tasks / scheduling** | — | ➖ | Not needed for a single-pass checker. |
| **Handoffs** (`Handoff`) | — | ➖ | `subagent` fit better because the reviewer returns to the coordinator. |
| **Cortensor Portal** | provider preset documented in README | ➖ | No Portal access during the build. Switching is config-only: `uv run docdrift init --provider cortensor-portal`. |
