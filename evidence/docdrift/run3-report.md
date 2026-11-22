# DocDrift report

- **openminion installed:** `0.1.23`
- **docs checked:** `openminion-v0.1.23 @ 695ba66`
- **generated:** 2026-11-19T01:27:33+00:00 on Windows 11, Python 3.12.13
- **OpenMinion session:** `docdrift-20261119-082027`

## Summary

| Stage | Result |
| --- | --- |
| Deterministic scan | 165 snippets checked, 5 candidates |
| Agent triage | 5 out_of_scope |
| Claim verification | 16 supported, 3 unverifiable |
| Confirmed by reviewer subagent | 0 |
| Disputed by reviewer subagent | 0 |
| Model turns | 9/9 succeeded |

## Confirmed drift

No confirmed drift.

## Disputed (reviewer did not confirm)

None.

## Triage of scan candidates

| Candidate | Where | Verdict | Reason |
| --- | --- | --- | --- |
| `D3cdd8d1` unknown_env_var | docs/guides/blockchain-tools.md:1 | out_of_scope | The 26 OPENMINION_* environment variables listed in the docs/guides/blockchain-tools.md are not referenced by the installed openminion package version 0.1.23. … |
| `Dde1f158` unknown_env_var | docs/runtime-database-upgrades.md:1 | out_of_scope | The environment variable OPENMINION_TEST_POSTGRES_URL is referenced in the documentation but nowhere in the installed openminion package source code, indicatin… |
| `Debb6ed1` unknown_env_var | docs/security-scanning.md:1 | out_of_scope | The 13 OPENMINION_* environment variables listed in docs/security-scanning.md are not referenced anywhere in the installed OpenMinion package version 0.1.23. E… |
| `D2472d8f` unknown_env_var | docs/system-operations.md:1 | out_of_scope | The environment variables listed in the docs/system-operations.md are not referenced by the installed package (version 0.1.23). These variables appear only in … |
| `D22f9339` unknown_env_var | docs/testing-and-validation.md:1 | out_of_scope | The environment variables starting with OPENMINION_CLI_FOCUS_E2E_AGENT and others listed in the doc are not referenced anywhere in the installed openminion pac… |

## Verified claims

| Section | Line | Verdict | Claim |
| --- | --- | --- | --- |
| docs/turn-budgets.md:8-30 (What the defaults control) | 12 | supported | `runtime.tool_selection.max_tools_per_turn` default is `6`, maximum entries in the selection service's shortlist, not executed calls per turn. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 13 | supported | `runtime.tool_selection.tool_prompt_token_budget` default is `600`, estimated prompt budget for that shortlist, not a complete model-request limit. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 14 | unverifiable | General adaptive loop bounds: `24` iterations, `64` tool calls, with adaptive extensions and other strategies having their own policies. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 15 | supported | `security.tool_policy.max_calls_per_run` default is `160`, runtime tool-call bound separate from the adaptive loop's bound. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 16 | supported | `runtime.session_context_token_budget` default is `0`, disables this optional additional session-context cap, with purpose-specific pack and bucket budgets sti… |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 74 | supported | OpenMinion reuses provider HTTP connections by default for OpenAI, OpenRouter, Anthropic, Cerebras, Groq, Ollama, and Cortensor. |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 76 | unverifiable | Reuse is owned by each provider instance and does not change routing, retries, prompts, or response parsing. |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 78 | supported | Set `http_connection_reuse_enabled: false` on a provider to return that provider to one HTTP connection per request |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 87 | unverifiable | The provider client is closed when its agent runtime is evicted or the API runtime shuts down. |
| docs/getting-started.md:109-161 (Persistent action-policy d… | 111 | supported | The top-level `action_policy` is the default for every agent without its own policy. |
| docs/getting-started.md:109-161 (Persistent action-policy d… | 117 | supported | "mode": "auto" |
| docs/getting-started.md:109-161 (Persistent action-policy d… | 118 | supported | "default_action": "require_confirm" |
| docs/getting-started.md:109-161 (Persistent action-policy d… | 119 | supported | "allow_read_only_without_prompt": true |
| docs/getting-started.md:109-161 (Persistent action-policy d… | 133 | supported | "mode": "bypass" disables ordinary action-policy enforcement for that agent. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 49 | supported | `Agent` owns an isolated session by default. Pass `session_id` to the constructor or to `run()` when an application already owns the continuity key. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 51 | supported | Pass `config_path` for a project-owned config and `agent_id` to select a configured profile. Agent calls return their result to Python without console delivery… |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 54 | supported | `Agent` also supports `with Agent(...) as agent:` for deterministic cleanup. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 55 | supported | `tools=None` keeps the configured default tool exposure; `tools=[]` disables application and orchestration tools for the turn. Explicit `handoffs` add their tr… |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 60 | supported | Its `run_stream()` method is a synchronous turn with a progress callback. For iterator streaming, cancellation, or explicit approval resolution, call `APIRunti… |

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| triage | docs/guides/blockchain-tools.md | yes | 27.6 | 2 |  |
| triage | docs/runtime-database-upgrades.md | yes | 15.3 | 1 |  |
| triage | docs/security-scanning.md | yes | 20.1 | 2 |  |
| triage | docs/system-operations.md | yes | 15.3 | 1 |  |
| triage | docs/testing-and-validation.md | yes | 21.6 | 2 |  |
| claims | docs/turn-budgets.md:8-30 (What the defaults control) | yes | 41.0 | 5 |  |
| claims | docs/provider-capabilities.md:72-88 (HTTP connection reuse) | yes | 28.7 | 5 |  |
| claims | docs/getting-started.md:109-161 (Persistent action-policy d… | yes | 30.1 | 7 |  |
| claims | docs/runtime-surfaces.md:34-125 (2. Python library API) | yes | 48.7 | 5 |  |
