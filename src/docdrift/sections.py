"""Select doc sections by heading, with absolute line numbers for citations."""

from __future__ import annotations

import re
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

DEFAULT_SECTIONS = (
    "docs/turn-budgets.md#What the defaults control",
    "docs/provider-capabilities.md#HTTP connection reuse",
    "docs/getting-started.md#Persistent action-policy defaults",
    "docs/runtime-surfaces.md#2. Python library API",
)


def load_section(root: Path, spec: str, max_lines: int = 120) -> tuple[str, str]:
    """Return (label, numbered text) for "path#Heading text"."""

    path_part, _, heading = spec.partition("#")
    lines = (root / path_part).read_text(encoding="utf-8").splitlines()
    in_fence = False
    start, level = None, 0
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if start is None:
            if match and (not heading or match.group(2).strip().lower() == heading.strip().lower()):
                start, level = i, len(match.group(1))
            continue
        if match and len(match.group(1)) <= level:
            end = i
            break
    else:
        end = len(lines)
    if start is None:
        raise ValueError(f"heading not found: {spec}")
    end = min(end, start + max_lines)
    numbered = "\n".join(f"{n + 1}: {lines[n]}" for n in range(start, end))
    return f"{path_part}:{start + 1}-{end} ({heading or 'top'})", numbered
