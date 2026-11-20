"""Deterministic checks a translation must pass before it is accepted.

The model proposes; these gates decide. Every failure is a concrete, quotable
reason that goes back to the translator on retry and into the report.
"""

from __future__ import annotations

import re
from collections import Counter

from .glossary import Glossary
from .segment import PLACEHOLDER, Protected

NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
HEADING = re.compile(r"^(#{1,6})\s")
LETTERS = re.compile(r"[A-Za-z]")


def _prose(text: str) -> str:
    return PLACEHOLDER.sub(" ", text)


def check(source: Protected, translated: str, glossary: Glossary | None = None) -> list[str]:
    """Return human-readable gate failures; an empty list means the translation passes."""

    errors: list[str] = []
    src_tokens = Counter(PLACEHOLDER.findall(source.text))
    out_tokens = Counter(PLACEHOLDER.findall(translated))
    missing = sorted((src_tokens - out_tokens).elements())
    extra = sorted((out_tokens - src_tokens).elements())
    if missing:
        errors.append(f"placeholders missing or altered: {', '.join(missing)} (copy them exactly)")
    if extra:
        errors.append(f"placeholders duplicated or invented: {', '.join(extra)}")

    src_head = HEADING.match(source.text)
    out_head = HEADING.match(translated)
    if src_head and (not out_head or out_head.group(1) != src_head.group(1)):
        errors.append(f"heading level changed: source starts with '{src_head.group(1)} '")

    src_numbers = Counter(NUMBER.findall(_prose(source.text)))
    out_numbers = Counter(NUMBER.findall(_prose(translated)))
    lost = sorted((src_numbers - out_numbers).elements())
    if lost:
        errors.append(f"numbers missing from translation: {', '.join(lost)}")

    src_rows = [l for l in source.text.splitlines() if l.lstrip().startswith("|")]
    out_rows = [l for l in translated.splitlines() if l.lstrip().startswith("|")]
    if len(src_rows) != len(out_rows):
        errors.append(f"table rows changed: {len(src_rows)} in source, {len(out_rows)} in translation")
    elif [r.count("|") for r in src_rows] != [r.count("|") for r in out_rows]:
        errors.append("table columns changed (pipe count differs on some row)")

    src_items = len(LIST_ITEM.findall(source.text))
    out_items = len(LIST_ITEM.findall(translated))
    if src_items != out_items:
        errors.append(f"list items changed: {src_items} in source, {out_items} in translation")

    if "```" in translated or "~~~" in translated:
        errors.append("translation added a code fence; code blocks are placeholders and must stay so")

    prose = _prose(source.text)
    if len(LETTERS.findall(prose)) > 60:
        if translated.strip() == source.text.strip():
            errors.append("section was returned untranslated")
        ratio = len(_prose(translated)) / max(1, len(prose))
        if not 0.6 <= ratio <= 2.2:
            errors.append(f"length ratio {ratio:.2f} is outside 0.6-2.2 (content added or dropped?)")

    if glossary:
        for term, entry in glossary.terms_in(source.text).items():
            target = entry["target"]
            if target.lower() not in translated.lower():
                errors.append(f"glossary: '{term}' must be rendered as '{target}'")
    return errors
