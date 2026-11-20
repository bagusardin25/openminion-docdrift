"""DocTwin deterministic tests: no model is called."""

from pathlib import Path

from doctwin import gates
from doctwin.glossary import Glossary
from doctwin.ledger import Ledger, SectionState
from doctwin.segment import protect, split_sections

DOC = """Intro line with a [link](https://example.com/a) and `code`.

## Install

Run this:

```bash
openminion setup --provider openai
# ## not a heading
```

- one
- two

| Key | Value |
| --- | --- |
| retries | 3 |

### Notes <a id="notes"></a>

Never set `timeout` below 30 seconds.
"""


def test_split_round_trips_and_ignores_headings_in_code():
    sections = split_sections(DOC)
    assert "".join(s.text for s in sections) == DOC
    assert [s.key for s in sections] == ["_preamble#1", "install#1", "install/notes#1"]


def test_protect_round_trips_and_hides_code_links_html():
    for s in split_sections(DOC):
        p = protect(s.text)
        assert p.restore(p.text) == s.text
        assert "openminion setup" not in p.text and "https://" not in p.text and "<a " not in p.text


def _install_section():
    return protect(split_sections(DOC)[1].text)


def test_gates_pass_a_faithful_translation():
    p = _install_section()
    translated = p.text.replace("## Install", "## Instalasi").replace("Run this:", "Jalankan ini:")
    translated = translated.replace("one", "satu").replace("two", "dua").replace("Key | Value", "Kunci | Nilai")
    assert gates.check(p, translated) == []


def test_gates_catch_structural_damage():
    p = _install_section()
    broken = p.text.replace("⟦CODE1⟧", "").replace("- two\n", "").replace("| retries | 3 |", "| retries | tiga |")
    errors = gates.check(p, broken.replace("## Install", "# Instalasi"))
    joined = " ".join(errors)
    assert "⟦CODE1⟧" in joined
    assert "heading level" in joined
    assert "numbers missing" in joined and "3" in joined
    assert "list items" in joined


def test_glossary_gate_and_placeholder_blindness(tmp_path: Path):
    g = Glossary(tmp_path / "g.json", "id", {"library": {"target": "library", "note": ""}})
    p = protect("Library callers can use `library_path` here.\n")
    assert gates.check(p, "Pemanggil perpustakaan dapat memakai ⟦IC1⟧ di sini.\n", g) == [
        "glossary: 'library' must be rendered as 'library'"
    ]
    assert gates.check(p, "Pemanggil library dapat memakai ⟦IC1⟧ di sini.\n", g) == []


def test_ledger_round_trip(tmp_path: Path):
    ledger = Ledger(tmp_path / "ledger.json", "id", "v1")
    ledger.put("README.md", "install#1", SectionState("abc", "teks", "ok"))
    ledger.save()
    again = Ledger.load(tmp_path / "ledger.json", "id")
    assert again.section("README.md", "install#1").text == "teks"
    assert again.prune("README.md", set()) == ["install#1"]


def test_large_sections_split_into_parts_that_rejoin_exactly():
    from doctwin.sync import PART_CHARS, _units

    paras = [f"## Big\n\nIntro ⟦CODE1⟧ paragraph."] + [("word " * 120).strip() + "." for _ in range(12)]
    text = "\n\n".join(paras) + "\n\n"
    units = _units("big#1", text)
    assert len(units) > 1 and all(len(u["text"]) <= PART_CHARS for u in units)
    assert units[0]["key"] == "big#1::p1" and units[0]["text"].startswith("## Big")
    assert "".join(u["lead"] + u["text"] + u["trail"] for u in units) == text
    single = _units("small#1", "## Small\n\nShort.\n\n")
    assert [u["key"] for u in single] == ["small#1"] and single[0]["trail"] == "\n\n"


def test_inline_code_wrapped_onto_the_next_line_is_one_span():
    text = 'answers it with `agent.run("yes",\n  thread_id=result.thread_id)`; a plain later `run()` starts a new thread.\n'
    p = protect(text)
    assert "a plain later" in p.text  # prose stays translatable
    assert p.text.count("⟦IC") == 2
    assert p.restore(p.text) == text


def test_quoted_program_output_is_protected_but_curly_prose_is_not():
    text = 'Returns "Confirmation denied. The action was not run." and never “walk away” autonomy.\n'
    p = protect(text)
    assert "Confirmation denied" not in p.text and "⟦Q1⟧" in p.text
    assert "walk away" in p.text
    assert p.restore(p.text) == text
