# [Hackathon #5] feat(apps): add DocTwin — translated docs that stay in sync and stay correct (OpenMinion 0.1)

## What it is

DocTwin is a set of OpenMinion 0.1 agents that keep a translated copy of a docs
tree a faithful, up-to-date twin of the English source. Only changed sections
are re-translated. Code, links and commands are protected byte for byte.
Deterministic gates and a reviewer subagent catch wrong translations, and a
human approves every new glossary term. DocDrift, our first prototype and now
the safety net, checks every command and import in the output against the
installed SDK.

- **Repository:** https://github.com/bagusardin25/openminion-docdrift
- **Demo video (1–5 min):** <VIDEO_URL>
- **openminion:** 0.1.23 (PyPI) · **provider:** `openai` / `gpt-4.1-mini`
  (config-only switch to Gemini or `cortensor-portal`)
- **Real output:** the OpenMinion docs in Bahasa Indonesia, synced from v0.1.18
  to v0.1.23: [`translations/id/`](translations/id/)

## OpenMinion SDK workflow

1. Split the docs into sections. The ledger finds what changed since the last
   sync.
2. Protect code, inline code, URLs, HTML and quoted program output as
   placeholders.
3. Translator `Agent` (`output_type=TranslationBatch`, `glossary_lookup`
   `READ_ONLY` tool).
4. Deterministic gates: placeholders, heading level, numbers, list items, table
   shape, glossary, length. One retry with the errors quoted back.
5. Reviewer `subagent` (skeptical, `output_type=ReviewBatch`). One repair, then
   "needs review".
6. Glossary keeper `Agent` with `forced_tools`: `add_glossary_term` runs only
   after `approval_callback` approves it.
7. DocDrift scan of the output: `--help` for every command, AST check of every
   import.

## Results

| Sync | Sections | Sent to the model | Reused | Kept in English |
| --- | --- | --- | --- | --- |
| initial (v0.1.18) | 47 | 47 | 0 | 2 (gate refused a decimal-comma rewrite and a dropped section) |
| update (→ v0.1.23) | 54 | 14 | 40 | 0 |

Code blocks were byte-identical in every file, and DocDrift found no broken
command or import.

## Checklist

- [x] Public repo + README with setup and run instructions
- [x] Explanation of the OpenMinion SDK workflow (README → "How a sync works", "How the OpenMinion SDK is used")
- [x] One working example + 1–5 minute demo video
- [x] Building Blocks Tested: `BUILDING_BLOCKS.md`
- [x] What We Learned: `WHAT_WE_LEARNED.md`
- [x] Bug reports: https://github.com/openminion/openminion/issues/803 and https://github.com/openminion/openminion/issues/804
- [x] Fix PR for #803, opened after the maintainer confirmed it in scope, then approved and merged into `dev` (2026-11-20, all 18 hosted checks passing): https://github.com/openminion/openminion/pull/810

## Highlights of the findings (details with file:line in WHAT_WE_LEARNED.md)

- `Agent(output_type=...)` never sends the schema to the model. JSON compliance
  was 0/4 without tools and 2/4 with tools until the schema went into the user
  turn.
- A user message over 12,000 characters returns a canned "could not safely
  update the task conditions" reply with `run_state="completed"`. Before we
  found the limit, 10 of 36 turns in one run failed this way.
- `AgentOutputValidationError` reports `json_invalid` when the real problem is a
  schema mismatch (fix PR above).
- Same-model self-review rubber-stamped 4 false findings. Giving the reviewer
  deterministic facts and asking it to disprove fixed it (5/5 correct
  afterwards).
