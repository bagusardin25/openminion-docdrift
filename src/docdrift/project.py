"""Facts about a project built on OpenMinion: which openminion version it pins."""

from __future__ import annotations

import re
from pathlib import Path

SPEC = re.compile(r"""openminion(?:\[[^\]]*\])?\s*((?:[=<>!~]=?|===)\s*[0-9][0-9A-Za-z.*]*(?:\s*,\s*(?:[=<>!~]=?)\s*[0-9][0-9A-Za-z.*]*)*)""")
LOCK = re.compile(r'name = "openminion"\s*\nversion = "([^"]+)"')


def pinned_openminion(root: Path) -> dict:
    """Return the declared openminion requirement and the locked version, if any."""

    declared = ""
    for name in ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.cfg", "setup.py"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match = SPEC.search(text)
        if match:
            declared = match.group(1).replace(" ", "")
            break
        if re.search(r"""["'\s]openminion["'\s\]]""", text) and not declared:
            declared = "(unpinned)"
    locked = ""
    lock = root / "uv.lock"
    if lock.is_file():
        match = LOCK.search(lock.read_text(encoding="utf-8", errors="replace"))
        if match:
            locked = match.group(1)
    return {"declared": declared, "locked": locked}
