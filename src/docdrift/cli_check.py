"""Check `openminion ...` commands in docs against the installed CLI's --help output.

The checker only ever runs `openminion <subcommand...> --help`, so it is
read-only. Help output is parsed rather than importing CLI internals, which keeps
the check on the public surface a reader of the docs would actually use.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

from .extract import Snippet

OPTION_LINE = re.compile(r"^\s{2,}(-[^\s].*?)(?:\s{2,}|$)")
FLAG = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]*)")
SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||\||;)\s*")
COMMAND_START = re.compile(r"(?<![\w./-])openminion(?![\w.-])")


@dataclass
class HelpInfo:
    """What one `openminion ... --help` page accepts."""

    ok: bool
    options: dict[str, bool] = field(default_factory=dict)  # flag -> takes a value
    subcommands: list[str] = field(default_factory=list)
    positionals: list[str] = field(default_factory=list)
    raw: str = ""


def openminion_executable() -> str:
    """Prefer the CLI that sits next to the running interpreter (the same venv)."""

    bindir = Path(sys.executable).parent
    for name in ("openminion.exe", "openminion"):
        candidate = bindir / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which("openminion")
    if not found:
        raise RuntimeError("openminion CLI not found; install the openminion package")
    return found


_SANDBOX_HOME = tempfile.mkdtemp(prefix="docdrift-help-")
_HELP_POOL = ThreadPoolExecutor(max_workers=8)
_HELP_FUTURES: dict[tuple[str, ...], Future] = {}
_HELP_LOCK = threading.Lock()


def help_for(path: tuple[str, ...]) -> HelpInfo:
    """Cached, thread-safe `openminion <path> --help`. Each path runs once."""

    with _HELP_LOCK:
        future = _HELP_FUTURES.get(path)
        if future is None:
            future = _HELP_POOL.submit(_run_help, path)
            _HELP_FUTURES[path] = future
    return future.result()


def _run_help(path: tuple[str, ...]) -> HelpInfo:
    """Run `openminion <path> --help` in an isolated home and parse the result."""

    env = dict(os.environ)
    # Keep help calls from touching the user's real OpenMinion state.
    env["OPENMINION_HOME"] = _SANDBOX_HOME
    env["OPENMINION_DATA_ROOT"] = str(Path(_SANDBOX_HOME) / ".openminion")
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [openminion_executable(), *path, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return HelpInfo(ok=False, raw="timeout")
    text = proc.stdout or proc.stderr
    if proc.returncode != 0 or "usage:" not in text:
        return HelpInfo(ok=False, raw=text[-2000:])
    return parse_help(text)


def parse_help(text: str) -> HelpInfo:
    info = HelpInfo(ok=True, raw=text)
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if line and not line[0].isspace() and stripped.endswith(":"):
            section = stripped.lower()
            continue
        if section.startswith("positional"):
            if line.startswith("  ") and not line.startswith("    "):
                head = stripped.split()[0] if stripped else ""
                if head.startswith("{"):
                    info.subcommands.extend(head.strip("{}").split(","))
                elif head:
                    info.positionals.append(head)
            continue
        match = OPTION_LINE.match(line)
        if match:
            invocation = match.group(1)
            parts = [p.strip() for p in invocation.split(",")]
            for part in parts:
                tokens = part.split()
                if not tokens or not tokens[0].startswith("-"):
                    continue
                info.options[tokens[0]] = len(tokens) > 1
    # argparse lists sub-commands under "positional arguments" but some
    # parsers put them under a titled section; fall back to the usage line.
    if not info.subcommands:
        usage = text.split("\n\n", 1)[0]
        tail = usage.split("]")[-1]
        choice = re.search(r"\{([\w,-]+)\}", tail)
        if choice:
            info.subcommands = choice.group(1).split(",")
    return info


@dataclass
class CliCandidate:
    snippet_id: str
    path: str
    line: int
    command: str
    kind: str  # unknown_subcommand | unknown_flag | help_failed
    detail: str
    suggestions: list[str]


def _is_placeholder(token: str) -> bool:
    return any(ch in token for ch in "<>$*{}") or token in {"...", "…"} or token.isupper()


def commands_in(snippet: Snippet) -> list[tuple[int, str]]:
    """Return (line offset, command text) for each `openminion` invocation."""

    logical: list[tuple[int, str]] = []
    buffer, start = "", 0
    for offset, raw in enumerate(snippet.code.splitlines()):
        line = raw.rstrip()
        if not buffer:
            start = offset
        if line.endswith("\\") or line.endswith("`"):
            buffer += line[:-1] + " "
            continue
        buffer += line
        logical.append((start, buffer))
        buffer = ""
    if buffer:
        logical.append((start, buffer))

    out: list[tuple[int, str]] = []
    for offset, line in logical:
        text = line.strip()
        if text.startswith("#"):
            continue
        text = re.sub(r"^(\$|PS>|>)\s+", "", text)
        for match in COMMAND_START.finditer(text):
            segment = text[match.start():]
            segment = SEGMENT_SPLIT.split(segment, maxsplit=1)[0]
            # Close a "$(openminion ...)" substitution at its paren.
            depth = 0
            for idx, ch in enumerate(segment):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        segment = segment[:idx]
                        break
                    depth -= 1
            out.append((offset, " ".join(segment.split()).rstrip('"')))
    return out


def check_command(snippet: Snippet, offset: int, command: str) -> list[CliCandidate]:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []
    if not tokens or tokens[0] != "openminion":
        return []

    line = snippet.line + offset
    found: list[CliCandidate] = []
    path: list[str] = []
    info = help_for(())
    if not info.ok:
        # Never pass silently: a CLI that cannot print help is itself a finding.
        return [
            CliCandidate(
                snippet_id=snippet.id,
                path=snippet.path,
                line=line,
                command=command,
                kind="help_failed",
                detail=f"`openminion --help` failed: {info.raw[-300:]}",
                suggestions=[],
            )
        ]
    walking = True
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("-") and len(token) > 1 and token != "--":
            name = token.split("=", 1)[0]
            if info.ok and name not in info.options:
                where = "openminion " + " ".join(path) if path else "openminion"
                found.append(
                    CliCandidate(
                        snippet_id=snippet.id,
                        path=snippet.path,
                        line=line,
                        command=command,
                        kind="unknown_flag",
                        detail=f"`{where}` does not accept `{name}`",
                        suggestions=get_close_matches(name, list(info.options), n=3),
                    )
                )
            elif info.options.get(name) and "=" not in token:
                i += 1  # skip the flag's value
        elif walking and info.subcommands:
            if token in info.subcommands:
                path.append(token)
                info = help_for(tuple(path))
                if not info.ok:
                    found.append(
                        CliCandidate(
                            snippet_id=snippet.id,
                            path=snippet.path,
                            line=line,
                            command=command,
                            kind="help_failed",
                            detail=f"`openminion {' '.join(path)} --help` failed: {info.raw[-300:]}",
                            suggestions=[],
                        )
                    )
                    return found
            elif _is_placeholder(token) or info.positionals:
                walking = False
            else:
                where = "openminion " + " ".join(path) if path else "openminion"
                found.append(
                    CliCandidate(
                        snippet_id=snippet.id,
                        path=snippet.path,
                        line=line,
                        command=command,
                        kind="unknown_subcommand",
                        detail=f"`{where}` has no subcommand `{token}`",
                        suggestions=get_close_matches(token, info.subcommands, n=3),
                    )
                )
                return found
        else:
            walking = False
        i += 1
    return found


def check_snippet(snippet: Snippet) -> list[CliCandidate]:
    out: list[CliCandidate] = []
    for offset, command in commands_in(snippet):
        out.extend(check_command(snippet, offset, command))
    return out


def check_snippets(snippets: list[Snippet]) -> list[CliCandidate]:
    """Check many shell snippets concurrently; help pages are shared via the cache."""

    jobs = [(s, offset, command) for s in snippets for offset, command in commands_in(s)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda job: check_command(*job), jobs)
        return [c for batch in results for c in batch]
