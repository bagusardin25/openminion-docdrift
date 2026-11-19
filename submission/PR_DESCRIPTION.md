# [Hackathon #5] feat(apps): add DocDrift — checks OpenMinion docs against the installed SDK

## What it is

DocDrift is an OpenMinion 0.1 agent that answers one repeatable question:
*if I follow the OpenMinion docs with the `openminion` I have installed, what
breaks, and which written claims are no longer true?*

- **Repository:** <REPO_URL>
- **Demo video (1–5 min):** <VIDEO_URL>
- **openminion:** 0.1.23 (PyPI) · **provider:** `openai` / `gpt-4.1-mini`
  (config-only switch to Gemini or `cortensor-portal`)

## OpenMinion SDK workflow

1. `docdrift scan` (no model): 165 doc snippets checked against the installed
   CLI (`--help` for 58 command paths), the package (AST: imports, kwargs,
   methods), and `OPENMINION_*` env vars.
2. Triage `Agent` (6 `READ_ONLY` tools, `output_type=TriageBatch`) labels each
   candidate: real drift, out of scope, or false positive.
3. Claims `Agent` pulls checkable claims out of prose and verifies them in the
   installed source, citing file:line.
4. `subagent` reviewer independently re-checks every negative verdict.
5. Issue-writer `Agent` (`forced_tools`) drafts GitHub issues. Each write is
   paused by the action policy and answered through `approval_callback`.

One OpenMinion session per run. Every turn's seconds, tool calls, `run_id` and
errors land in the report.

## Checklist

- [x] Public repo + README with setup and run instructions
- [x] Explanation of the OpenMinion SDK workflow (README → "How the OpenMinion SDK is used")
- [x] One working example + 1–5 minute demo video
- [x] Building Blocks Tested: `BUILDING_BLOCKS.md`
- [x] What We Learned: `WHAT_WE_LEARNED.md`
- [ ] Bug report + fix PR: <ISSUE_URL> / <FIX_PR_URL>

## Result on 0.1.23

There is no doc drift. All 165 snippets match, all 5 env-var candidates are
test-suite settings, and none of the 19 checked claims is contradicted. Against
0.1.10 and 0.1.15 the same docs show real drift (`--runs-limit`,
`HTTPTransport`). Getting a trustworthy agent verdict took three runs. In run 1,
the triage agent and its same-model reviewer agreed on 4 false findings. The
fix was to hand the model deterministic facts and make the reviewer try to
disprove each finding.

## Highlights of the findings

- `Agent(output_type=...)` never sends the schema to the provider. Measured
  JSON compliance with `gpt-4.1-mini` was 0/4 without tools and 2/4 with tools.
  It reached 100% once the schema was placed in the user turn.
- `AgentOutputValidationError` hides the real schema error behind
  `json_invalid` (fix PR above).
- Reply text carries a `"<agent>: "` prefix. `tools=None` exposes the runtime's
  default tools. A one-tool question costs about 7 provider calls.

Full details with file:line evidence are in `WHAT_WE_LEARNED.md`.
