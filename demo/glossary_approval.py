"""Show the approval gate on the glossary: one proposed term is denied, one is approved.

The write tool `add_glossary_term` has the default scope, so OpenMinion's action
policy pauses it and calls our approval callback. A denied term must not reach
the glossary file; an approved one must.

    uv run python demo/glossary_approval.py .cache/demo-twin
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from docdrift.agents import AgentSettings, RunLog
from docdrift.cli import CONFIG, isolate_runtime, load_dotenv
from doctwin import agents
from doctwin.glossary import Glossary

DECISIONS = {"worktree": True, "handoff": False}


def main(out: Path) -> int:
    load_dotenv()
    isolate_runtime()
    glossary = Glossary.load(out / "glossary.id.json", "id")
    for term in DECISIONS:
        glossary.terms.pop(term, None)
    glossary.save()
    agents.GLOSSARY = glossary
    before = set(glossary.terms)

    def decide(tool_name: str, args: dict, approval_id: str) -> bool:
        source, target = args.get("source", "?"), args.get("target", "?")
        allow = tool_name == "add_glossary_term" and DECISIONS.get(str(source), False)
        print(f"OpenMinion paused {tool_name}: '{source}' -> '{target}'", flush=True)
        print(f"  operator decision: {'APPROVE' if allow else 'DENY'}", flush=True)
        return allow

    proposals = [
        agents.TermProposal(source="worktree", target="worktree", reason="Git term that Indonesian developers keep in English."),
        agents.TermProposal(source="handoff", target="serah terima", reason="Proposed Indonesian rendering."),
    ]
    settings = AgentSettings(config_path=str(CONFIG), agent_id="docdrift", timeout=120)
    log = RunLog(session_id=f"doctwin-glossary-demo-{datetime.now():%H%M%S}")
    print(f"glossary before: {len(before)} terms", flush=True)
    agents.propose_terms(settings, log, "id", proposals, decide)

    after = set(Glossary.load(out / "glossary.id.json", "id").terms)
    added = sorted(after - before)
    print(f"glossary after:  {len(after)} terms, added: {added}", flush=True)
    ok = added == ["worktree"]
    print("approved term written, denied term not written" if ok else "UNEXPECTED RESULT", flush=True)
    for t in log.turns:
        print(f"  turn {t.label}: ok={t.ok} {t.seconds:.1f}s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
