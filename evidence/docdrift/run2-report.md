# DocDrift report

- **openminion installed:** `0.1.23`
- **docs checked:** `openminion-v0.1.23 @ 695ba66`
- **generated:** 2026-11-19T01:08:20+00:00 on Windows 11, Python 3.12.13
- **OpenMinion session:** `docdrift-20261119-080057`

## Summary

| Stage | Result |
| --- | --- |
| Deterministic scan | 165 snippets checked, 5 candidates |
| Agent triage | 5 out_of_scope |
| Claim verification | 10 supported, 9 unverifiable |
| Confirmed by reviewer subagent | 0 |
| Disputed by reviewer subagent | 0 |
| Model turns | 9/10 succeeded |

## Confirmed drift

No confirmed drift.

## Disputed (reviewer did not confirm)

None.

## Triage of scan candidates

| Candidate | Where | Verdict | Reason |
| --- | --- | --- | --- |
| `D3cdd8d1` unknown_env_var | docs/guides/blockchain-tools.md:1 | out_of_scope | The environment variables listed in the docs are not referenced in the installed openminion package version 0.1.23; they are only used in the source checkout t… |
| `Dde1f158` unknown_env_var | docs/runtime-database-upgrades.md:1 | out_of_scope | The environment variable 'OPENMINION_TEST_POSTGRES_URL' referenced in the doc 'docs/runtime-database-upgrades.md' is not used or recognized by the installed op… |
| `Debb6ed1` unknown_env_var | docs/security-scanning.md:1 | out_of_scope | The 13 OPENMINION_* environment variables mentioned in the docs/security-scanning.md are not referenced in the installed openminion package version 0.1.23. The… |
| `D2472d8f` unknown_env_var | docs/system-operations.md:1 | out_of_scope | The environment variables OPENMINION_LIVE_OPS_SSH, OPENMINION_OPS_SSH_HOST, OPENMINION_OPS_SSH_HOST_KEY, OPENMINION_OPS_SSH_KEY, OPENMINION_OPS_SSH_PASSWORD, O… |
| `D22f9339` unknown_env_var | docs/testing-and-validation.md:1 | out_of_scope | The environment variables OPENMINION_CLI_FOCUS_E2E_AGENT, OPENMINION_CLI_FOCUS_E2E_CONFIG, OPENMINION_CLI_FOCUS_E2E_RUNNER_TIMEOUT_SECONDS, OPENMINION_LIVE_CLI… |

## Verified claims

| Section | Line | Verdict | Claim |
| --- | --- | --- | --- |
| docs/turn-budgets.md:8-30 (What the defaults control) | 12 | unverifiable | `runtime.tool_selection.max_tools_per_turn` \| `6` \| Maximum entries in the selection service's shortlist, not executed calls per turn. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 13 | unverifiable | `runtime.tool_selection.tool_prompt_token_budget` \| `600` \| Estimated prompt budget for that shortlist, not a complete model-request limit. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 14 | supported | General adaptive loop \| `24` iterations, `64` tool calls \| Loop execution bounds; adaptive extensions and other strategies have their own policies. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 15 | supported | `security.tool_policy.max_calls_per_run` \| `160` \| Runtime tool-call bound, separate from the adaptive loop's bound. |
| docs/turn-budgets.md:8-30 (What the defaults control) | 16 | supported | `runtime.session_context_token_budget` \| `0` \| Disable this optional additional session-context cap; purpose-specific pack and bucket budgets still apply. |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 74 | supported | OpenMinion reuses provider HTTP connections by default for OpenAI, OpenRouter, Anthropic, Cerebras, Groq, Ollama, and Cortensor. |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 76 | unverifiable | Reuse is owned by each provider instance and does not change routing, retries, prompts, or response parsing. |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 78 | supported | Set `http_connection_reuse_enabled: false` on a provider to return that provider to one HTTP connection per request: |
| docs/provider-capabilities.md:72-88 (HTTP connection reuse) | 87 | unverifiable | The provider client is closed when its agent runtime is evicted or the API runtime shuts down. |
| docs/task-context.md:40-63 (Execution and budgets) | 54 | unverifiable | The task has at most 128 conditions and a 12000-character content limit. |
| docs/task-context.md:40-63 (Execution and budgets) | 49 | unverifiable | While an external job is pending, context amendments are rejected. |
| docs/task-context.md:40-63 (Execution and budgets) | 50 | unverifiable | Replacement and cancellation of task-backed execution must use its existing owner. |
| docs/task-context.md:40-63 (Execution and budgets) | 58 | unverifiable | Each returned entry retry is accounted for. |
| docs/task-context.md:40-63 (Execution and budgets) | 42 | unverifiable | The existing execution context owner builds the act request. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 49 | supported | `Agent` owns an isolated session by default. Pass `session_id` to the constructor or to `run()` when an application already owns the continuity key. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 51 | supported | Pass `config_path` for a project-owned config and `agent_id` to select a configured profile. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 55 | supported | `tools=None` keeps the configured default tool exposure; `tools=[]` disables application and orchestration tools for the turn. Explicit `handoffs` add their tr… |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 60 | supported | Its `run_stream()` method is a synchronous turn with a progress callback. |
| docs/runtime-surfaces.md:34-125 (2. Python library API) | 66 | supported | `Agent.run()` and callback-progress `run_stream()` accept optional `timeout_seconds`, `approval_callback`, and `cancel_event` controls already owned by runtime… |

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| triage | docs/guides/blockchain-tools.md | yes | 40.2 | 2 |  |
| triage | docs/runtime-database-upgrades.md | yes | 21.0 | 1 |  |
| triage | docs/security-scanning.md | yes | 28.6 | 2 |  |
| triage | docs/system-operations.md | yes | 20.0 | 1 |  |
| triage | docs/testing-and-validation.md | yes | 29.7 | 2 |  |
| claims | docs/turn-budgets.md:8-30 (What the defaults control) | yes | 51.9 | 8 |  |
| claims | docs/provider-capabilities.md:72-88 (HTTP connection reuse) | no | 34.0 | 5 | AgentOutputValidationError: recovered JSON object failed schema validation: 1 validation error for ClaimReport claims Field required [type=missing, input_value={'line': 74, 'quote': 'Op...'], 'sugges… |
| claims | docs/provider-capabilities.md:72-88 (HTTP connection reuse) | yes | 11.0 | 0 |  |
| claims | docs/task-context.md:40-63 (Execution and budgets) | yes | 49.2 | 11 |  |
| claims | docs/runtime-surfaces.md:34-125 (2. Python library API) | yes | 45.2 | 6 |  |
