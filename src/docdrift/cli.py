"""DocDrift command line.

    docdrift init               configure the Gemini agent profile (reads .env)
    docdrift fetch              clone the OpenMinion docs that match the installed version
    docdrift scan               deterministic snippet + env checks, no model
    docdrift run                scan, then agent triage, claim checks, review, report
"""

from __future__ import annotations

import argparse
import builtins
import functools
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import openminion

from . import agents, report, scan
from .cli_check import openminion_executable
from .extract import OPENMINION as OPENMINION_PROFILE
from .extract import PROJECT as PROJECT_PROFILE
from .extract import Profile, detect_profile
from .project import pinned_openminion
from .sections import DEFAULT_SECTIONS, load_section
from .tools import CTX

# Flush every line so progress shows up even when output goes to a file.
# (sys.stdout.reconfigure(line_buffering=True) duplicated lines printed before
# the first OpenMinion runtime started, so it is not used.)
print = functools.partial(builtins.print, flush=True)  # noqa: A001

PROJECT = Path.cwd()
CACHE = PROJECT / ".cache"
OUT = PROJECT / "out"
CONFIG = PROJECT / ".openminion" / "agents.json"
REPO_URL = "https://github.com/OpenMinion/openminion.git"


def load_dotenv(path: Path = PROJECT / ".env") -> None:
    """Load KEY=VALUE lines into the environment without printing them."""

    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def isolate_runtime() -> None:
    """Keep OpenMinion state (sessions, runs, memory) inside this project."""

    os.environ.setdefault("OPENMINION_HOME", str(PROJECT))
    os.environ.setdefault("OPENMINION_DATA_ROOT", str(PROJECT / ".openminion"))


def installed_version() -> str:
    version = getattr(openminion, "__version__", "")
    if not version:
        from importlib.metadata import version as dist_version

        version = dist_version("openminion")
    return version


def default_docs_root() -> Path:
    return CACHE / f"openminion-v{installed_version()}"


def docs_ref(root: Path) -> str:
    root = root.resolve()
    if not (root / ".git").exists():
        return root.name  # do not report a parent directory's repository
    try:
        sha = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return f"{root.name} @ {sha}"
    except (OSError, subprocess.CalledProcessError):
        return str(root)


# --------------------------------------------------------------------------
def provider_preset(provider: str) -> dict:
    """Read the credential env var and recommended model from OpenMinion's own preset list."""

    proc = subprocess.run(
        [openminion_executable(), "setup", "--list-providers", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    items = data if isinstance(data, list) else data.get("providers", [])
    return next((p for p in items if p.get("id") == provider), {})


def cmd_init(args: argparse.Namespace) -> int:
    preset = provider_preset(args.provider)
    if not preset:
        print(f"unknown provider preset: {args.provider}. See `uv run openminion setup --list-providers`.")
        return 2
    key_env = preset.get("credential_env")
    if preset.get("requires_credential") and key_env and not os.environ.get(key_env):
        print(f"{key_env} is not set. Put it in .env (see .env.example) and retry.")
        return 2
    args.model = args.model or (preset.get("recommended_models") or [None])[0]
    if not args.model:
        print(f"no recommended model for {args.provider}; pass --model")
        return 2
    cmd = [
        openminion_executable(),
        "--home-root",
        str(PROJECT),
        "setup",
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--agent",
        args.agent,
        "--no-chat",
    ]
    if args.check:
        cmd.append("--check-provider")
    print("running:", " ".join(cmd[1:]))
    return subprocess.call(cmd)


def cmd_fetch(args: argparse.Namespace) -> int:
    ref = args.ref or f"v{installed_version()}"
    dest = CACHE / f"openminion-{ref}"
    if dest.exists():
        print(f"already present: {dest}")
        return 0
    CACHE.mkdir(exist_ok=True)
    print(f"cloning {REPO_URL} at {ref} -> {dest}")
    return subprocess.call(["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1", "--branch", ref, REPO_URL, str(dest)])


def _docs_root(args: argparse.Namespace) -> Path | None:
    root = Path(args.docs) if args.docs else default_docs_root()
    if not root.exists():
        print(f"docs not found at {root}. Run `docdrift fetch` or pass --docs PATH.")
        return None
    return root


def _profile(args: argparse.Namespace, root: Path) -> Profile:
    choice = getattr(args, "profile", "auto")
    if choice == "openminion":
        return OPENMINION_PROFILE
    if choice == "project":
        return PROJECT_PROFILE
    return detect_profile(root)


def cmd_scan(args: argparse.Namespace) -> int:
    root = _docs_root(args)
    if root is None:
        return 2
    profile = _profile(args, root)
    pins = pinned_openminion(root) if profile.name == "project" else {}
    print(f"openminion {installed_version()} vs {docs_ref(root)}  (profile: {profile.name})")
    if pins:
        print(f"project pins openminion: declared {pins['declared'] or '-'}, locked {pins['locked'] or '-'}")
    snippets, candidates = scan.scan(root, profile, env=not args.no_env)
    out_path = Path(args.out) if args.out else OUT / "evidence.json"
    scan.write_evidence(
        out_path, root, snippets, candidates, installed_version(), {"profile": profile.name, "pins": pins}
    )
    if not args.quiet:
        print(
            f"checked {len(snippets)} snippets "
            f"({sum(s.kind == 'python' for s in snippets)} python, {sum(s.kind == 'shell' for s in snippets)} shell)"
        )
        for c in candidates:
            hint = f"  (did you mean {', '.join(c.suggestions)}?)" if c.suggestions else ""
            print(f"  [{c.kind}] {c.path}:{c.line}  {c.detail}{hint}")
    print(f"{len(candidates)} candidate(s); evidence written to {out_path.as_posix()}")
    return 1 if (args.strict and candidates) else 0


def _approval(mode: str):
    def decide(tool_name: str, tool_args: dict, approval_id: str) -> bool:
        if tool_name != "write_issue_draft":
            print(f"  approval: denying unexpected tool {tool_name}")
            return False
        title = str(tool_args.get("title", ""))
        target = f"out/issues/{tool_args.get('finding_id', '?')}.md"
        print(f"\n  OpenMinion asks to run write_issue_draft -> {target}\n  title: {title}")
        if mode == "yes":
            print("  approved (--issues yes)")
            return True
        if mode == "no":
            print("  denied (--issues no)")
            return False
        try:
            return input("  Save this issue draft? [y/N] ").strip().lower() in {"y", "yes"}
        except EOFError:
            return False

    return decide


def cmd_run(args: argparse.Namespace) -> int:
    root = _docs_root(args)
    if root is None:
        return 2
    if not CONFIG.exists():
        print(f"no agent config at {CONFIG}. Run `docdrift init` first.")
        return 2
    CTX.docs_root = root
    CTX.out_dir = OUT
    version = installed_version()
    settings = agents.AgentSettings(
        config_path=str(CONFIG),
        agent_id=args.agent,
        timeout=args.timeout,
        pace_seconds=args.pace,
    )
    log = agents.RunLog(session_id=f"docdrift-{datetime.now():%Y%m%d-%H%M%S}")
    previous = report.load_previous(OUT)

    profile = _profile(args, root)
    print(f"[1/5] scan: openminion {version} vs {docs_ref(root)}  (profile: {profile.name})")
    snippets, candidates = scan.scan(root, profile)
    candidates = candidates[: args.max_candidates]
    print(f"      {len(snippets)} snippets, {len(candidates)} candidate(s)")

    triage_items: list[agents.TriageItem] = []
    if candidates and not args.no_triage:
        print("[2/5] triage: agent classifies each candidate with read-only tools")
        batches: dict[str, list[dict]] = {}
        for c in candidates:
            batches.setdefault(c.path, []).append(c.to_dict())
        triage_items = agents.triage(settings, log, batches, version)
        for i in triage_items:
            print(f"      {i.candidate_id}: {i.verdict}")
    else:
        print("[2/5] triage: skipped")

    claims: dict[str, list[agents.Claim]] = {}
    if profile.name == "project" and not args.section:
        args.no_claims = True  # the default sections are OpenMinion doc pages
    if not args.no_claims:
        specs = args.section or list(DEFAULT_SECTIONS)
        sections = [load_section(root, spec) for spec in specs]
        print(f"[3/5] claims: verifying up to {args.max_claims} claims in {len(sections)} section(s)")
        claims = agents.verify_claims(settings, log, sections, version, args.max_claims)
        for label, cs in claims.items():
            counts = {v: sum(c.verdict == v for c in cs) for v in ("supported", "contradicted", "unverifiable")}
            print(f"      {label}: {counts}")
    else:
        print("[3/5] claims: skipped")

    to_review: list[tuple[str, dict]] = []
    by_id = {c.id: c for c in candidates}
    for item in triage_items:
        if item.verdict == "real_drift":
            to_review.append((item.candidate_id, {"candidate": by_id[item.candidate_id].to_dict(), "triage": item.model_dump()}))
    for label, cs in claims.items():
        for claim in cs:
            if claim.verdict == "contradicted":
                to_review.append((report.finding_key_for_claim(label, claim), {"section": label, "claim": claim.model_dump()}))
    print(f"[4/5] review: subagent re-checks {len(to_review)} negative verdict(s)")
    reviews = agents.review(settings, log, to_review)
    for key, r in reviews.items():
        print(f"      {key}: {'confirmed' if r.agree else 'disputed'}")

    data = report.build(
        version=version,
        docs_root=root,
        docs_ref=docs_ref(root),
        snippets_checked=len(snippets),
        candidates=candidates,
        triage=triage_items,
        claims=claims,
        reviews=reviews,
        log=log,
        previous=previous,
    )
    md_path, json_path = report.write(OUT, data)

    confirmed = data["confirmed"]
    if confirmed and args.issues != "skip":
        print(f"[5/5] issues: drafting {len(confirmed)} issue(s); each write needs your approval")
        agents.draft_issues(settings, log, [(f["id"], f) for f in confirmed], _approval(args.issues))
        data["turns"] = [t.__dict__ for t in log.turns]
        report.write(OUT, data)
    else:
        print("[5/5] issues: nothing to draft" if not confirmed else "[5/5] issues: skipped")

    failed = [t for t in log.turns if not t.ok]
    print(f"\nreport: {md_path.as_posix()}  ({len(confirmed)} confirmed, {len(data['disputed'])} disputed, {len(failed)} failed turn(s))")
    return 0


def cmd_approval_check(args: argparse.Namespace) -> int:
    """Prove the approval gate: a denied write leaves no file, an approved one does."""

    if not CONFIG.exists():
        print(f"no agent config at {CONFIG}. Run `docdrift init` first.")
        return 2
    CTX.out_dir = OUT
    settings = agents.AgentSettings(config_path=str(CONFIG), agent_id=args.agent, timeout=args.timeout)
    log = agents.RunLog(session_id=f"docdrift-approval-{datetime.now():%Y%m%d-%H%M%S}")
    finding = {
        "type": "snippet",
        "path": "docs/example.md",
        "line": 1,
        "doc_says": "openminion example --flag",
        "problem": "SYNTHETIC finding used only to exercise the approval gate",
        "evidence": ["cli_help: `openminion example` does not exist"],
        "suggested_fix": "remove the example",
    }
    outcomes = []
    for mode in ("no", "yes"):
        key = f"APPROVAL-CHECK-{mode}"
        target = OUT / "issues" / f"{key}.md"
        target.unlink(missing_ok=True)
        asked: list[str] = []
        decide = _approval(mode)

        def recording(tool_name: str, tool_args: dict, approval_id: str, _d=decide, _a=asked) -> bool:
            _a.append(tool_name)
            return _d(tool_name, tool_args, approval_id)

        [result] = agents.draft_issues(settings, log, [(key, finding)], recording)
        exists = target.exists()
        expected = exists if mode == "yes" else not exists
        reply = (result.text if result is not None else "<no result>")[:200].replace("\n", " ")
        print(f"mode={mode}: callback asked={asked or 'never'} file_exists={exists} -> {'PASS' if expected and asked else 'FAIL'}")
        print(f"   agent reply: {reply}")
        outcomes.append(bool(expected and asked))
    return 0 if all(outcomes) else 1


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    isolate_runtime()
    parser = argparse.ArgumentParser(prog="docdrift", description="Check OpenMinion docs against the installed SDK.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="configure the agent profile from .env")
    p.add_argument("--provider", default="gemini", help="OpenMinion preset id: gemini, openai, openrouter, cortensor-portal, ...")
    p.add_argument("--model", default=None, help="default: the preset's recommended model")
    p.add_argument("--agent", default="docdrift", help="agent id to write, e.g. docdrift-portal to keep several providers side by side")
    p.add_argument("--check", action="store_true", help="send one small validation request")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("fetch", help="clone the docs for the installed openminion version")
    p.add_argument("--ref", help="git tag or branch (default: v<installed version>)")
    p.set_defaults(func=cmd_fetch)

    profile_help = "openminion = the OpenMinion repo's docs; project = any repo built on OpenMinion; auto detects"
    p = sub.add_parser("scan", help="deterministic checks only (no model)")
    p.add_argument("--docs", help="path to an OpenMinion checkout or to any project that uses OpenMinion")
    p.add_argument("--profile", choices=("auto", "openminion", "project"), default="auto", help=profile_help)
    p.add_argument("--out", help="evidence JSON path (default out/evidence.json)")
    p.add_argument("--no-env", action="store_true", help="skip the OPENMINION_* env var check")
    p.add_argument("--quiet", action="store_true", help="print only the summary line")
    p.add_argument("--strict", action="store_true", help="exit 1 when any candidate is found (for CI)")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("run", help="scan + agent triage, claim checks, review and report")
    p.add_argument("--docs", help="path to an OpenMinion checkout or to any project that uses OpenMinion")
    p.add_argument("--profile", choices=("auto", "openminion", "project"), default="auto", help=profile_help)
    p.add_argument("--agent", default="docdrift", help="agent id in .openminion/agents.json")
    p.add_argument("--section", action="append", help='doc section to verify, "path#Heading" (repeatable)')
    p.add_argument("--max-claims", type=int, default=5)
    p.add_argument("--max-candidates", type=int, default=20)
    p.add_argument("--no-triage", action="store_true")
    p.add_argument("--no-claims", action="store_true")
    p.add_argument("--issues", choices=("ask", "yes", "no", "skip"), default="ask")
    p.add_argument("--timeout", type=float, default=300.0, help="seconds per model turn")
    p.add_argument("--pace", type=float, default=0.0, help="seconds to wait between turns (free-tier rate limits)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("approval-check", help="prove the approval gate with a synthetic finding")
    p.add_argument("--agent", default="docdrift")
    p.add_argument("--timeout", type=float, default=120.0)
    p.set_defaults(func=cmd_approval_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
