# Demo video script (target 3–4 minutes)

Record the terminal full-screen with a large font (VS Code terminal or Windows
Terminal at ~18pt). Windows: `Win+Alt+R` (Xbox Game Bar) records the active
window; OBS works too. Narrate in English or Indonesian, or add on-screen
captions using the text in quotes below.

Before recording:

```powershell
cd D:\Project\docdrift
uv sync
uv run docdrift fetch
# Delete the old report so "new since last run" does not show up mid-demo:
Remove-Item out\report.* -ErrorAction SilentlyContinue
```

---

## 0:00 – 0:20 · The problem

Show the README top section.

> "OpenMinion shipped 23 releases in its 0.1 line. People pin a version and
> read docs written for main. DocDrift is an OpenMinion agent that checks
> whether the docs still tell the truth about the SDK you actually installed."

## 0:20 – 1:00 · Deterministic scan (no model)

```powershell
uv run docdrift scan
```

> "First, a deterministic pass. 165 snippets: every `openminion` command is
> checked against the real `--help`, every Python snippet against the installed
> package, every OPENMINION_* env var against the source. On 0.1.23 the code
> examples are clean. Only five env-var mentions need judgement."

Then show that it catches real drift against an older install:

```powershell
uv run --isolated --no-project --python 3.12 --with "openminion==0.1.10" --with-editable . docdrift scan --docs .cache/openminion-v0.1.23
```

> "Against 0.1.10, the same docs reference a `--runs-limit` flag and an
> `HTTPTransport` class that don't exist yet. That's what you'd hit after
> pinning an older version."

## 1:00 – 2:40 · The agent run (real model)

```powershell
uv run docdrift run --max-claims 4
```

It takes about 4–5 minutes. Either speed up the middle when editing, or start
it before the scan segment and come back. While it runs, point out each stage
as it prints:

> "Step 2: the triage agent uses six read-only OpenMinion tools to decide
> whether each candidate is real drift or just a test-suite variable. All five
> are test-suite variables. In our first run the agent got four of them wrong,
> so DocDrift now hands it deterministic facts about where each name is used."
>
> "Step 3: the claims agent reads prose sections, pulls out checkable claims
> like defaults and limits, and verifies them in the installed source."
>
> "Step 4: an OpenMinion subagent re-checks every negative verdict and is told
> to try to disprove it."

Then show the approval gate (about 30 s):

```powershell
uv run docdrift approval-check
```

> "Writing an issue draft is a write, so OpenMinion's action policy pauses it
> and calls our approval callback. Denied: no file. Approved: the draft is
> written."

## 2:40 – 3:30 · The result

```powershell
code out\report.md      # or: notepad out\report.md
```

Scroll through: Summary, Confirmed/Disputed, Verified claims with file:line
evidence, and Run diagnostics (seconds and tool calls per turn).

> "Every claim cites file and line in the installed package. The diagnostics
> table is how we found our own OpenMinion feedback."

Open `WHAT_WE_LEARNED.md` for a few seconds:

> "Building it, we found that `output_type` never sends the schema to the
> model, plus a validation error that hides its real cause. We sent a fix PR
> for that one."

## 3:30 – 3:45 · Close

> "DocDrift: a small, repeatable OpenMinion agent that keeps the docs honest.
> Source and setup are in the README."
