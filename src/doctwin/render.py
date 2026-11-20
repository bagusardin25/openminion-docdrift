"""Sync report (Markdown + JSON) and a side-by-side HTML preview."""

from __future__ import annotations

import html
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .ledger import Ledger
from .segment import split_sections

ACTION_LABEL = {
    "unchanged": "reused",
    "copied": "copied (code only)",
    "translated": "translated",
    "needs_review": "needs review",
    "unreviewed": "translated, not reviewed",
    "reviewed": "re-reviewed",
    "source_fallback": "kept in English",
}


def build(result, log, *, source_root: Path, validation: dict | None, seconds: float) -> dict:
    sections = [asdict(s) for s in result.sections]
    counts = Counter(s["action"] for s in sections)
    words = Counter()
    for s in sections:
        words[s["action"]] += s["words"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lang": result.lang,
        "source": str(source_root),
        "source_ref": result.source_ref,
        "session_id": log.session_id,
        "wall_seconds": round(seconds, 1),
        "counts": dict(counts),
        "words": dict(words),
        "files": [asdict(f) for f in result.files],
        "sections": sections,
        "glossary_proposals": result.proposals,
        "glossary_added": result.glossary_added,
        "validation": validation,
        "turns": [asdict(t) for t in log.turns],
    }


def _cell(text: str, limit: int = 140) -> str:
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def to_markdown(data: dict) -> str:
    c = data["counts"]
    w = data["words"]
    turns = data["turns"]
    model_seconds = sum(t["seconds"] for t in turns)
    total_sections = sum(c.values())
    reused = c.get("unchanged", 0) + c.get("copied", 0) + c.get("reviewed", 0)
    lines = [
        f"# DocTwin sync report ({data['lang']})",
        "",
        f"- **source:** `{data['source_ref']}`",
        f"- **generated:** {data['generated_at']}",
        f"- **OpenMinion session:** `{data['session_id']}`",
        "",
        "## Summary",
        "",
        "| | |",
        "| --- | --- |",
        f"| Sections | {total_sections} total: {reused} reused from the ledger, {c.get('translated', 0)} translated, "
        f"{c.get('needs_review', 0)} need review, {c.get('unreviewed', 0)} not reviewed, {c.get('source_fallback', 0)} kept in English |",
        f"| Words sent to the model | {w.get('translated', 0) + w.get('needs_review', 0) + w.get('source_fallback', 0)} "
        f"(reused without a model call: {w.get('unchanged', 0)}) |",
        f"| Model turns | {sum(1 for t in turns if t['ok'])}/{len(turns)} succeeded, {model_seconds / 60:.1f} min model time, "
        f"{data['wall_seconds'] / 60:.1f} min wall time |",
        f"| Code blocks byte-identical to source | "
        f"{'yes, every file' if all(f['code_blocks_identical'] in (True, None) for f in data['files']) else 'NO, see files table'} |",
    ]
    v = data.get("validation")
    if v:
        lines.append(f"| DocDrift check of commands and code in the translation | {v['summary']} |")
    lines += ["", "## Files", "", "| File | Status | Sections | Code blocks identical |", "| --- | --- | --- | --- |"]
    for f in data["files"]:
        ident = {True: "yes", False: "**no**", None: "-"}[f["code_blocks_identical"]]
        lines.append(f"| {f['file']} | {f['status']} | {f['sections']} | {ident} |")

    flagged = [s for s in data["sections"] if s["action"] in ("needs_review", "unreviewed", "source_fallback")]
    lines += ["", "## Needs a human", ""]
    if not flagged:
        lines.append("Nothing. Every changed section passed the gates and the reviewer.")
    for s in flagged:
        why = s["review_issues"] or s["gate_errors"] or ["the reviewer returned no verdict"]
        lines.append(f"- `{s['file']}` · `{s['key']}` · {ACTION_LABEL[s['action']]}: {_cell('; '.join(why), 300)}")

    retried = [s for s in data["sections"] if s["attempts"] > 1 and s["action"] == "translated"]
    lines += ["", "## Fixed automatically", ""]
    lines.append(
        f"{len(retried)} section(s) passed only after a retry that quoted the gate or reviewer problems back to the translator."
        if retried
        else "No section needed a retry."
    )

    lines += ["", "## Glossary", ""]
    if data["glossary_proposals"]:
        for p in data["glossary_proposals"]:
            mark = "added" if p["source"] in data["glossary_added"] else "not added"
            lines.append(f"- `{p['source']}` → `{p['target']}` ({mark}): {_cell(p['reason'], 160)}")
    else:
        lines.append("No new terms proposed.")

    lines += ["", "## Run diagnostics", "", "| Role | Item | OK | Seconds | Tool calls | Error |", "| --- | --- | --- | --- | --- | --- |"]
    for t in turns:
        lines.append(
            f"| {t['role']} | {_cell(t['label'], 70)} | {'yes' if t['ok'] else 'no'} | {t['seconds']:.1f} | {t['tool_calls']} | {_cell(t['error'], 160)} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(report_dir: Path, data: dict) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    md = report_dir / "report.md"
    js = report_dir / "report.json"
    js.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    md.write_text(to_markdown(data), encoding="utf-8")
    return md, js


LANG_LABELS = {"id": "Bahasa Indonesia", "es": "Español", "pt": "Português", "vi": "Tiếng Việt", "zh": "简体中文"}

# The page body is written as a fragment (title, style, markup, script) so the
# same text can be published as an artifact as-is; preview.html wraps it in a
# minimal document for opening locally.
FRAGMENT = """<title>DocTwin __LANGLABEL__</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a two-column reading desk (English left, translation right) under a
   compact status ledger; one fold per file, changed files open first. */
:root{
  --paper:#f5f6f8;--surface:#ffffff;--ink:#16202c;--muted:#5a6676;--rule:#dfe3e9;--accent:#1c5bbf;--code-bg:#edf0f4;
  --ok:#1b7a4c;--warn:#9d5800;--bad:#b3261e;
  --font-ui:"Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --font-mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#0e131a;--surface:#151c25;--ink:#e5eaf1;--muted:#97a2b2;--rule:#253040;--accent:#80aaff;--code-bg:#1c2430;
  --ok:#4cc38a;--warn:#f0a54a;--bad:#ff7b72;color-scheme:dark}}
:root[data-theme="dark"]{
  --paper:#0e131a;--surface:#151c25;--ink:#e5eaf1;--muted:#97a2b2;--rule:#253040;--accent:#80aaff;--code-bg:#1c2430;
  --ok:#4cc38a;--warn:#f0a54a;--bad:#ff7b72;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:15px/1.6 var(--font-ui)}
.wrap{max-width:1320px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
h1{font-size:clamp(24px,3.2vw,34px);line-height:1.15;margin:6px 0 6px;font-weight:700;text-wrap:balance}
.sub{color:var(--muted);font-size:14px}.sub code{font-family:var(--font-mono);font-size:13px}
.ledger{display:flex;flex-wrap:wrap;gap:10px 28px;margin:20px 0 8px;padding:14px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.ledger div{display:flex;align-items:baseline;gap:8px}.ledger b{font-size:22px;font-variant-numeric:tabular-nums}
.ledger span{color:var(--muted);font-size:13px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:2px 9px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.chip::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.s-new{color:var(--ok)}.s-reused{color:var(--muted)}.s-review{color:var(--warn)}.s-english{color:var(--bad)}
details{background:var(--surface);border:1px solid var(--rule);border-radius:10px;margin:0 0 14px;overflow:hidden}
summary{cursor:pointer;padding:12px 16px;display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-weight:600}
summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
summary .path{font-family:var(--font-mono);font-size:14px;font-weight:500}
.cols,.row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.cols{border-top:1px solid var(--rule);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.cols span{padding:8px 16px}.cols span+span{border-left:1px solid var(--rule)}
.row{border-top:1px solid var(--rule)}.row>div{min-width:0;padding:6px 16px 10px;overflow-wrap:anywhere}
.row>div+div{border-left:3px solid var(--state,var(--rule))}
.row .chip{margin:8px 0 2px}
.md h1,.md h2,.md h3,.md h4{line-height:1.25;margin:.8em 0 .4em}.md h1{font-size:22px}.md h2{font-size:19px}.md h3{font-size:16px}
.md p,.md li{max-width:68ch}.md a{color:var(--accent)}
.md code{font-family:var(--font-mono);font-size:.86em;background:var(--code-bg);padding:1px 5px;border-radius:5px}
.md pre{background:var(--code-bg);padding:10px 12px;border-radius:8px;overflow-x:auto}.md pre code{padding:0;background:none}
.md table{border-collapse:collapse;display:block;overflow-x:auto;max-width:100%}.md td,.md th{border:1px solid var(--rule);padding:4px 8px;text-align:left}
.md img{max-width:100%;height:auto}
@media (max-width:760px){.cols{display:none}.row{grid-template-columns:minmax(0,1fr)}.row>div+div{border-left:0;border-top:1px dashed var(--rule)}
  .row>div:first-child::before{content:"English";display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding-top:8px}}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto}}
</style>
<div class="wrap">
  <div class="eyebrow">DocTwin sync preview</div>
  <h1>English → __LANGLABEL__</h1>
  <div class="sub">Source <code>__REF__</code> · generated __WHEN__ · code blocks and links are byte-identical to the source. __SCOPE__</div>
  <div class="ledger">__STATS__</div>
  <div class="legend"><span class="chip s-new">translated in this sync</span><span class="chip s-reused">reused from the ledger</span><span class="chip s-review">needs a human</span><span class="chip s-english">kept in English</span></div>
  __FILES__
</div>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script>
document.querySelectorAll('[data-md]').forEach(function(el){try{el.innerHTML=marked.parse(el.textContent)}catch(e){}});
</script>"""

STANDALONE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{margin:0}</style>
__FRAGMENT__
</html>
"""


def preview(out_path: Path, source_root: Path, translations: Path, files: list[str], data: dict) -> Path:
    """Write preview.html (opens locally) and preview-artifact.html (publishable fragment)."""

    ledger = Ledger.load(translations / ".doctwin" / "ledger.json", data["lang"])
    actions = {(s["file"], s["key"]): s["action"] for s in data["sections"]}
    state_class = {
        "translated": ("s-new", "translated", "var(--ok)"),
        "reviewed": ("s-new", "re-reviewed", "var(--ok)"),
        "needs_review": ("s-review", "needs review", "var(--warn)"),
        "unreviewed": ("s-review", "not reviewed", "var(--warn)"),
        "source_fallback": ("s-english", "kept in English", "var(--bad)"),
        "unchanged": ("s-reused", "reused", "var(--rule)"),
        "copied": ("s-reused", "code only", "var(--rule)"),
    }
    lang_label = LANG_LABELS.get(data["lang"], data["lang"])
    full = _file_blocks(source_root, files, ledger, actions, state_class, lang_label, changed_only=False)
    changed = _file_blocks(source_root, files, ledger, actions, state_class, lang_label, changed_only=True)
    c = data["counts"]
    stats = "".join(
        f"<div><b>{n}</b><span>{html.escape(label)}</span></div>"
        for label, n in (
            ("sections translated", c.get("translated", 0)),
            ("reused without a model call", c.get("unchanged", 0) + c.get("copied", 0) + c.get("reviewed", 0)),
            ("need a human", c.get("needs_review", 0) + c.get("unreviewed", 0)),
            ("kept in English", c.get("source_fallback", 0)),
        )
    )

    def fill(blocks: str, scope: str) -> str:
        return (
            FRAGMENT.replace("__LANGLABEL__", html.escape(lang_label))
            .replace("__REF__", html.escape(data["source_ref"]))
            .replace("__WHEN__", html.escape(data["generated_at"].replace("T", " ").replace("+00:00", " UTC")))
            .replace("__SCOPE__", scope)
            .replace("__STATS__", stats)
            .replace("__FILES__", blocks)
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(STANDALONE.replace("__FRAGMENT__", fill(full, "Every section, side by side.")), encoding="utf-8")
    out_path.with_name("preview-artifact.html").write_text(
        fill(changed, "Only the sections this sync translated are shown; the rest were reused unchanged."), encoding="utf-8"
    )
    return out_path


def _file_blocks(source_root, files, ledger, actions, state_class, lang_label, changed_only: bool) -> str:
    blocks = []
    for file in files:
        src = source_root / file
        if not src.exists():
            continue
        rows = []
        for s in split_sections(src.read_text(encoding="utf-8")):
            state = ledger.section(file, s.key)
            target = state.text if state and state.source_digest == s.digest else s.text
            action = actions.get((file, s.key), "unchanged" if state else "source_fallback")
            klass, label, color = state_class.get(action, ("s-reused", action, "var(--rule)"))
            if changed_only and action in ("unchanged", "copied", "reviewed"):
                continue
            rows.append(
                f'<div class="row"><div><div class="md" data-md>{html.escape(s.text)}</div></div>'
                f'<div style="--state:{color}"><span class="chip {klass}">{label}</span>'
                f'<div class="md" data-md>{html.escape(target)}</div></div></div>'
            )
        changed = sum(1 for (f, _), a in actions.items() if f == file and a not in ("unchanged", "copied", "reviewed"))
        if changed_only and not changed:
            continue
        chip = f'<span class="chip s-new">{changed} changed</span>' if changed else '<span class="chip s-reused">unchanged</span>'
        blocks.append(
            f"<details{' open' if changed else ''}><summary><span class=\"path\">{html.escape(file)}</span>{chip}</summary>"
            f'<div class="cols"><span>English source</span><span>{html.escape(lang_label)}</span></div>{"".join(rows)}</details>'
        )
    return "".join(blocks)
