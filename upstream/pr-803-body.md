- report the recovered object's `ValidationError` when the existing extractor recovers a JSON object from the reply and that object fails schema validation
- keep the original error otherwise: non-JSON replies still report their parse error, and raw invalid-schema JSON reports the same missing field as before
- keep `raw_text` unchanged; `__cause__` is the reported error and `__context__` still holds the first raw-text error
- add a parametrized test: the wrapped-object case discriminates (it fails on current `dev`), and the raw-object and non-JSON cases are neighbor controls that pass with and without the change
- no change to extraction rules, the reply prefix (#567) or the #804 outcome problem

Refs #803

Validation

- `python -m pytest -q tests/api/test_agent.py`: 52 passed. Without the source change, only `wrapped-object-schema-error` fails.
- `ruff check src/openminion/api/agent.py tests/api/test_agent.py`: all checks passed
- `ruff format --check src/openminion/api/agent.py tests/api/test_agent.py`: 2 files already formatted
- `mypy src/openminion/api/agent.py --follow-imports=silent --ignore-missing-imports`: 1 error before and after the change, pre-existing and outside the changed lines
- not run: `make lint`, `make typecheck`, `make check` (no `make dev-install` in this Windows environment)

Head `8a5e001` on base `dev` at `4204bbf`. Caller checked: `Agent._coerce_output` is used only by the run path at `src/openminion/api/agent.py:370`.

Contributor review

- [x] I followed [Code Quality and Hygiene](https://github.com/openminion/openminion/blob/dev/CODE_QUALITY.md), reviewed the complete final diff and each new delta, and recorded the head and caller/failure evidence for new layers, defensive checks, fallbacks or retries.
- [x] I removed unnecessary structure and redundant comments/docstrings in source, tests and scripts while preserving required validation, permissions, compatibility, persistence, replay, cleanup, public descriptions and notices/directives.
- [x] I updated affected public documentation and kept unrelated cleanup out of this PR. (No public documentation describes this error message.)
- [x] For brain or core changes, I traced the affected callers, stated any intended behavior change, and supplied positive and negative regression evidence for it and the neighboring contracts that must remain unchanged.
- [ ] For cleanup, I linked the current inventory and per-file dispositions, validation and remaining work; for merged-code findings, I checked surviving code and existing owners on current `dev`. (Not a cleanup PR.)
