"""Split Markdown into sections and protect everything a translator must not touch.

A *section* runs from one heading to the next heading of any level, so the
ledger can tell exactly which part of a page changed. Protected spans (fenced
code, inline code, link targets, URLs, HTML tags) are swapped for placeholders
before the model sees the text, then restored byte-for-byte afterwards.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
PLACEHOLDER = re.compile(r"⟦[A-Z]+\d+⟧")

# Order matters: code first, so a URL inside inline code stays part of the code.
# Inline code may wrap onto the next line (but never across a blank line).
_INLINE_CODE = re.compile(r"(`+)(?:(?!`)[^\n]|\n(?!\s*\n))+?\1")
_LINK_TARGET = re.compile(r"(?<=\])\((?:[^()\s]|\([^()]*\))+(?:\s+\"[^\"]*\")?\)")
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+\S.*$", re.MULTILINE)
_AUTOLINK = re.compile(r"<(?:https?://|mailto:)[^>\s]+>")
_BARE_URL = re.compile(r"(?<![(\w/])https?://[^\s)>\]]+")
# A full sentence in straight double quotes is, in technical docs, almost always
# literal program output ("Confirmation denied. The action was not run.") that a
# reader will see on screen in English. Curly-quoted prose is left translatable.
_QUOTED_OUTPUT = re.compile(r'"[A-Z][^"\n]{2,200}?[.!?…]"')
_HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>|<!--.*?-->", re.DOTALL)


@dataclass
class Section:
    key: str  # stable id: heading path + occurrence, e.g. "quick-start/install#1"
    heading: str  # the heading line itself ("" for the preamble)
    level: int
    text: str  # full section text including the heading line

    @property
    def digest(self) -> str:
        return hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:12]


def _slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)  # drop inline HTML such as anchors
    text = re.sub(r"[`*_\[\]()<>]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "section"


def split_sections(markdown: str) -> list[Section]:
    """Split on headings outside fenced code. Joining the texts gives the input back."""

    lines = markdown.splitlines(keepends=True)
    sections: list[Section] = []
    current: list[str] = []
    heading, level = "", 0
    stack: list[tuple[int, str]] = []
    seen: dict[str, int] = {}
    fence: str | None = None

    def flush() -> None:
        if not current and not heading:
            return
        path = "/".join(s for _, s in stack) or "_preamble"
        seen[path] = seen.get(path, 0) + 1
        sections.append(Section(f"{path}#{seen[path]}", heading, level, "".join(current)))

    for line in lines:
        match_fence = FENCE.match(line)
        if match_fence:
            marker = match_fence.group(1)
            if fence is None:
                fence = marker[0] * 3
            elif line.strip().startswith(fence):
                fence = None
            current.append(line)
            continue
        match = None if fence else HEADING.match(line.rstrip("\n"))
        if match:
            flush()
            level = len(match.group(1))
            heading = line.rstrip("\n")
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, _slug(match.group(2))))
            current = [line]
            continue
        current.append(line)
    flush()
    return sections


@dataclass
class Protected:
    """Text with placeholders, plus what each placeholder stands for."""

    text: str
    spans: dict[str, str] = field(default_factory=dict)

    def restore(self, translated: str) -> str:
        # Later spans can contain earlier placeholders (an HTML tag around a
        # URL), so expand in reverse creation order.
        out = translated
        for token, original in reversed(list(self.spans.items())):
            out = out.replace(token, original)
        return out


def protect(text: str) -> Protected:
    spans: dict[str, str] = {}
    counters: dict[str, int] = {}

    def token(kind: str, original: str) -> str:
        counters[kind] = counters.get(kind, 0) + 1
        name = f"⟦{kind}{counters[kind]}⟧"
        spans[name] = original
        return name

    # Fenced code blocks, whole, including the fence lines.
    out_lines: list[str] = []
    block: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        match_fence = FENCE.match(line)
        if fence is None and match_fence:
            fence = match_fence.group(1)[0] * 3
            block = [line]
            continue
        if fence is not None:
            block.append(line)
            if line.strip().startswith(fence) and len(block) > 1:
                ending = "\n" if block[-1].endswith("\n") else ""
                raw = "".join(block)
                if ending:
                    raw = raw[:-1]
                out_lines.append(token("CODE", raw) + ending)
                fence = None
            continue
        out_lines.append(line)
    if fence is not None:  # unterminated fence: keep it verbatim
        out_lines.append(token("CODE", "".join(block)))
    work = "".join(out_lines)

    for kind, pattern in (
        ("IC", _INLINE_CODE),
        ("REF", _REF_DEF),
        ("URL", _LINK_TARGET),
        ("URL", _AUTOLINK),
        ("URL", _BARE_URL),
        ("Q", _QUOTED_OUTPUT),
        ("TAG", _HTML_TAG),
    ):
        work = pattern.sub(lambda m, k=kind: token(k, m.group(0)), work)
    return Protected(work, spans)
