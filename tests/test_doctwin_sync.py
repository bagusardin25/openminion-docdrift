"""Offline integration test of the sync loop with a fake translator and reviewer."""

import re
from pathlib import Path

from docdrift.agents import AgentSettings, RunLog
from doctwin import agents, sync as sync_mod
from doctwin.ledger import Ledger


def fake_translate(settings, log, lang, label, items, glossary_entries, feedback=None):
    # "Translate" by upper-casing the word "the": prose changes, structure stays.
    return agents.TranslationBatch(
        sections=[agents.SectionText(key=i["key"], text=re.sub(r"\bthe\b", "THE", i["text"])) for i in items]
    )


def fake_review(settings, log, lang, label, pairs):
    return agents.ReviewBatch(sections=[agents.SectionReview(key=p["key"], faithful=True) for p in pairs])


def make_source(root: Path, extra: str = "") -> None:
    big = "\n\n".join(f"Paragraph {n} explains the setting and the reason behind it in some detail." * 8 for n in range(14))
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\nRead the intro first.\n\n## Install\n\nRun the setup:\n\n```bash\nopenminion setup\n```\n\n"
        f"## Big section\n\n{big}\n\n```python\nprint('the end')\n```\n\n## Last\n\nThe last words.{extra}\n",
        encoding="utf-8",
    )


def run(src: Path, out: Path, monkeypatch, max_chars: int = 1500):
    monkeypatch.setattr(agents, "translate", fake_translate)
    monkeypatch.setattr(agents, "review", fake_review)
    return sync_mod.sync(
        source=src, source_ref="test", out=out, lang="xx", files=["docs/guide.md"],
        settings=AgentSettings(config_path="unused", agent_id=None), log=RunLog("s"),
        approve_term=None, max_chars=max_chars, progress=lambda _m: None,
    )


def test_large_section_across_chunks_assembles_completely(tmp_path: Path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    make_source(src)
    result = run(src, out, monkeypatch)
    source_text = (src / "docs/guide.md").read_text(encoding="utf-8")
    output = (out / "docs/guide.md").read_text(encoding="utf-8")

    assert result.files[0].code_blocks_identical is True
    assert [l for l in output.splitlines() if l.startswith("#")] == [l for l in source_text.splitlines() if l.startswith("#")]
    assert output.count("Paragraph 13") == source_text.count("Paragraph 13")  # last part survived
    assert output.count("Paragraph 0") == source_text.count("Paragraph 0")  # first part survived
    actions = [s.action for s in result.sections if s.action != "copied"]
    assert actions and set(actions) == {"translated"}
    big = next(s for s in result.sections if s.key.startswith("guide/big-section"))
    assert big.parts > 1


def test_second_sync_only_touches_the_changed_section(tmp_path: Path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    make_source(src)
    run(src, out, monkeypatch)
    make_source(src, extra=" A new sentence.")
    result = run(src, out, monkeypatch)
    changed = [s.key for s in result.sections if s.action == "translated"]
    assert changed == ["guide/last#1"]
    assert Ledger.load(out / ".doctwin" / "ledger.json", "xx").section("docs/guide.md", "guide/last#1").status == "ok"


def test_human_edit_is_respected(tmp_path: Path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    make_source(src)
    run(src, out, monkeypatch)
    edited = out / "docs/guide.md"
    edited.write_text(edited.read_text(encoding="utf-8") + "\nA human fixed this.\n", encoding="utf-8")
    make_source(src, extra=" Changed.")
    result = run(src, out, monkeypatch)
    assert result.files[0].status == "human_edited"
    assert edited.read_text(encoding="utf-8").endswith("A human fixed this.\n")
