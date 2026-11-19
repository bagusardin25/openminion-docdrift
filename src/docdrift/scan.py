"""Deterministic evidence pass: every candidate here is reproducible without a model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import cli_check, env_check, py_check
from .extract import Snippet, collect, doc_files


@dataclass
class Candidate:
    """A possible doc/SDK mismatch, with the evidence the agent will triage."""

    id: str
    source: str  # "cli" | "python" | "env"
    kind: str
    path: str
    line: int
    snippet: str
    detail: str
    suggestions: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _cid(*parts: object) -> str:
    return "D" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:7]


def scan(root: Path) -> tuple[list[Snippet], list[Candidate]]:
    snippets = collect(root)
    candidates: list[Candidate] = []
    for c in cli_check.check_snippets([s for s in snippets if s.kind == "shell"]):
        candidates.append(
            Candidate(
                id=_cid(c.path, c.command, c.kind, c.detail),
                source="cli",
                kind=c.kind,
                path=c.path,
                line=c.line,
                snippet=c.command,
                detail=c.detail,
                suggestions=c.suggestions,
            )
        )
    for snip in snippets:
        if snip.kind != "python":
            continue
        for p in py_check.check_snippet(snip):
            candidates.append(
                Candidate(
                    id=_cid(p.path, p.code_line, p.kind, p.detail),
                    source="python",
                    kind=p.kind,
                    path=p.path,
                    line=p.line,
                    snippet=p.code_line,
                    detail=p.detail,
                    suggestions=p.suggestions,
                )
            )
    for path, usages in env_check.unknown_env_vars(root, doc_files(root)).items():
        names = [u.name for u in usages]
        candidates.append(
            Candidate(
                id=_cid(path, "unknown_env_var", ",".join(names)),
                source="env",
                kind="unknown_env_var",
                path=path,
                line=1,
                snippet=", ".join(names),
                detail=(
                    f"{len(names)} OPENMINION_* variable(s) in this doc are never referenced by the "
                    f"installed package. Source checkout usage: {env_check.summarize(usages)}"
                ),
                suggestions=[],
            )
        )
    # Same mistake repeated in one file is one finding.
    unique: dict[str, Candidate] = {}
    for c in candidates:
        unique.setdefault(c.id, c)
    return snippets, list(unique.values())


def write_evidence(path: Path, root: Path, snippets: list[Snippet], candidates: list[Candidate], version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "openminion_version": version,
        "docs_root": str(root),
        "snippets_checked": len(snippets),
        "python_snippets": sum(1 for s in snippets if s.kind == "python"),
        "shell_snippets": sum(1 for s in snippets if s.kind == "shell"),
        "candidates": [c.to_dict() for c in candidates],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
