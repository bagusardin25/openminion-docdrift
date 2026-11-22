Hi team! Portal testing notes from Hackathon #5 (DocTwin, OpenMinion 0.1.23, free-plan key, set up from the in-Portal Quick start, 2026-11-21). Full details: https://github.com/bagusardin25/openminion-docdrift/blob/main/WHAT_WE_LEARNED.md (Part D)

**Works when called directly** (`/v1/chat/completions`): tool calls, forced `tool_choice`, and the exact request OpenMinion sends (2,223 prompt tokens) all succeeded on `oss-20b` in 17–124 s. `gemma4` also returned a correct tool call in 62.5 s.

**Issues we hit** (7 full OpenMinion turns, none completed)
1. **Intermittent stalls.** In 4 of 7 runs a request hung for 5–15 min, ending with no response, a "server disconnected" at ~478 s, or our 900 s read timeout. It happened with and without HTTP connection reuse, on both tools and no-tools requests. Our small direct requests never stalled (7 of 7).
2. **502 for schema-invalid tool arguments.** "Model tool arguments do not match the advertised schema." came back as HTTP 502 (`gw-743094d3-c753-4916-8ce1-9f33dba81f63`). A 502 looks like an outage to clients, and upstream failures count toward free-plan quota. A 4xx/422 or a gateway retry would help clients tell a model mistake from an outage.
3. `qwen` stalled until our 300 s timeout on the same request that `gemma4` answered in 62.5 s.
4. `oss-120b` shows "supported, no capacity".
5. The Usage page first showed 200,000 tokens / 2 h and 2,000,000 / 7 days, and later "cap not published yet".

Successful request IDs, for reference: `gw-7135194f-8378-4c96-ac1c-dc2b971cfd28`, `gw-9a878a49-285b-4c3c-a498-8a738d55f0c9`, `gw-eb63dad5-616d-4e16-8f37-ab6f16659ff4`.

Is there a recommended timeout, or a known stall issue on the gateway right now? Happy to rerun anything if it helps. Thanks!
