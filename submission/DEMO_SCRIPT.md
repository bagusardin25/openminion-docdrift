# Demo video script (target ~3 minutes)

Total model cost of this script: **one sync of one section**, about two model
turns (~50k tokens on `gpt-4.1-mini`, roughly US$0.02). Every other step runs
locally without a model.

Record the terminal full screen with a large font (Windows Terminal or the VS
Code terminal at ~18 pt). `Win+Alt+R` (Xbox Game Bar) records the active window;
OBS also works. Narrate, or add the quoted lines as captions.

## Before recording (not on camera)

```powershell
cd D:\Project\docdrift
uv sync
uv run doctwin fetch --ref v0.1.23
uv run python scripts/make_demo_source.py     # v0.1.23 docs + one changed sentence, and a copy of the translations
```

Open these in a browser beforehand: `translations\id\.doctwin\preview.html`
(double-click the file) and this repo's README on GitHub.

---

## 0:00 – 0:25 · The problem

Show the README top section on GitHub.

> "Docs change every release. Translations fall behind, or break commands while
> translating them. DocTwin is a set of OpenMinion agents that keep a translated
> copy of the docs in sync with the English source, without breaking a single
> command, link or code block."

## 0:25 – 1:05 · It already did the real job

Show `translations\id\.doctwin\preview.html` (English left, Bahasa Indonesia
right). Scroll a little, and point at a code block and the green "translated"
chips.

> "We translated the OpenMinion docs into Bahasa Indonesia at v0.1.18, then
> synced to v0.1.23. Of 54 sections, only the 14 that changed went to the model.
> The other 40 were reused. Code blocks are byte-identical to the source in
> every file."

Open `docs\turn-budgets.md` in the preview and point at `33.76 s` in the table.

> "On the first sync, the translator turned 33.76 into the Indonesian 33,76. A
> number gate refused it, so that section stayed in English until a clean
> translation passed. Wrong numbers never ship."

## 1:05 – 2:15 · Live: the English docs change

```powershell
uv run doctwin plan --source .cache/demo-source --out .cache/demo-twin
```

> "One sentence changed upstream. The ledger knows exactly which section that
> is: 1 of 54."

```powershell
uv run doctwin sync --source .cache/demo-source --out .cache/demo-twin --terms ask
```

While it runs:

> "The changed section is protected first: code, inline code and links become
> placeholders the model cannot touch. The translator agent works with a
> glossary tool. Deterministic gates check placeholders, headings, numbers,
> lists and glossary terms. Then a skeptical reviewer subagent checks the
> meaning. If the translator proposes a new term, OpenMinion's action policy
> pauses and asks me before the glossary file is written."

If an approval prompt appears, answer `y` once and `n` once. At the end, DocDrift
validates every command and import in the output.

```powershell
code .cache\demo-twin\.doctwin\report.md
```

> "1 translated, 53 reused, 0 need review. Code blocks identical. No broken
> commands."

## 2:15 – 2:45 · Respecting humans

```powershell
Add-Content .cache\demo-twin\docs\provider-capabilities.md "`nCatatan dari editor manusia."
uv run doctwin sync --source .cache/demo-source --out .cache/demo-twin --terms skip --no-validate
```

> "A human edited a translated file. DocTwin notices and leaves it alone, so
> hand edits are never overwritten."

(Every section is already in sync at this point, so this sync makes no model
call.)

## 2:45 – 3:10 · What we found in OpenMinion

Open `WHAT_WE_LEARNED.md` and scroll through Part A, then open
https://github.com/openminion/openminion/pull/810 and show the green
"Merged" badge and the maintainer's approval.

> "Building it, we found that `output_type` never sends the schema to the
> model, that a user message over 12,000 characters comes back as a canned
> reply marked completed, and that validation errors hide their real cause. We
> reported that last one as issue 803. The maintainers confirmed it, and our fix
> PR, 810, passed all 18 CI checks and was merged into OpenMinion. DocDrift,
> our first prototype, now checks the commands in every translation."

## 3:10 · Close

> "DocTwin: translated docs that stay in sync and stay correct. Built on
> OpenMinion."
