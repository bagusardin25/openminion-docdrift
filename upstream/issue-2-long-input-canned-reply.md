## Summary

When the user message passed to `Agent.run()` is longer than
`TASK_CONTEXT_MAX_CHARS = 12_000` (`modules/brain/constants.py:21`), the model
is never asked. The turn ends with the fixed text *"I could not safely update
the task conditions. Please restate the current task and its required
conditions."* and `run_state="completed"` and `metadata["respond_kind"] ==
"assistant"`. Callers cannot tell this apart from a real model answer, and
nothing is raised.

The visible symptom is the same as #719, but the trigger is different. #719 is
an invalid optional `task_update` from the model. Here the trigger is only the
input length: the verbatim objective exceeds `ResolvedTaskContext.objective`'s
`max_length` (`modules/brain/schemas/task_context.py:35`).

## Environment

openminion 0.1.23 (PyPI), Python 3.12, Windows 11, provider preset `openai`,
model `gpt-4.1-mini`.

## Reproduce

```python
from openminion import Agent

filler = "The quick brown fox jumps over the lazy dog. " * 400
for size in (11_500, 12_500):
    msg = "Reply with exactly the word PONG and nothing else.\n\n" + filler[: size - 60]
    with Agent(tools=[]) as agent:
        r = agent.run(msg)
    print(len(msg), r.run_state, r.metadata.get("respond_kind"), r.text[:60])
```

Output (the agent id prefix is from #567):

```
11492 completed assistant docdrift: PONG
12492 completed assistant docdrift: I could not safely update the task conditions. Ple
```

## Expected

Any one of these:
- a typed error, for example an `INVALID_ARGUMENT`-style exception that names
  the 12,000-character limit;
- a distinct `run_state` or `respond_kind` such as `input_too_long`;
- a fallback that keeps a truncated objective and still answers.

At minimum, the input limit should be documented next to `Agent.run`.

## Impact

Our translation agent sends documentation sections for translation and review.
Any batch over 12,000 characters silently "succeeded" with this text. With
`output_type=...` it then surfaced as `AgentOutputValidationError: Invalid
JSON`, which points in the wrong direction (#803). Before we found the limit,
10 of 36 turns in one run failed. All three failed replies we inspected were
this canned text.

We now keep requests under 11,000 characters, split batches, and treat the
canned text as a failure. That works, but any SDK user who sends long inputs
will run into this.

Separately, in a later run, 1 of 38 turns got the same reply for a
6,066-character message. We could not reproduce it, which fits #719's trigger.

---

Found while building a Cortensor Hackathon #5 project on the OpenMinion 0.1 SDK:
https://github.com/bagusardin25/openminion-docdrift
