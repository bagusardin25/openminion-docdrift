"""Turn scan, triage, claim and review results into report.md + report.json."""

from __future__ import annotations

import json
import platform
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .agents import Claim, Review, RunLog, TriageItem
from .scan import Candidate


def finding_key_for_claim(label: str, claim: Claim) -> str:
    path = label.split(":", 1)[0].replace("/", "_").replace(".md", "")
    return f"C-{path}-L{claim.line}"


def build(
    *,
    version: str,
    docs_root: Path,
    docs_ref: str,
    snippets_checked: int,
    candidates: list[Candidate],
    triage: list[TriageItem],
    claims: dict[str, list[Claim]],
    reviews: dict[str, Review],
    log: RunLog,
    previous: dict | None,
) -> dict:
    by_id = {c.id: c for c in candidates}
    confirmed, disputed = [], []

    for item in triage:
        if item.verdict != "real_drift":
            continue
        cand = by_id[item.candidate_id]
        entry = {
            "id": item.candidate_id,
            "type": "snippet",
            "path": cand.path,
            "line": cand.line,
            "doc_says": cand.snippet,
            "problem": cand.detail,
            "reason": item.reason,
            "evidence": item.evidence,
            "suggested_fix": item.suggested_fix,
        }
        review = reviews.get(item.candidate_id)
        entry["review"] = asdict_review(review)
        (confirmed if review and review.agree else disputed).append(entry)

    for label, items in claims.items():
        for claim in items:
            if claim.verdict != "contradicted":
                continue
            key = finding_key_for_claim(label, claim)
            entry = {
                "id": key,
                "type": "claim",
                "path": label.split(":", 1)[0],
                "line": claim.line,
                "doc_says": claim.quote,
                "problem": "claim contradicted by installed source",
                "reason": "",
                "evidence": claim.evidence,
                "suggested_fix": claim.suggested_fix,
            }
            review = reviews.get(key)
            entry["review"] = asdict_review(review)
            (confirmed if review and review.agree else disputed).append(entry)

    previous_ids = {f["id"] for f in (previous or {}).get("confirmed", [])}
    for entry in confirmed:
        entry["new_since_last_run"] = bool(previous) and entry["id"] not in previous_ids

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "openminion_version": version,
        "docs_root": str(docs_root),
        "docs_ref": docs_ref,
        "environment": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
        "session_id": log.session_id,
        "snippets_checked": snippets_checked,
        "candidates": [c.to_dict() for c in candidates],
        "triage": [i.model_dump() for i in triage],
        "claims": {k: [c.model_dump() for c in v] for k, v in claims.items()},
        "confirmed": confirmed,
        "disputed": disputed,
        "turns": [asdict(t) for t in log.turns],
    }


def asdict_review(review: Review | None) -> dict | None:
    return review.model_dump() if review else None


def _counts(counter: Counter) -> str:
    return ", ".join(f"{n} {k}" for k, n in sorted(counter.items())) or "not run"


def _cell(text: str, limit: int = 160) -> str:
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def to_markdown(data: dict) -> str:
    triage_counts = Counter(i["verdict"] for i in data["triage"])
    claim_counts = Counter(c["verdict"] for cs in data["claims"].values() for c in cs)
    turns = data["turns"]
    ok_turns = sum(1 for t in turns if t["ok"])
    lines = [
        "# DocDrift report",
        "",
        f"- **openminion installed:** `{data['openminion_version']}`",
        f"- **docs checked:** `{data['docs_ref']}`",
        f"- **generated:** {data['generated_at']} on {data['environment']}",
        f"- **OpenMinion session:** `{data['session_id']}`",
        "",
        "## Summary",
        "",
        "| Stage | Result |",
        "| --- | --- |",
        f"| Deterministic scan | {data['snippets_checked']} snippets checked, {len(data['candidates'])} candidates |",
        f"| Agent triage | {_counts(triage_counts)} |",
        f"| Claim verification | {_counts(claim_counts)} |",
        f"| Confirmed by reviewer subagent | {len(data['confirmed'])} |",
        f"| Disputed by reviewer subagent | {len(data['disputed'])} |",
        f"| Model turns | {ok_turns}/{len(turns)} succeeded |",
        "",
        "## Confirmed drift",
        "",
    ]
    if not data["confirmed"]:
        lines += ["No confirmed drift.", ""]
    for f in data["confirmed"]:
        new = " **(new since last run)**" if f.get("new_since_last_run") else ""
        lines += [
            f"### `{f['id']}` · {f['path']}:{f['line']}{new}",
            "",
            f"- **Doc says:** {_cell(f['doc_says'], 400)}",
            f"- **Problem:** {_cell(f['problem'], 400)}",
        ]
        if f["reason"]:
            lines.append(f"- **Why it matters:** {_cell(f['reason'], 400)}")
        lines += [f"- **Evidence:** {_cell(e, 300)}" for e in f["evidence"][:5]]
        if f["suggested_fix"]:
            lines.append(f"- **Suggested fix:** {_cell(f['suggested_fix'], 400)}")
        if f["review"]:
            lines.append(f"- **Reviewer:** {_cell(f['review']['reason'], 400)}")
        lines.append("")

    lines += ["## Disputed (reviewer did not confirm)", ""]
    if not data["disputed"]:
        lines.append("None.")
    for f in data["disputed"]:
        why = f["review"]["reason"] if f["review"] else "reviewer did not return a verdict"
        lines.append(f"- `{f['id']}` {f['path']}:{f['line']}: {_cell(f['doc_says'], 160)} → {_cell(why, 240)}")
    lines.append("")

    lines += ["## Triage of scan candidates", "", "| Candidate | Where | Verdict | Reason |", "| --- | --- | --- | --- |"]
    by_id = {c["id"]: c for c in data["candidates"]}
    for item in data["triage"]:
        c = by_id.get(item["candidate_id"], {})
        lines.append(
            f"| `{item['candidate_id']}` {_cell(c.get('kind', ''), 40)} | {c.get('path', '')}:{c.get('line', '')} | {item['verdict']} | {_cell(item['reason'])} |"
        )
    untriaged = [c for c in data["candidates"] if c["id"] not in {i["candidate_id"] for i in data["triage"]}]
    for c in untriaged:
        lines.append(f"| `{c['id']}` {c['kind']} | {c['path']}:{c['line']} | not triaged | {_cell(c['detail'])} |")
    lines.append("")

    lines += ["## Verified claims", "", "| Section | Line | Verdict | Claim |", "| --- | --- | --- | --- |"]
    for label, claims in data["claims"].items():
        for c in claims:
            lines.append(f"| {_cell(label, 60)} | {c['line']} | {c['verdict']} | {_cell(c['quote'])} |")
    lines.append("")

    lines += [
        "## Run diagnostics",
        "",
        "| Role | Item | OK | Seconds | Tool calls | Error |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for t in turns:
        lines.append(
            f"| {t['role']} | {_cell(t['label'], 60)} | {'yes' if t['ok'] else 'no'} | {t['seconds']:.1f} | {t['tool_calls']} | {_cell(t['error'], 200)} |"
        )
    lines.append("")
    return "\n".join(lines)


def write(out_dir: Path, data: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    md_path.write_text(to_markdown(data), encoding="utf-8")
    return md_path, json_path


def load_previous(out_dir: Path) -> dict | None:
    path = out_dir / "report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
