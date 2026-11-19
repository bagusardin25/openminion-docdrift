# DocDrift

**An OpenMinion agent that checks whether OpenMinion's own documentation still
matches the SDK and CLI you actually installed.**

Built for Cortensor Hackathon #5 with the OpenMinion 0.1 Python SDK.

OpenMinion shipped 23 releases in the 0.1 line. People pin a version, then read
docs written for `main`. DocDrift answers one repeatable question:

> *If I follow these docs with the `openminion` I have installed, what will break,
> and which written claims are no longer true?*

## What it does

```
            OpenMinion docs (git tag that matches your install)
                               │
   ┌───────────────────────────┴────────────────────────────┐
   │ 1. scan  (deterministic, no model)                      │
   │    • every `openminion ...` command → real `--help`     │
   │    • every Python snippet / example → imports, kwargs,  │
   │      methods resolved against the installed package     │
   │    • every OPENMINION_* env var → grep installed source │
   └───────────────────────────┬────────────────────────────┘
                               │ candidates + evidence.json
   ┌───────────────────────────┴────────────────────────────┐
   │ 2. triage agent    real_drift / out_of_scope / false_+ │
   │ 3. claims agent    reads prose, extracts checkable     │
   │                    claims, verifies them in source      │
   │ 4. reviewer        `subagent` re-checks every negative  │
   │                    verdict independently                │
   │ 5. issue writer    drafts GitHub issues, each write     │
   │                    paused for operator approval         │
   └───────────────────────────┬────────────────────────────┘
                               │
                 out/report.md · out/report.json · out/issues/*.md
```

All evidence tools are read-only (`@tool(min_scope="READ_ONLY", idempotent=True)`).
The only tool that writes, `write_issue_draft`, uses the default write scope, so
OpenMinion's action policy pauses it and asks you first. Nothing is posted to
GitHub.

## Quick start

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), git, and a model
provider key. The default is Gemini, which has a free tier.

```bash
git clone <this repo> docdrift && cd docdrift
uv sync
cp .env.example .env          # then put your GEMINI_API_KEY or OPENAI_API_KEY in .env
uv run docdrift init          # Gemini; or: uv run docdrift init --provider openai
                              # writes .openminion/agents.json (key stays in .env)
uv run docdrift fetch         # clones the OpenMinion docs at v<installed version>
uv run docdrift scan          # deterministic pass, no model, ~45 s
uv run docdrift run           # full agent pipeline -> out/report.md
```

On Windows PowerShell use `copy .env.example .env`.

Useful options:

| Option | Meaning |
| --- | --- |
| `scan --strict` | exit 1 when any candidate is found (CI gate before an upgrade) |
| `run --section "docs/x.md#Heading"` | verify claims in specific sections (repeatable) |
| `run --max-claims 5` | claims extracted per section |
| `run --issues ask\|yes\|no\|skip` | how issue-draft approvals are answered |
| `run --pace 5` | wait between model turns (free-tier rate limits) |
| `init --provider X --model Y` | any OpenMinion provider preset, e.g. `cortensor-portal` |
| `approval-check` | proves the approval gate with a synthetic finding (deny → no file, approve → file) |

### Check docs against a different installed version

DocDrift is most useful right before or after an upgrade. Run the same docs
against another `openminion` release without touching your project:

```bash
uv run --isolated --no-project --python 3.12 --with "openminion==0.1.10" --with-editable . \
  docdrift scan --docs .cache/openminion-v0.1.23
```

## Results

**Deterministic scan** (docs tag v0.1.23, 165 snippets: 20 Python, 145 shell):

| Installed | Candidates | What they are |
| --- | --- | --- |
| 0.1.23 | 5 | all `unknown_env_var`, and all used only by the repo's `tests/` / `.github/` |
| 0.1.15 | 6 | + `openminion.modules.a2a.transport.HTTPTransport` does not exist (`docs/a2a-remote.md:72`) |
| 0.1.10 | 8 | + `openminion tasks show --runs-limit` is not a flag (`docs/system-operations.md:215`) |

**Agent run on 0.1.23** (`gpt-4.1-mini`, run 3, [`out/report.md`](out/report.md)):
5/5 candidates correctly triaged `out_of_scope`; 19 claims checked in 4 doc
sections, 16 supported, 0 contradicted, 3 unverifiable; 9/9 model turns
succeeded in 4.1 minutes of model time. **No doc drift in 0.1.23.**

Getting there took three runs. In run 1, the triage agent and the reviewer
subagent agreed on four "drift" findings that were all wrong. The fixes, and
six pieces of SDK feedback found along the way (one with a fix PR), are in
[WHAT_WE_LEARNED.md](WHAT_WE_LEARNED.md). Per-feature results are in
[BUILDING_BLOCKS.md](BUILDING_BLOCKS.md).

## How the OpenMinion SDK is used

| SDK feature | Where | Why |
| --- | --- | --- |
| `Agent(config_path=..., agent_id=...)` | `agents.py` | provider-neutral: switch Gemini ↔ Cortensor Portal in config only |
| `@tool(min_scope="READ_ONLY", idempotent=True)` | `tools.py` | six evidence tools run without prompts |
| `@tool` default scope + `approval_callback` | `tools.write_issue_draft`, `cli._approval` | operator approves every file write |
| `output_type=<Pydantic model>` | triage, claims, reviewer | validated JSON verdicts, no regex parsing |
| `subagent(parent, ...)` | `agents.review` | bounded reviewer with its own instructions and timeout |
| `forced_tools=[...]` | issue writer | first action is always the draft write |
| `session_id` per run, new thread per item | every role | one inspectable OpenMinion session per DocDrift run |
| `ProviderError`, `TurnTimeoutError`, `AgentOutputValidationError`, `result.stats` | `agents._run` | every turn is logged in the report's *Run diagnostics* |

OpenMinion state (sessions, runs) stays inside the project in `.openminion/`.

## Project layout

```
src/docdrift/
  extract.py     fenced-block and example-file extraction with absolute lines
  cli_check.py   `openminion ... --help` walker (parallel, cached, sandboxed home)
  py_check.py    AST checks against the installed package
  env_check.py   OPENMINION_* env vars vs installed source
  scan.py        deterministic pass → candidates
  tools.py       OpenMinion tools (6 read-only + 1 approval-gated write)
  agents.py      triage / claims / reviewer subagent / issue writer
  report.py      report.md + report.json
  cli.py         docdrift init | fetch | scan | run
tests/           checker tests (no model needed): uv run pytest
```

## Limits

- Python checks are static. Methods on objects returned from calls (for example
  `result.output.x`) are not type-inferred.
- Claim verification is only as good as the model and its tool use. That is why
  every negative verdict goes through the reviewer subagent, and disputed items
  are reported separately instead of dropped.
- Doc pages about the repository's own test suite are in scope for scanning.
  The triage agent is expected to mark their env vars `out_of_scope`.

## License

MIT
