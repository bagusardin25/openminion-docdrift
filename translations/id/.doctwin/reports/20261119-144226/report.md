# DocTwin sync report (id)

- **source:** `openminion-v0.1.18 @ b879519`
- **generated:** 2026-11-19T07:42:26+00:00
- **OpenMinion session:** `doctwin-id-20261119-142206`

## Summary

| | |
| --- | --- |
| Sections | 47 total: 0 reused from the ledger, 45 translated, 0 need review, 0 not reviewed, 2 kept in English |
| Words sent to the model | 5682 (reused without a model call: 0) |
| Model turns | 37/38 succeeded, 19.4 min model time, 20.3 min wall time |
| Code blocks byte-identical to source | yes, every file |
| DocDrift check of commands and code in the translation | no broken commands or imports |

## Files

| File | Status | Sections | Code blocks identical |
| --- | --- | --- | --- |
| README.md | written | 14 | yes |
| docs/getting-started.md | written | 11 | yes |
| docs/runtime-surfaces.md | written | 10 | yes |
| docs/turn-budgets.md | written | 5 | yes |
| docs/provider-capabilities.md | written | 5 | yes |
| docs/configuration-compatibility.md | missing_source | 0 | - |
| examples/sdk/README.md | written | 2 | yes |

## Needs a human

- `README.md` · `what-openminion-does-not-provide#1` · kept in English: missing from the model's output
- `docs/turn-budgets.md` · `understanding-turn-budgets-and-token-cost/maintainer-assessment-for-issue-497#1` · kept in English: numbers missing from translation: 0.0393, 0.0430, 33.76, 42.04

## Fixed automatically

4 section(s) passed only after a retry that quoted the gate or reviewer problems back to the translator.

## Glossary

No new terms proposed.

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| translate | README.md [_preamble, read-this-first, trust-and-brand-safety, at-a-g… | yes | 51.6 | 8 |  |
| review | README.md [_preamble, read-this-first, trust-and-brand-safety, at-a-g… | yes | 5.5 | 0 |  |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-provides… | yes | 67.4 | 3 |  |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-provides… | no | 12.0 | 0 | task-context capacity refusal: OpenMinion returned its canned 'could not safely update the task conditions' reply (input over the 12,000-character task limit) … |
| review | README.md [quick-start::p1, quick-start::p2, what-openminion-provides… | yes | 7.6 | 0 |  |
| review | README.md [quick-start::p1, quick-start::p2, what-openminion-provides… | yes | 7.5 | 0 |  |
| translate | README.md [runtime-surfaces, repository-map, development, docs-and-re… | yes | 53.0 | 4 |  |
| review | README.md [runtime-surfaces, repository-map, development, docs-and-re… | yes | 7.7 | 0 |  |
| translate | docs/getting-started.md [openminion-getting-started, fast-bootstrap, … | yes | 87.9 | 3 |  |
| review | docs/getting-started.md [openminion-getting-started, fast-bootstrap, … | yes | 5.7 | 0 |  |
| review | docs/getting-started.md [openminion-getting-started, fast-bootstrap, … | yes | 10.7 | 0 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p1] | yes | 45.0 | 1 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p1] | yes | 8.2 | 0 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 62.8 | 1 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 62.0 | 1 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 6.6 | 0 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 4.6 | 0 |  |
| translate | docs/getting-started.md [per-agent-command-access, read-first, normal… | yes | 83.1 | 2 |  |
| review | docs/getting-started.md [per-agent-command-access, read-first, normal… | yes | 6.2 | 0 |  |
| translate | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 123.8 | 2 |  |
| translate | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 47.6 | 1 |  |
| review | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 5.7 | 0 |  |
| review | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 5.3 | 0 |  |
| review | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 4.7 | 0 |  |
| review | docs/runtime-surfaces.md [openminion-runtime-surfaces, primary-surfac… | yes | 5.1 | 0 |  |
| translate | docs/runtime-surfaces.md [5-visual-graph-inspection, 6-acp-and-publis… | yes | 62.6 | 6 |  |
| translate | docs/runtime-surfaces.md [5-visual-graph-inspection, 6-acp-and-publis… | yes | 35.4 | 1 |  |
| review | docs/runtime-surfaces.md [5-visual-graph-inspection, 6-acp-and-publis… | yes | 6.9 | 0 |  |
| translate | docs/turn-budgets.md [understanding-turn-budgets-and-token-cost, what… | yes | 72.1 | 19 |  |
| translate | docs/turn-budgets.md [understanding-turn-budgets-and-token-cost, what… | yes | 31.8 | 1 |  |
| review | docs/turn-budgets.md [understanding-turn-budgets-and-token-cost, what… | yes | 5.5 | 0 |  |
| review | docs/turn-budgets.md [understanding-turn-budgets-and-token-cost, what… | yes | 18.3 | 0 |  |
| translate | docs/turn-budgets.md [maintainer-assessment-for-issue-497] | yes | 32.2 | 1 |  |
| translate | docs/turn-budgets.md [maintainer-assessment-for-issue-497] | yes | 31.5 | 1 |  |
| translate | docs/provider-capabilities.md [provider-capabilities, profile-facts, … | yes | 42.7 | 5 |  |
| review | docs/provider-capabilities.md [provider-capabilities, profile-facts, … | yes | 5.2 | 0 |  |
| translate | examples/sdk/README.md [python-sdk-examples, example-map] | yes | 29.0 | 9 |  |
| review | examples/sdk/README.md [python-sdk-examples, example-map] | yes | 5.4 | 0 |  |
