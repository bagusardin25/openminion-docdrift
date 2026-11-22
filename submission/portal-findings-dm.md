Hi Cortensor team, I'm a Hackathon #5 builder (project: DocTwin, https://github.com/bagusardin25/openminion-docdrift).

I tested Cortensor Portal and Gemma4 with OpenMinion 0.1.23, following the Portal Quick start, and wanted to share the results directly:

- Direct API calls work: tool calls, forced tool_choice, and OpenMinion's exact request all succeeded in 17–124 s (oss-20b and gemma4).
- Full OpenMinion turns did not complete in 7 runs. The two Portal-side issues:
  1. Intermittent stalls of 5–15 min with no response (4 of 7 runs, with and without connection reuse).
  2. Schema-invalid tool arguments return HTTP 502 ("Model tool arguments do not match the advertised schema", gw-743094d3-c753-4916-8ce1-9f33dba81f63), which looks like an outage and counts toward quota.

Full details, every run and request IDs: https://github.com/bagusardin25/openminion-docdrift/blob/main/WHAT_WE_LEARNED.md (Part D)

Is there a recommended timeout, or a known gateway issue right now? Happy to rerun anything. Thank you!
