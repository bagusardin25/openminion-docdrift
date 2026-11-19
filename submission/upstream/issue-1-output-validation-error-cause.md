# AgentOutputValidationError reports "Invalid JSON" when the recovered JSON object fails the schema

## Summary

`Agent._coerce_output` first validates the raw reply text. If that fails, it
recovers the first JSON object from the text and validates again. When the
second validation also fails, the second error is discarded and the **first**
error is raised. Replies are prefixed with `"<agent>: "`
(`services/brain/post_execution/postprocess_response.py:276`), so the first
error is always `json_invalid ... line 1 column 1`. The real problem, for
example a missing field, never reaches the caller.

## Affected version / environment

- openminion 0.1.23 (PyPI), Python 3.12, Windows 11
- provider: `openai` preset, `gpt-4.1-mini`

## Steps to reproduce

```python
from pydantic import BaseModel
from openminion import Agent, AgentOutputValidationError

class Reply(BaseModel):
    sentiment: str
    summary: str

class FakeRuntime:  # same shape as tests/api/test_agent.py::_FakeRuntime
    ...  # returns 'agent: {"sentiment": "neutral"}'

try:
    Agent(output_type=Reply, runtime=FakeRuntime()).run("evaluate")
except AgentOutputValidationError as exc:
    print(exc.validation_error.errors())
```

A complete version is the new test
`test_agent_reports_schema_error_of_recovered_json_object` in the linked PR.

## Expected

`validation_error.errors()` is `[("missing", ("summary",))]`, and the message
names the missing field.

## Actual

`validation_error.errors()` is `[("json_invalid", ())]` and the message is
`Invalid JSON: expected value at line 1 column 1`.

## Impact

We saw this in a live run. The model returned
`docdrift: {"claims_verification": [...]}`, which uses the wrong top-level key.
The exception said the JSON was invalid, so we spent time debugging JSON
formatting when the real cause was a schema mismatch.

## Suggested fix

Keep the recovered object's `ValidationError` when one exists, and raise with
it (`from` it). Patch: `0001-agent-output-validation-error-cause.patch` (+14 test
lines; `tests/api/test_agent.py` 50 passed). The new test fails on 0.1.23 with
`json_invalid` and passes with the patch.
