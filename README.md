# DocTwin

**OpenMinion agents that keep translated docs a faithful, up-to-date twin of the
English source.**

Built for Cortensor Hackathon #5 with the OpenMinion 0.1 Python SDK.

Open-source docs change every release; translations fall behind or break. A
translated page that is three releases old, or that "translated" a command
into something that no longer runs, is worse than no translation. DocTwin
answers one repeatable job:

> *The English docs changed. Update the translation, only where the source
> changed, without breaking a single command, link or code block, and tell a
> human exactly what still needs their eyes.*

Demo target: the OpenMinion docs, translated into **Bahasa Indonesia** and kept
in sync as OpenMinion moves from v0.1.18 to v0.1.23.

## Results (real runs, `gpt-4.1-mini`)

| Sync | Sections | Sent to the model | Reused | Kept in English | Model time |
| --- | --- | --- | --- | --- | --- |
| initial, OpenMinion docs **v0.1.18** (6 files) | 47 | 47 | 0 | 2 (gates refused them, see below) | 19.4 min |
| update to **v0.1.23** (7 files, one new) | 54 | **14** | **40** | 0 | 11.0 min |

In every file of every sync, code blocks, links and headings matched the
source exactly. DocDrift found no broken command or import in the output.
The two sections kept in English during the first sync were refused by the
gates: the translator rewrote `33.76` as `33,76` (Indonesian decimal comma) in
a table of measurements, and it dropped one section from its output twice.
Both translated cleanly in the update. The translated docs live in
[`translations/id/`](translations/id/). They are unofficial, and the
Apache-2.0 attribution is in [`translations/NOTICE.md`](translations/NOTICE.md).
The reports are in `translations/id/.doctwin/reports/`, one folder per sync.

## How a sync works

```
 English docs (any git ref)                       translations/<lang>/
          │                                                 ▲
          ▼                                                 │
 1. split into sections ──► ledger: which sections changed? ┤ unchanged sections
          │                                                 │ are reused as-is
          ▼ changed / new sections only                     │
 2. protect: code, inline code, URLs, HTML  →  ⟦CODE1⟧ ⟦IC2⟧ ⟦URL3⟧
          │      (the model never sees them, so it cannot break them)
          ▼
 3. translator agent (OpenMinion, glossary_lookup tool)
          ▼
 4. deterministic gates: placeholders exact · heading level · numbers ·
    list items · table shape · glossary terms · length ratio
          │ fail → one retry with the gate errors quoted back
          ▼
 5. reviewer subagent (skeptical, bilingual): meaning, negations, numbers
          │ reject → one repair attempt, then "needs review"
          ▼
 6. restore placeholders byte-for-byte, write the file, update the ledger
 7. glossary keeper agent: new terms are written only after human approval
 8. DocDrift: every command and import in the output checked against the SDK
```

What a human can rely on:

| Guarantee | How |
| --- | --- |
| Code blocks, inline code, links and HTML are byte-identical to the source | placeholders + a per-file check (`code blocks identical` in every report) |
| Only changed sections are re-translated | section digests in `.doctwin/ledger.json` |
| Hand edits to a translated file are never overwritten | the ledger stores each written file's digest; an edited file is skipped |
| Terminology stays consistent | `glossary.<lang>.json`, enforced by a gate; additions need approval |
| Nothing wrong is silently accepted | a section that fails gates stays in English; reviewer problems are marked `<!-- doctwin: needs review -->` and listed in the report |

## Quick start

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), git and an OpenAI or
Gemini key.

```bash
git clone https://github.com/bagusardin25/openminion-docdrift.git doctwin && cd doctwin
uv sync
cp .env.example .env                   # put OPENAI_API_KEY (or GEMINI_API_KEY) in .env
uv run docdrift init --provider openai # writes .openminion/agents.json; the key stays in .env

uv run doctwin fetch --ref v0.1.18     # English docs at an older release
uv run doctwin sync --source .cache/openminion-v0.1.18 --lang id

uv run doctwin fetch --ref v0.1.23     # the docs move on
uv run doctwin plan --source .cache/openminion-v0.1.23 --lang id   # what changed (no model)
uv run doctwin sync --source .cache/openminion-v0.1.23 --lang id   # only those sections
```

Output: `translations/id/` (the translated docs), `translations/id/.doctwin/report.md`
and `preview.html` (English and Indonesian side by side).

| Option | Meaning |
| --- | --- |
| `--lang es` / `pt` / `vi` / `zh` / any code | target language (glossary seed exists for `id`) |
| `--file docs/x.md` | which files to keep in sync (repeatable) |
| `--terms ask\|yes\|no\|skip` | how glossary additions are approved |
| `--max-chars N` | source + previous translation per model turn (default 5200) |
| `--force` | overwrite translated files a human edited |
| `--dry-run` | translate but do not write |

## How the OpenMinion SDK is used

| SDK feature | Where | Why |
| --- | --- | --- |
| `Agent(config_path, agent_id, tools=[...], output_type=...)` | translator, reviewer, glossary keeper | provider-neutral; switch OpenAI ↔ Gemini ↔ Cortensor Portal in config |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | `glossary_lookup` | runs without prompts |
| `@tool` default scope + `approval_callback` | `add_glossary_term` | a human approves every terminology decision |
| `forced_tools=[...]` | glossary keeper | the first action is the (approval-gated) write |
| `subagent(parent, ...)` | reviewer | bounded, own instructions/tools/output type |
| `output_type=<Pydantic>` | translation and review batches | validated JSON; see WHAT_WE_LEARNED §1 for the workaround we needed |
| `session_id` per sync, a new thread per turn | all roles | one inspectable OpenMinion session per sync |
| `ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`, `run_id`, `stats` | `docdrift.agents._run` | per-turn diagnostics in every report |

## DocDrift: the validation gate (and our first prototype)

`docdrift` is the second tool in this repo. It checks docs against the
installed SDK without a model: every `openminion ...` command against the
real `--help` (58 command paths), every Python snippet against the installed
package (imports, keyword arguments, methods), every `OPENMINION_*` variable
against the source. DocTwin runs it on its own output. It also works on its
own:

```bash
uv run docdrift fetch && uv run docdrift scan        # OpenMinion docs vs installed SDK
uv run docdrift scan --docs path/to/your/openminion/project   # any project built on OpenMinion
uv run docdrift run                                  # + agent triage, claim checks, reviewer
```

We started the hackathon with DocDrift as the main project. It found no drift
in OpenMinion 0.1.23 (the docs are in good shape), real drift when the same
docs meet older releases (0.1.10, 0.1.15), and six SDK issues. Then we found a
similar entry (DriftCheck), so we made DocDrift the safety net of something
nobody else was building. Its results are in [`out/report.md`](out/report.md).

## Running on Cortensor Portal

DocTwin is provider-neutral, so Portal is a config switch. Put your key in
`.env` as `CORTENSOR_API_KEY`, then:

```bash
uv run docdrift init --provider cortensor-portal --model oss-20b --agent docdrift-portal
uv run doctwin sync --source .cache/demo-source --out .cache/demo-twin --agent docdrift-portal --timeout 900
```

We tested it with a free-plan Portal key, following the Portal's own Quick
start. Direct API calls work: tool calls, forced `tool_choice`, and even
OpenMinion's exact captured request. Full OpenMinion turns did not complete
reliably on Portal yet. In seven runs we hit request stalls, a gateway 502 for
schema-invalid tool arguments, OpenMinion #719's canned task-update reply, and
prose instead of JSON. Each run, with request IDs and the mitigations we tried,
is in [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md) Part D. The real syncs in this
repo ran on `gpt-4.1-mini`.

## What we found in OpenMinion

Full details with file:line evidence in [WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md),
building-block results in [BUILDING_BLOCKS.md](BUILDING_BLOCKS.md). The short
version:

1. `Agent(output_type=...)` never sends the schema to the model.
2. `AgentOutputValidationError` reports `json_invalid` when the real problem is a
   schema mismatch: [openminion#803](https://github.com/openminion/openminion/issues/803).
   The maintainer confirmed it in scope, and our fix with regression tests,
   [openminion#810](https://github.com/openminion/openminion/pull/810), was
   **approved and merged into `dev`** on 2026-11-20 after all 18 hosted checks
   passed.
3. A user message over 12,000 characters comes back as a canned "could not safely
   update the task conditions" reply with `run_state="completed"`:
   [openminion#804](https://github.com/openminion/openminion/issues/804).

## Project layout

```
src/doctwin/    segment.py · gates.py · glossary.py · ledger.py · agents.py · sync.py · render.py · cli.py
src/docdrift/   extract.py · cli_check.py · py_check.py · env_check.py · scan.py · tools.py · agents.py · report.py · cli.py
tests/          uv run pytest   (no model needed)
scripts/        make_demo_source.py (cheap live demo) · invalidate_protect_change.py
translations/   the Indonesian twin of the OpenMinion docs, produced by DocTwin
submission/     demo script, PR text, upstream issue drafts and patch
```

## License

MIT
