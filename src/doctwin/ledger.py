"""What has been translated, from which source text, and with what result.

The ledger is what makes sync incremental: a section is re-translated only
when its source digest changes. It also records the digest of every file
DocTwin wrote, so a human edit to a translated file is detected and respected.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class SectionState:
    source_digest: str
    text: str  # accepted translation (placeholders restored)
    status: str  # ok | needs_review | source_fallback
    notes: list[str] = field(default_factory=list)
    updated: str = ""


@dataclass
class Ledger:
    path: Path
    lang: str
    source_ref: str = ""
    files: dict[str, dict] = field(default_factory=dict)  # path -> {"written_digest": str, "sections": {key: SectionState}}

    @classmethod
    def load(cls, path: Path, lang: str) -> "Ledger":
        if not path.exists():
            return cls(path, lang)
        data = json.loads(path.read_text(encoding="utf-8"))
        files = {}
        for name, entry in data.get("files", {}).items():
            files[name] = {
                "written_digest": entry.get("written_digest", ""),
                "sections": {k: SectionState(**v) for k, v in entry.get("sections", {}).items()},
            }
        return cls(path, data.get("lang", lang), data.get("source_ref", ""), files)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "lang": self.lang,
            "source_ref": self.source_ref,
            "saved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": {
                name: {
                    "written_digest": entry["written_digest"],
                    "sections": {k: vars(s) for k, s in entry["sections"].items()},
                }
                for name, entry in sorted(self.files.items())
            },
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def section(self, file: str, key: str) -> SectionState | None:
        return self.files.get(file, {}).get("sections", {}).get(key)

    def put(self, file: str, key: str, state: SectionState) -> None:
        state.updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.files.setdefault(file, {"written_digest": "", "sections": {}})["sections"][key] = state

    def prune(self, file: str, keep: set[str]) -> list[str]:
        sections = self.files.get(file, {}).get("sections", {})
        removed = [k for k in sections if k not in keep]
        for k in removed:
            del sections[k]
        return removed
