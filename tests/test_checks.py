"""Checker tests. They use the installed openminion CLI and package, never a model."""

from pathlib import Path

from docdrift import cli_check, py_check
from docdrift.extract import Snippet, blocks_from_markdown
from docdrift.sections import load_section


def shell(code: str) -> Snippet:
    return Snippet(id="t.md:1", path="t.md", line=1, lang="bash", code=code)


def python(code: str) -> Snippet:
    return Snippet(id="t.md:1", path="t.md", line=1, lang="python", code=code)


def kinds(found) -> list[str]:
    return [c.kind for c in found]


def test_valid_commands_pass():
    snip = shell(
        "openminion config init --provider echo\n"
        "openminion setup --provider gemini --model x --no-chat\n"
        'openminion run "hello"\n'
        "openminion --dir \"$PWD\" --add-dir ../shared\n"
    )
    assert cli_check.check_snippet(snip) == []


def test_unknown_flag_and_subcommand_are_reported_with_suggestions():
    found = cli_check.check_snippet(shell("openminion setup --no-chatt\nopenminion confg init"))
    assert kinds(found) == ["unknown_flag", "unknown_subcommand"]
    assert "--no-chat" in found[0].suggestions
    assert "config" in found[1].suggestions
    assert found[1].line == 2


def test_continuations_substitutions_and_pipes_are_split():
    snip = shell('out="$(openminion \\\n  config init --provider echo)"\nopenminion tools list | head\n# openminion bogus\n')
    commands = [c for _, c in cli_check.commands_in(snip)]
    assert commands == ["openminion config init --provider echo", "openminion tools list"]


def test_python_imports_kwargs_and_methods():
    code = (
        "from openminion import Agent, Agnt\n"
        "from openminion.api.nope import X\n"
        "with Agent(instructions='x', modle='y') as agent:\n"
        "    agent.run('hi', sesion_id='a')\n"
        "    agent.runn('x')\n"
    )
    found = py_check.check_snippet(python(code))
    assert sorted(kinds(found)) == sorted(
        ["missing_name", "missing_module", "unknown_kwarg", "unknown_kwarg", "missing_attribute"]
    )
    by_kind = {c.kind: c for c in found}
    assert by_kind["missing_name"].suggestions == ["Agent"]
    assert by_kind["missing_attribute"].line == 5


def test_valid_python_passes():
    code = (
        "from openminion import Agent, tool\n"
        "@tool(min_scope='READ_ONLY', idempotent=True)\n"
        "def f(x: str) -> str:\n"
        "    return x\n"
        "with Agent(instructions='x', tools=[f], session_id='s') as agent:\n"
        "    result = agent.run('hi', timeout_seconds=5)\n"
        "    print(result.text, result.session_id)\n"
    )
    assert py_check.check_snippet(python(code)) == []


def test_markdown_blocks_keep_absolute_lines(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# T\n\ntext\n\n```bash\nopenminion run hi\n```\n", encoding="utf-8")
    [block] = blocks_from_markdown(doc, tmp_path)
    assert block.line == 6 and block.kind == "shell"


def test_section_by_heading(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# A\n\n## B\nline b\n```\n# not a heading\n```\n## C\nline c\n", encoding="utf-8")
    label, text = load_section(tmp_path, "doc.md#B")
    assert label.startswith("doc.md:3-7")
    assert "line b" in text and "line c" not in text and "# not a heading" in text


def test_env_usage_tracks_dirs_and_long_prefix_constants(tmp_path: Path):
    from docdrift import env_check

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "runner.py").write_text(
        'PREFIX = "OPENMINION_DEMO_WRITE_APPROVED_"\nSHORT = "OPENMINION_TEST_"\nX = "OPENMINION_LIVE_FLAG"\n',
        encoding="utf-8",
    )
    exact = env_check.usage_in_checkout(tmp_path, "OPENMINION_LIVE_FLAG")
    assert exact.used_in == ["tests"] and exact.via_prefix == ""
    built = env_check.usage_in_checkout(tmp_path, "OPENMINION_DEMO_WRITE_APPROVED_CHAIN_ID")
    assert built.used_in == ["tests"] and built.via_prefix == "tests/runner.py:1"
    # "OPENMINION_TEST_" is too short to count as a builder prefix.
    assert env_check.usage_in_checkout(tmp_path, "OPENMINION_TEST_ANYTHING").used_in == []
