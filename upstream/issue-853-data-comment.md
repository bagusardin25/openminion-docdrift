Adding reporter data on how often a live model misses the format, since that is the part noted above as not established. This is not a competing proposal, and the PR offer above stays with the reporter.

**Environment:** openminion 0.1.23 from PyPI, Windows 11, Python 3.12, `openai` preset, `gpt-4.1-mini`, live requests.

**Probe.** `instructions='Always end with ONLY this JSON: {"color_code": "<hex>", "marker": "PINEAPPLE-42"}. The marker must be the literal string PINEAPPLE-42.'`, `output_type` a two-field Pydantic model, message "What is the hex code of teal? Use the tool if you have one."

| Agent | Schema-valid replies | Invalid replies looked like |
| --- | --- | --- |
| no `tools=` | 0 of 4 | `The hex code of teal is #008080.` |
| one `READ_ONLY` `@tool` | 2 of 4 | `#008080` |

So the instructions spelled out the exact JSON, and that was still not enough in this probe.

**Outbound requests.** I captured the provider request bodies in-process by wrapping `ProviderHTTPClient.urlopen`. The instructions were present in a system message under `[IDENTITY]`, inside a runtime system prompt of 5,278 to 17,763 characters. No schema was present, which matches the source finding above.

**With the schema in the user message.** In a larger agent (multi-field batch models, read-only tools), appending `Model.model_json_schema()` to the user message gave 13 of 13, 9 of 10, and 9 of 9 valid structured turns across three real runs. The one failure was fixed by a single repair turn.

**Not separated.** I did not determine how much of the probe failure is the model not following `[IDENTITY]` instructions, and how much is a later runtime step rewriting an answer, as #720 and #726 describe. The bare `#008080` replies could be either.

One observation that may matter for the ordering question in the proposal: placement made the difference in these runs. The format request in `instructions` was not enough, and the same request at the end of the user message was. This is a small sample on one model.
