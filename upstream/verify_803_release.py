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
