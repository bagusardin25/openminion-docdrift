# DocTwin sync report (id)

- **source:** `openminion-v0.1.23 @ 695ba66`
- **generated:** 2026-11-19T08:05:08+00:00
- **OpenMinion session:** `doctwin-id-20261119-150154`

## Summary

| | |
| --- | --- |
| Sections | 54 total: 52 reused from the ledger, 2 translated, 0 need review, 0 not reviewed, 0 kept in English |
| Words sent to the model | 718 (reused without a model call: 6173) |
| Model turns | 5/7 succeeded, 2.6 min model time, 3.2 min wall time |
| Code blocks byte-identical to source | yes, every file |
| DocDrift check of commands and code in the translation | no broken commands or imports |

## Files

| File | Status | Sections | Code blocks identical |
| --- | --- | --- | --- |
| README.md | written | 14 | yes |
| docs/getting-started.md | unchanged | 11 | yes |
| docs/runtime-surfaces.md | unchanged | 10 | yes |
| docs/turn-budgets.md | unchanged | 6 | yes |
| docs/provider-capabilities.md | unchanged | 5 | yes |
| docs/configuration-compatibility.md | unchanged | 5 | yes |
| examples/sdk/README.md | written | 3 | yes |

## Needs a human

Nothing. Every changed section passed the gates and the reviewer.

## Fixed automatically

1 section(s) passed only after a retry that quoted the gate or reviewer problems back to the translator.

## Glossary

No new terms proposed.

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| translate | README.md [quick-start::p1, quick-start::p2] | no | 20.3 | 0 | task-context capacity refusal: OpenMinion returned its canned 'could not safely update the task conditions' reply (input over the 12,000-character task limit) … |
| translate | README.md [quick-start::p1, quick-start::p2] | no | 55.4 | 2 | AgentOutputValidationError: recovered JSON object failed schema validation: 1 validation error for TranslationBatch sections Field required [type=missing, inpu… |
| translate | README.md [quick-start::p1, quick-start::p2] | yes | 29.3 | 0 |  |
| review | README.md [quick-start::p1, quick-start::p2] | yes | 7.8 | 0 |  |
| review | README.md [quick-start::p1, quick-start::p2] | yes | 7.7 | 0 |  |
| translate | examples/sdk/README.md [handoff-approval] | yes | 28.4 | 1 |  |
| review | examples/sdk/README.md [handoff-approval] | yes | 7.5 | 0 |  |
