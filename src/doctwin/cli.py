"""DocTwin command line.

    doctwin fetch --ref v0.1.18          clone OpenMinion docs at a tag into .cache/
    doctwin plan  --source PATH          what a sync would translate (no model)
    doctwin sync  --source PATH          translate changed sections, gate, review, write
"""

from __future__ import annotations

import argparse
import builtins
import functools
import subprocess
import time
from datetime import datetime
from pathlib import Path

from docdrift import scan
from docdrift.agents import AgentSettings, RunLog
from docdrift.cli import CACHE, CONFIG, PROJECT, REPO_URL, docs_ref, isolate_runtime, load_dotenv
from docdrift.extract import Profile

from . import render
from .ledger import Ledger
from .segment import split_sections
from .sync import DEFAULT_FILES, sync

print = functools.partial(builtins.print, flush=True)  # noqa: A001


def _out(args) -> Path:
    return Path(args.out) if args.out else PROJECT / "translations" / args.lang


def _files(args) -> list[str]:
    return args.file or list(DEFAULT_FILES)


def cmd_fetch(args) -> int:
    dest = CACHE / f"openminion-{args.ref}"
    if dest.exists():
        print(f"already present: {dest}")
        return 0
    CACHE.mkdir(exist_ok=True)
    print(f"cloning {REPO_URL} at {args.ref} -> {dest}")
    return subprocess.call(["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1", "--branch", args.ref, REPO_URL, str(dest)])


def cmd_plan(args) -> int:
    source, out = Path(args.source), _out(args)
    ledger = Ledger.load(out / ".doctwin" / "ledger.json", args.lang)
    total = todo = 0
    print(f"{docs_ref(source)} -> {out} ({args.lang}); last synced from: {ledger.source_ref or 'never'}")
    for file in _files(args):
        path = source / file
        if not path.exists():
            print(f"  {file}: missing in source")
            continue
        sections = split_sections(path.read_text(encoding="utf-8"))
        changed = [s for s in sections if not ((st := ledger.section(file, s.key)) and st.source_digest == s.digest and st.status == "ok")]
        total += len(sections)
        todo += len(changed)
        print(f"  {file}: {len(changed)}/{len(sections)} sections to translate")
    print(f"{todo} of {total} sections would go to the model")
    return 0


def _term_approval(mode: str):
    def decide(tool_name: str, tool_args: dict, approval_id: str) -> bool:
        if tool_name != "add_glossary_term":
            print(f"    approval: denying unexpected tool {tool_name}")
            return False
        src, tgt = tool_args.get("source", "?"), tool_args.get("target", "?")
        print(f"\n    OpenMinion asks to run add_glossary_term: '{src}' -> '{tgt}'\n    reason: {tool_args.get('reason', '')}")
        if mode in ("yes", "no"):
            print(f"    {'approved' if mode == 'yes' else 'denied'} (--terms {mode})")
            return mode == "yes"
        try:
            return input("    Add this term to the glossary? [y/N] ").strip().lower() in {"y", "yes"}
        except EOFError:
            return False

    return decide


def cmd_sync(args) -> int:
    if not CONFIG.exists():
        print(f"no agent config at {CONFIG}. Run `docdrift init` first.")
        return 2
    source, out = Path(args.source), _out(args)
    if not source.exists():
        print(f"source not found: {source}")
        return 2
    files = _files(args)
    ref = docs_ref(source)
    settings = AgentSettings(config_path=str(CONFIG), agent_id=args.agent, timeout=args.timeout, pace_seconds=args.pace)
    log = RunLog(session_id=f"doctwin-{args.lang}-{datetime.now():%Y%m%d-%H%M%S}")
    print(f"DocTwin sync: {ref} -> {out} ({args.lang})")
    started = time.monotonic()
    result = sync(
        source=source,
        source_ref=ref,
        out=out,
        lang=args.lang,
        files=files,
        settings=settings,
        log=log,
        approve_term=None if args.terms == "skip" else _term_approval(args.terms),
        max_chars=args.max_chars,
        dry_run=args.dry_run,
        force=args.force,
        max_chunks=args.max_chunks,
        progress=print,
    )
    validation = None
    if not args.no_validate and not args.dry_run:
        print("  validating commands and code in the translated files with DocDrift ...")
        profile = Profile("translation", tuple(files), ())
        _, candidates = scan.scan(out, profile, env=False)
        validation = {
            "candidates": [c.to_dict() for c in candidates],
            "summary": "no broken commands or imports" if not candidates else f"{len(candidates)} candidate(s); see report.json",
        }
    data = render.build(result, log, source_root=source, validation=validation, seconds=time.monotonic() - started)
    report_dir = out / ".doctwin" / "reports" / datetime.now().strftime("%Y%m%d-%H%M%S")
    md, _ = render.write_report(report_dir, data)
    render.write_report(out / ".doctwin", data)  # latest
    page = render.preview(out / ".doctwin" / "preview.html", source, out, files, data)
    c = data["counts"]
    print(
        f"\ndone: {c.get('translated', 0)} translated, {c.get('unchanged', 0) + c.get('copied', 0)} reused, "
        f"{c.get('needs_review', 0)} need review, {c.get('unreviewed', 0)} not reviewed, {c.get('source_fallback', 0)} kept in English"
    )
    print(f"report:  {md.as_posix()}\npreview: {page.as_posix()}")
    return 0


def cmd_preview(args) -> int:
    """Rebuild preview.html from the last sync report (no model)."""

    import json

    out = _out(args)
    report = out / ".doctwin" / "report.json"
    if not report.exists():
        print(f"no sync report at {report}; run `doctwin sync` first")
        return 2
    data = json.loads(report.read_text(encoding="utf-8"))
    page = render.preview(out / ".doctwin" / "preview.html", Path(args.source), out, _files(args), data)
    print(f"preview: {page.as_posix()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    isolate_runtime()
    parser = argparse.ArgumentParser(prog="doctwin", description="Keep translated docs a faithful twin of the source.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="clone OpenMinion at a tag into .cache/")
    p.add_argument("--ref", required=True, help="git tag, e.g. v0.1.18")
    p.set_defaults(func=cmd_fetch)

    for name, func, helptext in (
        ("plan", cmd_plan, "show what a sync would translate (no model)"),
        ("sync", cmd_sync, "translate, gate, review and write"),
        ("preview", cmd_preview, "rebuild the side-by-side preview from the last sync (no model)"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--source", required=True, help="docs source folder (e.g. .cache/openminion-v0.1.23)")
        p.add_argument("--lang", default="id", help="target language code (default: id)")
        p.add_argument("--out", help="translation folder (default: translations/<lang>)")
        p.add_argument("--file", action="append", help="doc path relative to the source (repeatable)")
        p.set_defaults(func=func)
        if name == "sync":
            p.add_argument("--agent", default="docdrift", help="agent id in .openminion/agents.json")
            p.add_argument("--terms", choices=("ask", "yes", "no", "skip"), default="ask", help="how glossary additions are approved")
            p.add_argument("--max-chars", type=int, default=5200, help="source + previous-translation characters per translation turn")
            p.add_argument("--max-chunks", type=int, help="stop after this many translation turns (testing)")
            p.add_argument("--timeout", type=float, default=300.0)
            p.add_argument("--pace", type=float, default=0.0)
            p.add_argument("--dry-run", action="store_true", help="translate but do not write files")
            p.add_argument("--force", action="store_true", help="overwrite translated files edited by a human")
            p.add_argument("--no-validate", action="store_true", help="skip the DocDrift check of the output")

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
