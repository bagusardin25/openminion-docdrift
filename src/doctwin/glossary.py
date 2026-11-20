"""Terminology the translator must follow, stored as a reviewable JSON file.

New terms are only ever added through an approval-gated OpenMinion tool, so a
human decides terminology; the model can only propose.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .segment import PLACEHOLDER

# Starter glossary for Indonesian. Names stay as they are; common developer
# terms that Indonesian technical writing usually keeps in English stay too.
SEED: dict[str, dict[str, dict[str, str]]] = {
    "id": {
        "OpenMinion": {"target": "OpenMinion", "note": "product name"},
        "Cortensor": {"target": "Cortensor", "note": "product name"},
        "Python": {"target": "Python", "note": "name"},
        "SDK": {"target": "SDK", "note": "keep"},
        "CLI": {"target": "CLI", "note": "keep"},
        "API": {"target": "API", "note": "keep"},
        "MCP": {"target": "MCP", "note": "keep"},
        "agent": {"target": "agent", "note": "keep English, common in Indonesian AI writing"},
        "runtime": {"target": "runtime", "note": "keep English"},
        "provider": {"target": "provider", "note": "keep English"},
        "prompt": {"target": "prompt", "note": "keep English"},
        "workspace": {"target": "workspace", "note": "keep English"},
        "endpoint": {"target": "endpoint", "note": "keep English"},
        "library": {"target": "library", "note": "software library; never 'perpustakaan' (a building)"},
        "token": {"target": "token", "note": "keep English"},
        "session": {"target": "sesi", "note": "standard Indonesian"},
        "approval": {"target": "persetujuan", "note": "standard Indonesian"},
        "repository": {"target": "repositori", "note": "standard Indonesian"},
    }
}


@dataclass
class Glossary:
    path: Path
    lang: str
    terms: dict[str, dict[str, str]] = field(default_factory=dict)
    version: int = 1

    @classmethod
    def load(cls, path: Path, lang: str) -> "Glossary":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(path, data.get("lang", lang), data.get("terms", {}), data.get("version", 1))
        glossary = cls(path, lang, dict(SEED.get(lang, {})))
        glossary.save()
        return glossary

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"lang": self.lang, "version": self.version, "terms": dict(sorted(self.terms.items(), key=lambda kv: kv[0].lower()))}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def add(self, source: str, target: str, note: str) -> None:
        self.terms[source] = {
            "target": target,
            "note": note,
            "added": datetime.now(timezone.utc).date().isoformat(),
        }
        self.version += 1
        self.save()

    def terms_in(self, text: str) -> dict[str, dict[str, str]]:
        """Glossary entries whose source term appears in the prose (not in placeholders)."""

        prose = PLACEHOLDER.sub(" ", text)
        found = {}
        for term, entry in self.terms.items():
            flags = 0 if term[:1].isupper() else re.IGNORECASE
            if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", prose, flags):
                found[term] = entry
        return found
