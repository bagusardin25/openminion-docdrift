"""Create .cache/demo-source: the v0.1.23 docs with one sentence changed.

A sync against it re-translates exactly one section, which makes a cheap live
demo (about two model turns) of DocTwin's incremental behaviour.

Usage: uv run python scripts/make_demo_source.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

SRC = Path(".cache/openminion-v0.1.23")
DEST = Path(".cache/demo-source")
FILE = "docs/provider-capabilities.md"
OLD = "The provider client is closed when its agent runtime is evicted or the API\nruntime shuts down."
NEW = (
    "The provider client is closed when its agent runtime is evicted or the API\n"
    "runtime shuts down. Reuse never shares a connection between two providers."
)


def main() -> int:
    if not SRC.exists():
        print("run `uv run doctwin fetch --ref v0.1.23` first")
        return 2
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for rel in ("README.md", "docs", "examples"):
        src = SRC / rel
        if src.is_dir():
            shutil.copytree(src, DEST / rel)
        else:
            shutil.copy2(src, DEST / rel)
    target = DEST / FILE
    text = target.read_text(encoding="utf-8")
    if OLD not in text:
        print(f"expected sentence not found in {FILE}")
        return 1
    target.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"{DEST}: copy of v0.1.23 docs with one sentence added to {FILE}")

    # Work on a copy of the translations so the demo never changes translations/id.
    twin_src, twin_dest = Path("translations/id"), Path(".cache/demo-twin")
    if twin_dest.exists():
        shutil.rmtree(twin_dest)
    shutil.copytree(twin_src, twin_dest, ignore=shutil.ignore_patterns("reports"))
    print(f"{twin_dest}: copy of translations/id for the demo (use --out {twin_dest.as_posix()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
