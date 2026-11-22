Published-package check for the acceptance listed above. No provider was used: a controlled runtime returns one fixed reply body, and the actual `Agent.run` is called with a Pydantic `output_type`.

| Control | openminion 0.1.23 (PyPI) | openminion 0.1.24 (PyPI) |
| --- | --- | --- |
| wrapped schema-invalid JSON, `agent: {"sentiment": "neutral"}` | `json_invalid` (the reported behaviour) | `missing` at `summary` |
| raw schema-invalid JSON | `missing` at `summary` | `missing` at `summary` |
| non-JSON text | `json_invalid` | `json_invalid` |
| `__cause__` is `validation_error` | yes, all three | yes, all three |
| `raw_text` unchanged | yes, all three | yes, all three |
| healthy wrapped JSON and healthy raw JSON | both parse | both parse |

So 0.1.24 contains the #810 change, and the three failure controls plus the two healthy controls behave as specified.

Environment: Windows 11, Python 3.12.13. Each version was installed from PyPI into a fresh isolated environment with `uv run --isolated --no-project --python 3.12 --with "openminion==<version>" python verify_803_release.py`. Installed `api/agent.py` sha256 prefix: `2e178d5bb850b8f3` for 0.1.23 and `497de46baa39f534` for 0.1.24.

Limits: this is a controlled runtime on the installed package, not a live provider run. The reply prefix (#567) is unchanged and out of scope here.

<details>
<summary>verify_803_release.py</summary>

```python
"""Acceptance controls for openminion#803 on an installed package. Controlled runtime, no provider."""

import hashlib
import importlib.metadata as md
import inspect
import platform
import sys
from pathlib import Path

import openminion
from openminion import Agent, AgentOutputValidationError
from pydantic import BaseModel


class Reply(BaseModel):
    sentiment: str
    summary: str


class ControlledRuntime:
    """Returns one fixed reply body, the same shape the upstream fake runtime returns."""

    def __init__(self, body: str) -> None:
        self.body = body

    def run_turn(self, *, payload, progress_callback=None, **kwargs):
        return {
            "body": self.body,
            "id": "controlled-1",
            "metadata": {"request_id": "controlled-req-1"},
            "stats": {},
            "session_id": payload.get("session_id"),
        }

    def close(self) -> None:
        pass


dist = md.distribution("openminion")
agent_file = Path(inspect.getfile(Agent))
print(f"openminion {dist.version} | Python {platform.python_version()} | {platform.system()} {platform.release()}")
print(f"installed from: {Path(openminion.__file__).parent}")
print(f"api/agent.py sha256: {hashlib.sha256(agent_file.read_bytes()).hexdigest()[:16]}")
src = inspect.getsource(Agent._coerce_output)
print("fix present in _coerce_output source:", "recovered_exc" in src)

cases = [
    ("wrapped schema-invalid JSON", 'agent: {"sentiment": "neutral"}', [("missing", ("summary",))]),
    ("raw schema-invalid JSON", '{"sentiment": "neutral"}', [("missing", ("summary",))]),
    ("non-JSON text", "not json at all", [("json_invalid", ())]),
]
ok = True
for label, body, expected in cases:
    try:
        Agent(output_type=Reply, runtime=ControlledRuntime(body)).run("evaluate")
        print(f"[{label}] FAIL: no exception")
        ok = False
        continue
    except AgentOutputValidationError as exc:
        got = [(e["type"], tuple(e["loc"])) for e in exc.validation_error.errors()]
        checks = {
            "validation_error": got == expected,
            "chained cause": exc.__cause__ is exc.validation_error,
            "raw_text unchanged": exc.raw_text == body,
        }
        ok = ok and all(checks.values())
        print(f"[{label}] errors={got} | " + " | ".join(f"{k}: {'ok' if v else 'FAIL'}" for k, v in checks.items()))

for label, body in (
    ("healthy wrapped JSON", 'agent: {"sentiment": "neutral", "summary": "fine"}'),
    ("healthy raw JSON", '{"sentiment": "neutral", "summary": "fine"}'),
):
    r = Agent(output_type=Reply, runtime=ControlledRuntime(body)).run("evaluate")
    good = r.output == Reply(sentiment="neutral", summary="fine")
    ok = ok and good
    print(f"[{label}] output={r.output!r} -> {'ok' if good else 'FAIL'}")

print("RESULT:", "ALL CONTROLS PASS" if ok else "SOME CONTROLS FAILED")
sys.exit(0 if ok else 1)
```

</details>
