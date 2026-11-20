"""Mark ledger sections for re-translation when the protection rules changed for them.

Usage: uv run python scripts/invalidate_protect_change.py SOURCE_DIR TRANSLATIONS_DIR

Compares how each source section is protected now with the old inline-code rule
(single-line only). Sections whose protected text differs were translated with a
wrong placeholder layout; their ledger status is set to "stale" so the next
`doctwin sync` re-translates exactly those.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from doctwin import segment
from doctwin.ledger import Ledger
from doctwin.sync import DEFAULT_FILES

OLD_INLINE = re.compile(r"(`+)(?:(?!\1).)+?\1")


def protected_with(pattern, text: str) -> str:
    saved = segment._INLINE_CODE
    segment._INLINE_CODE = pattern
    try:
        return segment.protect(text).text
    finally:
        segment._INLINE_CODE = saved


def main(source: Path, out: Path) -> int:
    ledger = Ledger.load(out / ".doctwin" / "ledger.json", "id")
    marked = []
    for file in DEFAULT_FILES:
        path = source / file
        if not path.exists():
            continue
        for s in segment.split_sections(path.read_text(encoding="utf-8")):
            if protected_with(OLD_INLINE, s.text) != segment.protect(s.text).text:
                state = ledger.section(file, s.key)
                if state:
                    state.status = "stale"
                    state.notes = ["protection rule for wrapped inline code changed"]
                    marked.append(f"{file} {s.key}")
    ledger.save()
    print(f"{len(marked)} section(s) marked stale:")
    for m in marked:
        print("  ", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
