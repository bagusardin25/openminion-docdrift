# DocTwin sync report (id)

- **source:** `demo-source`
- **generated:** 2026-11-22T17:04:50+00:00
- **OpenMinion session:** `doctwin-id-20261123-000423`

## Summary

| | |
| --- | --- |
| Sections | 54 total: 53 reused from the ledger, 1 translated, 0 need review, 0 not reviewed, 0 kept in English |
| Words sent to the model | 75 (reused without a model call: 6814) |
| Model turns | 2/3 succeeded, 0.2 min model time, 0.5 min wall time |
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

Nothing. Every changed section passed the gates and the reviewer.

## Fixed automatically

1 section(s) passed only after a retry that quoted the gate or reviewer problems back to the translator.

## Glossary

No new terms proposed.

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| translate | docs/provider-capabilities.md [http-connection-reuse] | no | 5.4 | 0 | task-context capacity refusal: OpenMinion returned its canned 'could not safely update the task conditions' reply (input over the 12,000-character task limit) … |
| translate | docs/provider-capabilities.md [http-connection-reuse] | yes | 5.3 | 0 |  |
| review | docs/provider-capabilities.md [http-connection-reuse] | yes | 3.6 | 0 |  |
