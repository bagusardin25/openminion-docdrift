# DocTwin

Keep translated docs in sync with the English source, without breaking a single
command, link or code block.

Built on the OpenMinion 0.1 Python SDK for Cortensor Hackathon #5.

## Why

Docs change with every release. Translations don't keep up, and when someone
does re-translate a page, a command or a number often gets "translated" too. A
stale or subtly wrong translation is worse than none.

DocTwin does one job, repeatably: when the English docs change, it updates the
translation only where the source changed, guarantees the code survives
untouched, and tells a human exactly which parts still need their eyes.

To prove it on something real, we translated the OpenMinion docs into Bahasa
Indonesia at v0.1.18, then synced them to v0.1.23:

| Sync | Sections | Sent to the model | Reused | Kept in English |
| --- | --- | --- | --- | --- |
| initial (v0.1.18, 6 files) | 47 | 47 | 0 | 2 |
| update to v0.1.23 (7 files) | 54 | **14** | **40** | 0 |

Across both syncs every code block, link and heading matched the source
exactly, and no command or import in the output was broken. The result is in
[`translations/id/`](translations/id/), with a report for each sync under
`translations/id/.doctwin/reports/`.

The two sections "kept in English" are the part we like most. On the first
sync the model turned `33.76` into `33,76` (the Indonesian decimal comma) in a
table of measurements, and dropped one section from its answer. The gates
refused both, so those sections stayed in English instead of shipping wrong.
Both went through cleanly on the next sync.

## How a sync works

```
English docs (any git ref)
   │
   ├─ split into sections, compare with the ledger ──► unchanged sections are reused
   │
   ▼  changed sections only
 protect    code, inline code, URLs, HTML and quoted program output become
            placeholders (⟦CODE1⟧, ⟦IC2⟧, ...) the model cannot touch
 translate  translator agent, with a glossary lookup tool
 gate       placeholders, heading level, numbers, list items, table shape,
            glossary terms, length. Fail → one retry with the errors quoted back
 review     a skeptical reviewer subagent checks meaning, negations, numbers.
            Reject → one repair attempt, then the section is marked "needs review"
 write      placeholders restored byte for byte, file written, ledger updated
 glossary   new terms are proposed by the model and written only if a human approves
 validate   DocDrift checks every command and import in the output against the SDK
```

A few things follow from this design:

- **The model never sees code**, so it cannot break it. Each report also
  verifies that code blocks are byte-identical to the source.
- **Only changed sections cost anything.** Section digests live in
  `.doctwin/ledger.json`.
- **Hand edits are respected.** If a person edits a translated file, DocTwin
  notices and leaves that file alone unless you pass `--force`.
- **Nothing wrong is accepted quietly.** A section that fails the gates stays in
  English. A section the reviewer rejects is marked
  `<!-- doctwin: needs review -->` and listed in the report.

## Try it

You need Python 3.12+, [uv](https://docs.astral.sh/uv/), git, and an OpenAI or
Gemini API key.

```bash
git clone https://github.com/bagusardin25/openminion-docdrift.git doctwin && cd doctwin
uv sync
cp .env.example .env                    # add OPENAI_API_KEY (or GEMINI_API_KEY)
uv run docdrift init --provider openai  # writes .openminion/agents.json; the key stays in .env

uv run doctwin fetch --ref v0.1.23
uv run doctwin plan --source .cache/openminion-v0.1.23   # what would be translated (no model)
uv run doctwin sync --source .cache/openminion-v0.1.23   # translate, gate, review, write
```

The repo already contains the Indonesian translation and its ledger, so `plan`
reports nothing to do. To watch a real incremental sync for a few cents:

```bash
uv run python scripts/make_demo_source.py   # v0.1.23 docs with one sentence changed
uv run doctwin sync --source .cache/demo-source --out .cache/demo-twin
```

That re-translates exactly one section out of 54. Each sync writes
`report.md` and a side-by-side `preview.html` (English left, translation
right) into the `.doctwin/` folder of the output.

Useful options for `sync`: `--lang` (default `id`), `--file` to pick files,
`--terms ask|yes|no|skip` for glossary approvals, `--no-tools` for providers
with weak tool calling, `--dry-run`, and `--force`.

Tests need no API key: `uv run pytest`.

## What it uses from OpenMinion

| SDK feature | Where |
| --- | --- |
| `Agent` with `output_type` (Pydantic) | translator and reviewer return validated batches |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | `glossary_lookup` runs without prompts |
| default-scope `@tool` + `approval_callback` | `add_glossary_term` writes only after a human says yes |
| `forced_tools` | the glossary keeper must go through that approval-gated tool |
| `subagent` | the reviewer, with its own instructions, output type and timeout |
| sessions, `ProviderError`, `TurnTimeoutError`, `run_id` | one session per sync, and a per-turn diagnostics table in every report |

Providers are a config switch (`docdrift init --provider ...`); the agent code
does not change.

## DocDrift

The repo is called `openminion-docdrift` because that is where we started.
DocDrift checks docs against the installed SDK without a model: every
`openminion ...` command against the real `--help`, every Python snippet
against the installed package, every `OPENMINION_*` variable against the
source.

```bash
uv run docdrift fetch && uv run docdrift scan    # OpenMinion docs vs the installed SDK
uv run docdrift scan --docs path/to/project      # any project built on OpenMinion
uv run docdrift run                              # adds agent triage and claim checks
```

It found the 0.1.23 docs in good shape, and real drift when the same docs meet
older releases (0.1.10 and 0.1.15). Midway through we noticed another entry
doing similar checks, so DocDrift became the safety net for DocTwin: it
validates every translation. Its reports are in
[`evidence/docdrift/`](evidence/docdrift/).

## What we found along the way

Details, with file and line references, are in
[WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md). Per-feature results are in
[BUILDING_BLOCKS.md](BUILDING_BLOCKS.md).

- **`AgentOutputValidationError` hid the real cause of a failure.** Reported as
  [openminion#803](https://github.com/openminion/openminion/issues/803). The
  maintainers confirmed it, and our fix,
  [openminion#810](https://github.com/openminion/openminion/pull/810), was
  merged into `dev`.
- **A user message over 12,000 characters returns a canned reply marked
  `completed`.** Reported as
  [openminion#804](https://github.com/openminion/openminion/issues/804), where
  the maintainer also corrected part of our analysis.
- **`Agent(output_type=...)` never sends the schema to the model.** We measured
  how often replies were valid with and without our workaround.
- **One model reviewing itself rubber-stamps.** Our first reviewer confirmed
  four findings that were all wrong. Handing it deterministic facts and asking
  it to disprove fixed that.

### Cortensor Portal and Gemma4

We tested Portal with a free-plan key, following its Quick start
(`docdrift init --provider cortensor-portal --model oss-20b --agent docdrift-portal`).
Called directly, the API works: tool calls, forced `tool_choice`, and even the
exact request OpenMinion sends, on both `oss-20b` and `gemma4`. Full OpenMinion
turns did not complete in seven attempts. We hit intermittent stalls, a
gateway 502 for schema-invalid tool arguments, and prose instead of JSON. So
the syncs in this repo ran on `gpt-4.1-mini`. Every run, with request IDs, is
in [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md) Part D, and the raw logs are in
[`evidence/portal/`](evidence/portal/).

## Repository

```
src/doctwin/     sync, gates, ledger, glossary, agents, preview
src/docdrift/    command, snippet and env-var checks, plus the triage agents
tests/           20 tests, no model needed
translations/    the Indonesian docs DocTwin produced, with ledger and reports
evidence/        logs and reports from the real runs
upstream/        the issue texts and patch we sent to OpenMinion
scripts/         demo helper
```

The translations are unofficial. Attribution for the Apache-2.0 originals is in
[`translations/NOTICE.md`](translations/NOTICE.md).

## License

MIT
