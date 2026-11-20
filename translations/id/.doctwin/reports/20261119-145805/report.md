# DocTwin sync report (id)

- **source:** `openminion-v0.1.23 @ 695ba66`
- **generated:** 2026-11-19T07:58:05+00:00
- **OpenMinion session:** `doctwin-id-20261119-144619`

## Summary

| | |
| --- | --- |
| Sections | 54 total: 40 reused from the ledger, 14 translated, 0 need review, 0 not reviewed, 0 kept in English |
| Words sent to the model | 3777 (reused without a model call: 3125) |
| Model turns | 30/33 succeeded, 11.0 min model time, 11.8 min wall time |
| Code blocks byte-identical to source | yes, every file |
| DocDrift check of commands and code in the translation | no broken commands or imports |

## Files

| File | Status | Sections | Code blocks identical |
| --- | --- | --- | --- |
| README.md | written | 14 | yes |
| docs/getting-started.md | written | 11 | yes |
| docs/runtime-surfaces.md | written | 10 | yes |
| docs/turn-budgets.md | written | 6 | yes |
| docs/provider-capabilities.md | unchanged | 5 | yes |
| docs/configuration-compatibility.md | written | 5 | yes |
| examples/sdk/README.md | written | 3 | yes |

## Needs a human

Nothing. Every changed section passed the gates and the reviewer.

## Fixed automatically

3 section(s) passed only after a retry that quoted the gate or reviewer problems back to the translator.

## Glossary

- `Bare` → `sederhana` (not added): Untuk mengartikan perintah 'bare command' sebagai perintah dasar atau sederhana dalam konteks teknologi
- `read-only` → `hanya baca` (not added): Istilah read-only digunakan sebagai 'hanya baca' sesuai konteks akses sistem file
- `preset` → `preset` (not added): Istilah ini tidak memiliki padanan khusus dalam glosarium, sehingga lebih baik menggunakan istilah aslinya agar tidak membingungkan konteks teknis.
- `researcher` → `researcher` (not added): Term 'researcher' not found in glossary and contextually it refers to a specific role or identity in a technical setting, so the English term is preserved.
- `risk metadata` → `metadata risiko` (not added): Translated based on common Indonesian technical terminology to describe metadata related to risk.
- `operator prompt` → `prompt operator` (not added): Translated by combining the glossary term 'prompt' with 'operator' to fit the context.
- `thread` → `thread` (not added): Not found in glossary and commonly used as a technical term in Indonesian IT contexts, so it is preserved in English.

## Run diagnostics

| Role | Item | OK | Seconds | Tool calls | Error |
| --- | --- | --- | --- | --- | --- |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | yes | 82.4 | 28 |  |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | no | 8.6 | 0 | task-context capacity refusal: OpenMinion returned its canned 'could not safely update the task conditions' reply (input over the 12,000-character task limit) … |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | no | 16.0 | 1 | AgentOutputValidationError: Reply did not validate against TranslationBatch: 1 validation error for TranslationBatch Invalid JSON: expected value at line 1 col… |
| translate | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | yes | 7.1 | 0 |  |
| review | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | yes | 5.2 | 0 |  |
| review | README.md [quick-start::p1, quick-start::p2, what-openminion-does-not… | yes | 5.1 | 0 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p1] | no | 23.9 | 0 | task-context capacity refusal: OpenMinion returned its canned 'could not safely update the task conditions' reply (input over the 12,000-character task limit) … |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p1] | yes | 36.5 | 1 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p1] | yes | 8.6 | 0 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 75.7 | 1 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 4.9 | 0 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p2, st… | yes | 5.8 | 0 |  |
| translate | docs/getting-started.md [start-a-local-human-plus-agents-room::p4] | yes | 23.7 | 1 |  |
| review | docs/getting-started.md [start-a-local-human-plus-agents-room::p4] | yes | 5.3 | 0 |  |
| translate | docs/runtime-surfaces.md [2-python-library-api::p1, 2-python-library-… | yes | 37.9 | 0 |  |
| review | docs/runtime-surfaces.md [2-python-library-api::p1, 2-python-library-… | yes | 7.2 | 0 |  |
| review | docs/runtime-surfaces.md [2-python-library-api::p1, 2-python-library-… | yes | 9.6 | 0 |  |
| translate | docs/turn-budgets.md [automatic-fact-extraction] | yes | 38.8 | 1 |  |
| review | docs/turn-budgets.md [automatic-fact-extraction] | yes | 17.1 | 0 |  |
| translate | docs/turn-budgets.md [maintainer-assessment-for-issue-497] | yes | 38.5 | 1 |  |
| translate | docs/turn-budgets.md [maintainer-assessment-for-issue-497] | yes | 31.7 | 0 |  |
| review | docs/turn-budgets.md [maintainer-assessment-for-issue-497] | yes | 10.6 | 0 |  |
| translate | docs/configuration-compatibility.md [configuration-compatibility-note… | yes | 46.4 | 2 |  |
| review | docs/configuration-compatibility.md [configuration-compatibility-note… | yes | 8.6 | 0 |  |
| translate | examples/sdk/README.md [example-map, handoff-approval] | yes | 44.5 | 4 |  |
| review | examples/sdk/README.md [example-map, handoff-approval] | yes | 12.3 | 0 |  |
| glossary | Bare | yes | 10.3 | 0 |  |
| glossary | read-only | yes | 6.8 | 0 |  |
| glossary | preset | yes | 5.9 | 0 |  |
| glossary | researcher | yes | 7.2 | 0 |  |
| glossary | risk metadata | yes | 6.3 | 0 |  |
| glossary | operator prompt | yes | 6.1 | 0 |  |
| glossary | thread | yes | 6.8 | 0 |  |
