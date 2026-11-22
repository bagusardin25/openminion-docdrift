# DocTwin sync report (id)

- **source:** `demo-source`
- **generated:** 2026-11-22T22:20:22+00:00
- **OpenMinion session:** `doctwin-id-20261123-043510`

## Summary

| | |
| --- | --- |
| Sections | 54 total: 53 reused from the ledger, 0 translated, 0 need review, 0 not reviewed, 1 kept in English |
| Words sent to the model | 75 (reused without a model call: 6814) |
| Model turns | 0/3 succeeded, 45.0 min model time, 45.2 min wall time |
| Code blocks byte-identical to source | yes, every file |
| DocDrift check of commands and code in the translation | no broken commands or imports |

## Files

| File | Status | Sections | Code blocks identical |
| --- | --- | --- | --- |
| README.md | unchanged | 14 | yes |
| docs/getting-started.md | unchanged | 11 | yes |
| docs/runtime-surfaces.md | unchanged | 10 | yes |
| docs/turn-budgets.md | unchanged | 6 | yes |
| docs/provider-capabilities.md | written | 5 | yes |
| docs/configuration-compatibility.md | unchanged | 5 | yes |
| examples/sdk/README.md | unchanged | 3 | yes |

## Needs a human

- `docs/provider-capabilities.md` · `provider-capabilities/http-connection-reuse#1` · kept in English: missing from the model's output

## Fixed automatically

No section needed a retry.

## Glossary

No new terms proposed.

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| translate | docs/provider-capabilities.md [http-connection-reuse] | no | 901.4 | 0 | TurnTimeoutError: Turn execution timed out after 900.00 seconds. |
| translate | docs/provider-capabilities.md [http-connection-reuse] | no | 900.5 | 0 | TurnTimeoutError: Turn execution timed out after 900.00 seconds. |
| translate | docs/provider-capabilities.md [http-connection-reuse] (solo http-conn… | no | 900.4 | 0 | TurnTimeoutError: Turn execution timed out after 900.00 seconds. |
