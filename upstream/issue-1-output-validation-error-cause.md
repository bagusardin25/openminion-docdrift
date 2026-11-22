## Summary

`Agent._coerce_output` first validates the raw reply text. If that fails, it
recovers the first JSON object from the text and validates again. When the
second validation also fails, its error is discarded and the **first** error is
raised.

Replies reach `_coerce_output` with the `"<agent>: "` prefix
(`services/brain/post_execution/postprocess_response.py:276`, see #567), so the
first error is always `json_invalid ... expected value at line 1 column 1`. The
real problem, for example a missing field in the recovered object, never
reaches the caller.

## Environment

- openminion 0.1.23 (PyPI), Python 3.12, Windows 11
- provider preset `openai`, model `gpt-4.1-mini`

## Reproduce (no provider needed)

With the `_FakeRuntime` and `_ReplyModel` helpers from `tests/api/test_agent.py`:

```python
def test_agent_reports_schema_error_of_recovered_json_object() -> None:
    reply = 'agent: {"sentiment": "neutral"}'  # "summary" is missing
    agent = Agent(output_type=_ReplyModel, runtime=_FakeRuntime(reply))
    with pytest.raises(AgentOutputValidationError) as exc_info:
        agent.run("evaluate")
    errors = exc_info.value.validation_error.errors()
    assert [(e["type"], e["loc"]) for e in errors] == [("missing", ("summary",))]
```

## Expected

`validation_error.errors()` is `[("missing", ("summary",))]`, and the
exception message names the missing field.

## Actual (0.1.23)

`validation_error.errors()` is `[("json_invalid", ())]`, and the message is
`Invalid JSON: expected value at line 1 column 1`.

## Impact

We hit this in a live run. The model returned `docdrift: {"claims_verification": [...]}`,
which used the wrong top-level key. The exception said the JSON was invalid, so
we debugged JSON formatting when the real cause was a schema mismatch. We now
re-validate the recovered object ourselves only to get a usable error message.

## Suggested fix

Keep the recovered object's `ValidationError` when there is one:

```diff
             try:
                 return cast(OutputT, self.output_type.model_validate_json(text))
             except ValidationError as exc:
-                # Some providers wrap JSON answers in prose; recover the first
-                # balanced object before failing validation.
-                stripped = _extract_json_object(text)
-                if stripped:
-                    try:
-                        return cast(OutputT, self.output_type.model_validate_json(stripped))
-                    except ValidationError:
-                        pass
-                raise AgentOutputValidationError(
-                    f"Reply did not validate against {self.output_type.__name__}: {exc}",
-                    raw_text=text,
-                    validation_error=exc,
-                ) from exc
+                error = exc
+            # Some providers wrap JSON answers in prose; recover the first
+            # balanced object before failing validation. When an object is
+            # recovered, its validation error explains the failure.
+            stripped = _extract_json_object(text)
+            if stripped:
+                try:
+                    return cast(OutputT, self.output_type.model_validate_json(stripped))
+                except ValidationError as exc:
+                    error = exc
+            raise AgentOutputValidationError(
+                f"Reply did not validate against {self.output_type.__name__}: {error}",
+                raw_text=text,
+                validation_error=error,
+            ) from error
```

With this change and the test above, `tests/api/test_agent.py` passes (50
tests). The new test fails on 0.1.23 and passes with the change. The change
and test are ready, and I will open a PR if the fix is in scope.

---

Found while building a Cortensor Hackathon #5 project on the OpenMinion 0.1 SDK:
https://github.com/bagusardin25/openminion-docdrift
