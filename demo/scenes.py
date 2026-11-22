"""HTML for every visual state of the demo video.

Each scene function takes a state number and returns the HTML for the stage
area. Terminal scenes leave a slot that build_video.py fills with the screen
recording; every other number comes from that recorded run and from the sync
reports in this repo.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "demo" / "logs"
RECORDING = ROOT / "demo" / "screen-recording.mp4"
MARKS = json.loads((LOGS / "marks.json").read_text(encoding="utf-8"))  # written by record_screen.py
V = MARKS["video"]  # step name -> seconds into the recording
CLIP_W, CLIP_H = 1222, 718  # size of the recorded window
OVERLAY = "<!--overlay-->"  # what follows is placed in stage pixels, outside the zoom
SPEED: dict[tuple[str, int], float] = {}  # (scene, state) -> playback speed, set by build_video.plan()

CSS = """
/* Paper, ink and one accent. Green and red appear only where something passed or was refused. */
:root{--bg:#F4F0E6;--panel:#FCFAF4;--panel2:#ECE7DA;--line:#DED8CA;--line2:#BFB7A5;--fg:#191814;--fg2:#3B3933;
--mut:#6C675C;--dim:#9C9689;--sky:#1F3FD0;--skyt:#E4E9FB;--amber:#8F5A00;--hl:#FFE27A;--gold:#F2B02A;
--ok:#12784A;--okt:#DFF0E5;--bad:#C5341F;--badt:#FBE5DF;--violet:#1F3FD0;
--sans:"Segoe UI Variable Display","Segoe UI",system-ui,sans-serif;--mono:"Cascadia Code","Cascadia Mono",Consolas,monospace}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden}
body{background:var(--bg);color:var(--fg);font-family:var(--sans);-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.glow,.gridbg{display:none}
.top{position:absolute;left:96px;right:96px;top:44px;padding-bottom:18px;border-bottom:1.5px solid var(--fg);display:flex;justify-content:space-between;align-items:center}
.brand{display:flex;align-items:center;gap:14px;font-weight:650;font-size:27px;letter-spacing:-.01em}
.mark{display:flex;gap:5px}.mark i{display:block;width:9px;height:27px;border-radius:3px;background:var(--sky)}.mark i+i{background:var(--gold)}
.eyebrow{font-size:17px;letter-spacing:.18em;text-transform:uppercase;color:var(--mut);font-weight:600}
.stage{position:absolute;left:96px;right:96px;top:128px;bottom:180px}
.cap{position:absolute;left:0;right:0;bottom:52px;display:flex;justify-content:center}
.cap span{max-width:1480px;text-align:center;font-size:32px;line-height:1.36;color:#F7F3EA;background:var(--fg);padding:15px 30px;border-radius:14px;font-weight:500;text-wrap:balance}
h1{font-size:76px;line-height:1.04;letter-spacing:-.035em;font-weight:680}
h2{font-size:50px;letter-spacing:-.028em;font-weight:660;line-height:1.12}
h3{font-size:30px;letter-spacing:-.015em;font-weight:640}
.sub{font-size:28px;color:var(--mut);line-height:1.4;margin-top:14px}
.mono{font-family:var(--mono)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:26px 30px}
.lab{font-size:16px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);font-weight:650;margin-bottom:12px}
.sky{color:var(--sky)}.amber{color:var(--amber)}.okc{color:var(--ok)}.badc{color:var(--bad)}.mutc{color:var(--mut)}
.chip{display:inline-flex;align-items:center;gap:9px;padding:7px 16px;border-radius:999px;border:1px solid var(--line2);font-size:21px;color:var(--fg2);background:var(--panel)}
.chip.ok{border-color:var(--ok);color:var(--ok);background:var(--okt)}.chip.bad{border-color:var(--bad);color:var(--bad);background:var(--badt)}
.chip.sky{border-color:var(--sky);color:var(--sky);background:var(--skyt)}.chip.amber{border-color:var(--amber);color:var(--amber);background:#FFF3C9}
.hide{visibility:hidden}.gone{display:none}.fade{opacity:.45}
.row{display:flex;gap:24px}.col{display:flex;flex-direction:column;gap:20px}.grow{flex:1;min-width:0}
pre{font-family:var(--mono);white-space:pre-wrap;word-break:break-word}
code{font-family:var(--mono);font-size:.9em;background:var(--panel2);border-radius:6px;padding:1px 7px;color:var(--fg)}
/* screen recording slot: build_video.py swaps the magenta for the footage */
.rec{position:absolute;left:0;width:1224px;border:1px solid var(--fg);border-radius:14px;overflow:hidden;background:#0c0c0c;box-shadow:0 34px 60px -30px rgba(25,24,20,.55),0 10px 22px -12px rgba(25,24,20,.3)}
.rec .hd{height:44px;display:flex;align-items:center;gap:11px;padding:0 16px;background:var(--fg);font-size:14.5px;font-weight:700;letter-spacing:.14em;color:#F4F0E6}
.rec .hd i{width:11px;height:11px;border-radius:50%;background:#F0503A;display:block}
.rec .hd em{font-style:normal;font-weight:500;letter-spacing:.02em;color:#A9A294;font-size:15.5px;margin-left:6px}
.rec .hd span{margin-left:auto;font-size:13.5px;font-weight:650;letter-spacing:.1em;text-transform:uppercase;padding:4px 12px;border-radius:999px;border:1px solid}
.rec .hd .ff{color:#F2B02A;border-color:rgba(242,176,42,.6)}.rec .hd .rt{color:#7BD3A4;border-color:rgba(123,211,164,.55)}
.rec .slot{width:1222px;background:#f0f}
.side{margin-left:1248px;height:764px;display:flex;flex-direction:column;gap:20px}
.side .card{padding:22px 26px}
.side5{margin-left:1057.6px;width:406.8px;display:flex;flex-direction:column;gap:16px}
.kr{display:flex;align-items:center;gap:18px;padding:15px 0;border-bottom:1px solid var(--line)}.kr:last-child{border-bottom:0}
.kr b{width:128px;flex:none;font-size:42px;font-weight:700;letter-spacing:-.03em;color:var(--sky);line-height:1}
.kr span{font-size:21px;color:var(--fg2);line-height:1.25}
.st{display:flex;align-items:center;gap:16px;padding:12px 0;border-bottom:1px solid var(--line)}.st:last-child{border-bottom:0}
.st i{font-style:normal;width:34px;height:34px;flex:none;border-radius:50%;border:1.5px solid var(--sky);color:var(--sky);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700}
.st b{display:block;font-size:23px;font-weight:640}.st span{display:block;font-size:18px;color:var(--mut);margin-top:2px}
/* s1 */
.pills{display:flex;gap:14px;align-items:center}
.pill{font-family:var(--mono);font-size:24px;padding:10px 18px;border-radius:12px;border:1px solid var(--line2);color:var(--dim);background:transparent}
.pill.on.s{color:#fff;background:var(--sky);border-color:var(--sky);font-weight:600}
.pill.on.a{color:var(--fg);background:var(--hl);border-color:#D6AE36;font-weight:600}
.pill.ghost{border-style:dashed;color:#B7B0A0}
.track{display:flex;align-items:center;gap:28px;padding:26px 30px}
.track .tl{width:250px;font-size:28px;font-weight:640}
/* s2 */
.word{display:flex;align-items:center;gap:30px}
.word .mark i{width:26px;height:118px;border-radius:9px}.word span{font-size:150px;font-weight:700;letter-spacing:-.045em;line-height:1}
.doc{width:330px;background:#FFFEFA;border:1px solid var(--line2);border-radius:14px;padding:22px;box-shadow:0 26px 44px -30px rgba(25,24,20,.45)}
.doc .hd{font-size:15px;letter-spacing:.14em;text-transform:uppercase;font-weight:650;margin-bottom:16px}
.ln{height:12px;border-radius:6px;background:#E0DACC;margin:11px 0}
.cb{border-radius:10px;background:var(--panel2);border:1px solid var(--line2);padding:12px 14px;margin:16px 0;font-family:var(--mono);font-size:15px;color:var(--fg2);line-height:1.5}
.cb.lock{border-color:var(--ok);box-shadow:0 0 0 4px rgba(18,120,74,.16)}
/* s3 */
.steps{display:grid;grid-template-columns:repeat(6,1fr);gap:18px}
.step{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px 20px 22px;min-height:150px}
.step .n{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;border:1.5px solid var(--line2);color:var(--mut);margin-bottom:14px}
.step .t{font-size:28px;font-weight:650;letter-spacing:-.01em}.step .s{font-size:20px;color:var(--mut);margin-top:6px;line-height:1.3}
.step.act{border-color:var(--sky);background:var(--skyt);box-shadow:0 0 0 1.5px var(--sky)}
.step.act .n{background:var(--sky);border-color:var(--sky);color:#fff}
.step.done .n{background:var(--okt);border-color:var(--ok);color:var(--ok)}
.step.todo{opacity:.45}
.detail{margin-top:24px;height:548px;padding:38px 44px;display:flex;flex-direction:column;justify-content:center}
.detail .what{font-size:40px;line-height:1.28;font-weight:600;letter-spacing:-.02em;max-width:1500px}
.ex{font-family:var(--mono);font-size:27px;line-height:1.62;color:var(--fg2);background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:24px 30px}
.ph{color:#fff;background:var(--sky);border-radius:6px;padding:0 7px;font-weight:650}
.checks{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.ck{display:flex;align-items:center;gap:12px;font-size:28px;padding:20px 22px;border:1px solid var(--line);border-radius:14px;background:var(--bg)}
.ck i{font-style:normal;color:var(--ok);font-weight:800}
/* tables */
table{border-collapse:collapse;width:100%;font-size:22px}
td,th{border:1px solid var(--line2);padding:10px 14px;text-align:left}
th{color:var(--mut);font-weight:600;background:var(--panel2)}
/* md */
.md h4{font-size:36px;letter-spacing:-.02em;margin-bottom:14px}
.md p{font-size:24px;line-height:1.48;color:var(--fg2);margin:11px 0}
.md pre{font-size:21px;line-height:1.48;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:12px 0;color:var(--fg2)}
.md mark{background:#D9E2FF;color:var(--fg);border-radius:5px;padding:1px 5px;box-shadow:0 0 0 1.5px rgba(31,63,208,.45)}
.md.tw mark{background:var(--hl);color:var(--fg);box-shadow:0 0 0 1.5px #D6AE36}
/* stats */
.big{font-size:150px;font-weight:720;letter-spacing:-.05em;line-height:.95}
.big small{font-size:56px;color:var(--mut);font-weight:600;letter-spacing:-.02em}
.fact{display:flex;align-items:baseline;gap:12px;font-size:22px;padding:12px 0;border-bottom:1px solid var(--line);line-height:1.3}
.fact:last-child{border-bottom:0}.fact i{font-style:normal;font-weight:800;color:var(--ok);width:26px}
.fact b{font-weight:680}
.unit{display:flex;align-items:center;gap:18px;margin:15px 0}
.unit .f{width:436px;font-family:var(--mono);font-size:20px;color:var(--fg2);text-align:right}
.unit .cells{display:flex;gap:6px}.cell{width:34px;height:34px;border-radius:8px;background:#DDD6C7;display:inline-block}
.cell.t{background:var(--sky)}.unit .k{font-size:21px;color:var(--sky);margin-left:8px;width:130px}
/* tabs */
.tabs{display:flex;gap:14px;margin-bottom:22px}
.tab{flex:1;padding:16px 22px;border-radius:14px;border:1px solid var(--line);background:var(--panel);font-size:24px;font-weight:620;color:var(--mut);display:flex;align-items:center;gap:14px}
.tab .n{width:34px;height:34px;border-radius:50%;border:1.5px solid var(--line2);display:flex;align-items:center;justify-content:center;font-size:17px}
.tab.act{border-color:var(--sky);color:var(--fg);background:var(--skyt);box-shadow:0 0 0 1.5px var(--sky)}.tab.act .n{background:var(--sky);color:#fff;border-color:var(--sky)}
.stamp{display:inline-block;border:3px solid var(--bad);color:var(--bad);font-weight:800;letter-spacing:.14em;font-size:30px;padding:8px 20px;border-radius:10px;transform:rotate(-4deg)}
/* browser frame */
.browser{border:1px solid var(--fg);border-radius:14px;overflow:hidden;background:#0d1117;box-shadow:0 34px 60px -34px rgba(25,24,20,.55)}
.browser .bar{height:46px;background:var(--fg);display:flex;align-items:center;gap:8px;padding:0 16px}
.browser .bar b{width:11px;height:11px;border-radius:50%;background:#4D4A43;display:block}
.browser .url{margin-left:14px;font-family:var(--mono);font-size:15px;color:#CFC8B8;background:#2B2A25;border:1px solid #3D3B35;border-radius:8px;padding:4px 14px;flex:1}
.browser img{display:block;width:100%}
/* bars */
.bar-row{display:flex;align-items:center;gap:14px;margin:9px 0;font-size:20px}
.bar-row .n{width:306px;color:var(--fg2)}.bar-row .trk{flex:1;height:20px;background:var(--panel2);border-radius:6px;position:relative}
.bar-row .fill{position:absolute;left:0;top:0;bottom:0;border-radius:6px;background:var(--sky)}
.bar-row .fill.x{background:repeating-linear-gradient(45deg,#C5341F,#C5341F 8px,#E39483 8px,#E39483 16px)}
.bar-row .v{width:118px;text-align:right;font-family:var(--mono);color:var(--fg2)}
.dots{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-top:18px}
.dot{border:1px solid rgba(197,52,31,.45);border-radius:14px;padding:14px 10px;text-align:center;background:var(--badt)}
.dot b{display:block;font-size:26px;color:var(--bad)}.dot span{display:block;font-size:16px;color:var(--fg2);margin-top:6px;line-height:1.25}
.crop{height:330px;overflow:hidden;background:#0d1117}.crop img{width:2160px;max-width:none;margin:-286px 0 0 -134px}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-top:22px}
.flow .card{padding:22px 22px 24px;min-height:300px}
.flow .k{font-size:15px;letter-spacing:.14em;text-transform:uppercase;font-weight:650;color:var(--ok);margin-bottom:12px}
.flow .k.v{color:var(--sky)}.flow h3{font-size:31px;line-height:1.16}.flow .d{font-size:22.5px;color:var(--fg2);margin-top:12px;line-height:1.36}
"""

ICON_CHECK = "&#10003;"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def vis(show: bool, extra: str = "") -> str:
    return f' class="{extra}"' if show else f' class="{extra} hide"'


def page(label: str, body: str, caption: str, zoom: float = 1.0) -> str:
    main, _, overlay = body.partition(OVERLAY)
    main = f'<div style="zoom:{zoom};width:{1728 / zoom:.0f}px;height:{772 / zoom:.0f}px">{main}</div>'
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>' + CSS + "</style></head><body>"
        '<div class="glow"></div><div class="gridbg"></div>'
        '<div class="top"><div class="brand"><div class="mark"><i></i><i></i></div>DocTwin</div>'
        f'<div class="eyebrow">{esc(label)}</div></div>'
        f'<div class="stage">{main}{overlay}</div>'
        f'<div class="cap"><span>{esc(caption)}</span></div></body></html>'
    )


def clip(sid: str, state: int, top: int, height: int) -> str:
    """A framed slot for the screen recording, `height` pixels of the window from its top edge."""

    speed = SPEED.get((sid, state), 1.0)
    if speed >= 1.25:
        n = f"{speed:.0f}" if speed >= 3 else f"{speed:.1f}"
        chip = f'<span class="ff">{n}&times; fast-forward</span>'
    else:
        chip = '<span class="rt">real time</span>'
    return (
        f'{OVERLAY}<div class="rec" style="top:{top}px"><div class="hd"><i></i>SCREEN RECORDING'
        f"<em>real run on gpt-4.1-mini</em>{chip}</div>"
        f'<div class="slot" style="height:{height}px"></div></div>'
    )


# --------------------------------------------------------------------------- s01
def s01(state: int) -> tuple[str, str, float]:
    versions = ["v0.1.18", "v0.1.19", "v0.1.20", "v0.1.21", "v0.1.22", "v0.1.23"]
    lit = {0: 1, 1: 3, 2: 6}.get(state, 6)
    en = "".join(f'<span class="pill {"on s" if i < lit else ""}">{v}</span>' for i, v in enumerate(versions))
    tr = "".join(
        f'<span class="pill {"on a" if i == 0 else "ghost"}">{v if i == 0 else "&nbsp;&nbsp;&nbsp;?&nbsp;&nbsp;&nbsp;"}</span>'
        for i, v in enumerate(versions)
    )
    title = "Docs change with every release." if state < 3 else ("Translations fall behind." if state == 3 else "Or they break quietly.")
    body = f"""
    <div style="height:100%;display:flex;flex-direction:column;justify-content:center">
    <h2>{title}</h2>
    <div class="card" style="margin-top:30px;padding:6px 4px">
      <div class="track"><div class="tl sky" style="width:200px">English docs</div><div class="pills">{en}</div></div>
      <div class="track" style="border-top:1px solid var(--line)"><div class="tl amber" style="width:200px">Translation</div><div class="pills">{tr}</div></div>
    </div>
    <div style="margin-top:18px;height:44px"><span{vis(state >= 3, "chip bad")}>the translation is 5 releases behind</span></div>
    <div{vis(state >= 4, "row")} style="margin-top:14px;align-items:stretch">
      <div class="card grow"><div class="lab">English source</div>
        <pre style="font-size:24px;color:var(--fg)">openminion setup --provider openai</pre>
        <div class="chip ok" style="margin-top:16px">{ICON_CHECK} runs</div></div>
      <div style="display:flex;align-items:center;font-size:40px;color:var(--dim)">&rarr;</div>
      <div class="card grow" style="border-color:rgba(197,52,31,.55)"><div class="lab">Re-translated without protection (illustration)</div>
        <pre style="font-size:24px;color:var(--bad)">openminion pengaturan --penyedia openai</pre>
        <div class="chip bad" style="margin-top:16px">&#10007; command no longer runs</div></div>
    </div></div>"""
    return "The problem", body, 1.22


# --------------------------------------------------------------------------- s02
def s02(state: int) -> tuple[str, str, float]:
    lines = lambda n: "".join(f'<div class="ln" style="width:{w}%"></div>' for w in n)  # noqa: E731
    doc = lambda head, cls, code: (  # noqa: E731
        f'<div class="doc"><div class="hd {cls}">{head}</div>{lines([92, 78, 86])}'
        f'<div class="cb {"lock" if state >= 2 else ""}">{code}</div>{lines([88, 64])}</div>'
    )
    code = "openminion setup \\<br>&nbsp;&nbsp;--provider openai"
    body = f"""
    <div class="row" style="align-items:center;height:100%">
      <div class="grow">
        <div class="word"><div class="mark"><i></i><i></i></div><span>DocTwin</span></div>
        <div{vis(state >= 1, "sub")} style="font-size:38px;max-width:860px;color:var(--fg2);margin-top:34px">
          Translated docs that stay in sync with the English source.</div>
        <div{vis(state >= 2, "row")} style="margin-top:34px;gap:14px;flex-wrap:wrap">
          <span class="chip ok">{ICON_CHECK} commands</span><span class="chip ok">{ICON_CHECK} links</span>
          <span class="chip ok">{ICON_CHECK} code blocks</span><span class="chip">byte-identical to the source</span></div>
        <div{vis(state >= 1, "row")} style="margin-top:30px;gap:12px">
          <span class="chip sky">OpenMinion 0.1 Python SDK</span><span class="chip">Cortensor Hackathon #5</span></div>
      </div>
      <div{vis(state >= 1, "row")} style="gap:22px;align-items:center">
        {doc("English", "sky", code)}
        <div style="font-size:40px;color:var(--dim)">&#8644;</div>
        {doc("Bahasa Indonesia", "amber", code)}
      </div>
    </div>"""
    return "What it is", body, 1.0


# --------------------------------------------------------------------------- s03
STEPS = [
    ("Split + ledger", "only changed sections"),
    ("Protect", "code becomes placeholders"),
    ("Translate", "agent + glossary tool"),
    ("Gate", "deterministic checks"),
    ("Review", "skeptical subagent"),
    ("Validate", "DocDrift vs the SDK"),
]


def s03(state: int) -> tuple[str, str, float]:
    cards = ""
    for i, (title, sub) in enumerate(STEPS, 1):
        cls = "act" if i == state else ("done" if i < state else ("todo" if state else ""))
        mark = ICON_CHECK if i < state else str(i)
        cards += f'<div class="step {cls}"><div class="n">{mark}</div><div class="t">{title}</div><div class="s">{sub}</div></div>'
    ph = lambda t: f'<span class="ph">{t}</span>'  # noqa: E731
    details = {
        0: ('One sync, six steps. Each one is small on purpose.',
            '<div class="row" style="gap:14px;flex-wrap:wrap">' + "".join(f'<span class="chip">{t}</span>' for t, _ in STEPS) + "</div>"),
        1: ("The ledger stores a digest per section. Unchanged sections are reused, with no model call.",
            '<div class="ex"><span class="d" style="color:var(--mut)">provider-capabilities/profile-facts&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;unchanged &rarr; reused<br>'
            "provider-capabilities/request-requirements&nbsp;unchanged &rarr; reused<br>"
            'provider-capabilities/inspecting-the-matrix unchanged &rarr; reused</span><br>'
            '<span style="color:var(--sky)">provider-capabilities/http-connection-reuse digest changed &rarr; translate</span></div>'),
        2: ("The model never sees code, so it cannot break it.",
            f'<div class="ex">Set <code>http_connection_reuse_enabled: false</code> on a provider &hellip;<br>'
            f'<span style="color:var(--mut)">&darr; protected</span><br>Set {ph("&#10214;IC1&#10215;")} on a provider &hellip; {ph("&#10214;CODE1&#10215;")}</div>'),
        3: ("An OpenMinion agent translates, with a read-only glossary tool and a typed output.",
            f'<div class="ex">Tetapkan {ph("&#10214;IC1&#10215;")} pada sebuah provider &hellip; {ph("&#10214;CODE1&#10215;")}<br>'
            '<span style="color:var(--amber)">glossary_lookup("provider") &rarr; provider (keep English)</span></div>'),
        4: ("No model involved here. A failure goes back to the translator once, with the errors quoted.",
            '<div class="checks">' + "".join(f'<div class="ck"><i>{ICON_CHECK}</i>{t}</div>' for t in
                                             ["placeholders exact", "heading level", "numbers kept", "list items",
                                              "table shape", "glossary terms", "length ratio", "no new code fences"]) + "</div>"),
        5: ("A bounded subagent compares source and translation, and is told to look for problems.",
            '<div class="ex">subagent(parent, name="doctwin-reviewer", output_type=ReviewBatch)<br>'
            '<span style="color:var(--ok)">{"key": "http-connection-reuse", "faithful": true, "issues": []}</span><br>'
            '<span style="color:var(--mut)">checks meaning, flipped negations, changed numbers</span></div>'),
        6: ("Every command and import in the translated file is checked against the installed SDK.",
            f'<div class="ex">openminion setup --provider openai&nbsp;&nbsp;<span style="color:var(--ok)">{ICON_CHECK} matches --help</span><br>'
            f'from openminion import Agent, tool&nbsp;&nbsp;<span style="color:var(--ok)">{ICON_CHECK} resolves in the package</span><br>'
            '<span style="color:var(--ok)">no broken commands or imports</span></div>'),
    }
    what, example = details[state]
    body = f"""
    <div class="steps">{cards}</div>
    <div class="card detail"><div class="what">{what}</div><div style="margin-top:22px">{example}</div></div>"""
    return "How a sync works", body, 1.0


# --------------------------------------------------------------------------- terminal helpers
def md_html(text: str, mark: str = "") -> str:
    """Tiny Markdown renderer for one docs section: heading, paragraphs, inline code, one code fence."""

    out, in_code, code, para = [], False, [], []

    def flush() -> None:
        if para:
            body = esc(" ".join(para))
            body = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)
            if mark and esc(mark) in body:
                body = body.replace(esc(mark), f"<mark>{esc(mark)}</mark>")
            out.append(f"<p>{body}</p>")
            para.clear()

    for line in text.strip().splitlines():
        if line.startswith("```"):
            if in_code:
                out.append("<pre>" + esc("\n".join(code)) + "</pre>")
                code.clear()
            else:
                flush()
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif line.startswith("#"):
            flush()
            out.append(f"<h4>{esc(line.lstrip('# '))}</h4>")
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    return "".join(out)


# --------------------------------------------------------------------------- s04
def s04(state: int) -> tuple[str, str, float]:
    run, seconds = MARKS["run"], round(MARKS["sync_seconds"])
    assert run["validation"] == "no broken commands or imports", run["validation"]
    if state >= 9:  # the result, side by side
        sec = json.loads((LOGS / "section.json").read_text(encoding="utf-8"))
        new_id = sec["id"].strip().split(". ")[-1]
        body = f"""
        <div class="row" style="height:100%;align-items:stretch">
          <div class="card grow md"><div class="lab sky">English source &middot; {esc(sec["file"])}</div>{md_html(sec["en"], sec["new_en"])}</div>
          <div class="card grow md tw"><div class="lab amber">Bahasa Indonesia &middot; written in this run</div>{md_html(sec["id"], new_id)}
            <div class="row" style="gap:12px;margin-top:18px"><span class="chip ok">{ICON_CHECK} code block byte-identical</span>
            <span class="chip ok">{ICON_CHECK} reviewer: faithful</span></div></div>
        </div>"""
        return "Live run on gpt-4.1-mini", body, 1.0

    changed = (
        '<div class="card"><div class="lab">What changed upstream</div>'
        '<div class="mono" style="font-size:17px;color:var(--mut)">docs/provider-capabilities.md</div>'
        '<div class="mono" style="font-size:19.5px;color:var(--ok);line-height:1.5;margin-top:12px">'
        "+ Reuse never shares a connection between two providers.</div></div>"
    )
    if state >= 7:
        kpis = [
            (str(run["translated"]), "section translated"), (str(run["reused"]), "reused, no model call"),
            (f'{run["files_with_identical_code"]} / {run["files"]}', "files with identical code blocks"),
            ("0", "broken commands or imports"), (f"{seconds} s", "wall time, about $0.01"),
        ]
        rest = ('<div class="card grow"><div class="lab">This run</div>'
                + "".join(f'<div class="kr"><b>{a}</b><span>{b}</span></div>' for a, b in kpis) + "</div>")
    else:
        stages = [("Translator agent", "writes the section"), ("Gates", "structure, numbers, glossary"),
                  ("Reviewer subagent", "checks the meaning"), ("DocDrift", "checks every command")]
        rest = (
            f'<div{vis(state >= 3, "card")} style="display:flex;align-items:center;gap:22px">'
            '<div class="big" style="font-size:80px;white-space:nowrap;flex:none">1<small style="font-size:40px"> / 54</small></div>'
            '<div><div class="lab" style="margin-bottom:6px">The plan</div>'
            '<div style="font-size:22px;color:var(--fg2);line-height:1.3">Only one section goes to the model.</div></div></div>'
            f'<div{vis(state >= 4, "card grow")}><div class="lab">What the sync runs</div>'
            + "".join(f'<div class="st"><i>{n}</i><div><b>{a}</b><span>{b}</span></div></div>' for n, (a, b) in enumerate(stages, 1))
            + "</div>"
        )
    return "Live run on gpt-4.1-mini", f'<div class="side">{changed}{rest}</div>' + clip("s04-live", state, 0, CLIP_H), 1.0


# --------------------------------------------------------------------------- s05
def s05(state: int) -> tuple[str, str, float]:
    active = 0 if state == 0 else (1 if state <= 2 else (2 if state <= 5 else 3))
    names = ["Gates", "Human approval", "Human edits"]
    tabs = "".join(
        f'<div class="tab {"act" if i == active else ""}"><span class="n">{i}</span>{n}</div>' for i, n in enumerate(names, 1)
    )
    if active == 0:
        cards = [
            ("Gates", "Deterministic checks on every translated section. A section that fails stays in English."),
            ("Human approval", "The model can propose glossary terms. Only a human can write one."),
            ("Human edits", "A translated file that someone edited by hand is never overwritten."),
        ]
        panel = '<div class="row" style="align-items:stretch;height:420px">' + "".join(
            f'<div class="card grow" style="padding:36px;display:flex;flex-direction:column;justify-content:center">'
            f'<h3 style="font-size:40px">{t}</h3><div class="sub" style="font-size:27px">{d}</div></div>' for t, d in cards
        ) + "</div>"
    elif active == 1:
        panel = f"""
        <div style="height:500px;display:flex;flex-direction:column;justify-content:center">
        <div class="row" style="align-items:stretch">
          <div class="card grow"><div class="lab sky">English source &middot; docs/turn-budgets.md</div>
            <table style="font-size:25px"><tr><th>Observation</th><th>Disabled</th><th>Enabled</th></tr>
            <tr><td>Measured turn time</td><td class="mono">33.76 s</td><td class="mono">42.04 s</td></tr></table></div>
          <div class="card grow" style="border-color:rgba(197,52,31,.55)"><div class="lab badc">What the model returned (first sync, recorded)</div>
            <table style="font-size:25px"><tr><th>Pengamatan</th><th>Dinonaktifkan</th><th>Diaktifkan</th></tr>
            <tr><td>Waktu giliran yang diukur</td><td class="mono badc">33,76 s</td><td class="mono badc">42,04 s</td></tr></table></div>
        </div>
        <div{vis(state >= 2, "card")} style="margin-top:24px;display:flex;align-items:center;gap:34px;border-color:rgba(197,52,31,.55)">
          <span class="stamp">REFUSED</span>
          <div><div class="mono" style="font-size:22px;color:var(--bad)">gate: numbers missing from translation: 0.0393, 0.0430, 33.76, 42.04</div>
          <div class="sub" style="font-size:25px;margin-top:10px;color:var(--fg2)">The section stayed in English. On the next sync it passed, with the decimal points intact.</div></div>
        </div></div>"""
    elif active == 2:
        code = ('<div class="ex" style="font-size:16px;line-height:1.55;padding:16px 18px">'
                '<span style="color:var(--amber)">@tool</span>(description="Add a term")<br>'
                "def add_glossary_term(<br>&nbsp;&nbsp;&nbsp;&nbsp;source, target, reason):<br>&nbsp;&nbsp;&nbsp;&nbsp;&hellip;<br>"
                '<span style="color:var(--mut)"># default scope: the action policy<br># pauses it and asks first</span></div>')
        after = (f'<div{vis(state >= 5, "card")} style="padding:18px 20px"><div class="lab">glossary.id.json after the run</div>'
                 '<div class="mono" style="font-size:17px;color:var(--ok)">+ "worktree": "worktree"</div>'
                 '<div class="mono" style="font-size:17px;color:var(--dim);margin-top:6px">&nbsp;&nbsp;"handoff": not written</div></div>')
        panel = f'<div class="side5">{code}{after}</div>' + clip("s05-guardrails", state, 110, 616)
    else:
        panel = (
            '<div class="side5">'
            '<div class="card" style="padding:18px 20px"><div class="lab amber">A person edits the translation</div>'
            '<div class="mono" style="font-size:15px;color:var(--mut)">docs/provider-capabilities.md</div>'
            '<div class="mono" style="font-size:17px;color:var(--ok);margin-top:10px">+ Catatan dari editor manusia.</div></div>'
            '<div class="card" style="padding:18px 20px"><div class="lab">How it knows</div>'
            '<div class="sub" style="font-size:19px;margin-top:0;color:var(--fg2)">The ledger keeps a digest of every file '
            "DocTwin wrote. A different digest means a human was here.</div></div>"
            f'<div{vis(state >= 7, "card")} style="padding:18px 20px;border-color:rgba(18,120,74,.55)"><div class="lab okc">Result</div>'
            '<div class="sub" style="font-size:19px;margin-top:0;color:var(--fg2)">The file is left alone. '
            "Nothing a person wrote is overwritten.</div></div></div>"
        ) + clip("s05-guardrails", state, 110, 616)
    return "Guardrails", f'<div class="tabs">{tabs}</div>{panel}', 1.18


# --------------------------------------------------------------------------- s06
def s06(state: int) -> tuple[str, str, float]:
    report = json.loads((ROOT / "translations/id/.doctwin/reports/20261119-145805/report.json").read_text(encoding="utf-8"))
    files: dict[str, list[bool]] = {}
    for s in report["sections"]:
        files.setdefault(s["file"], []).append(s["action"] == "translated")
    rows = ""
    for name, cells in files.items():
        n = sum(cells)
        boxes = "".join(f'<span class="cell {"t" if (c and state >= 1) else ""}"></span>' for c in cells)
        note = ("new file" if n == len(cells) else f"{n} changed") if state >= 1 and n else ("" if state >= 1 else "")
        rows += f'<div class="unit"><span class="f">{esc(name)}</span><span class="cells">{boxes}</span><span class="k">{note}</span></div>'
    total = sum(len(c) for c in files.values())
    changed = sum(sum(c) for c in files.values())
    body = f"""
    <div class="row" style="align-items:stretch;height:100%">
      <div class="card" style="width:470px;display:flex;flex-direction:column;justify-content:center">
        <div class="lab">OpenMinion docs &middot; v0.1.18 &rarr; v0.1.23</div>
        <div class="big {'sky' if state >= 1 else ''}">{changed if state >= 1 else total}<small> {'/ ' + str(total) if state >= 1 else 'sections'}</small></div>
        <div class="sub" style="font-size:27px">{'sections went to the model' if state >= 1 else 'in 7 files, translated into Bahasa Indonesia'}</div>
        <div{vis(state >= 2)} style="margin-top:30px"><div class="big" style="font-size:104px;color:var(--fg2)">{total - changed}<small> reused</small></div>
          <div class="sub" style="font-size:24px">straight from the ledger, untouched</div></div>
      </div>
      <div class="card grow" style="display:flex;flex-direction:column;justify-content:center"><div class="lab">One square per section &middot; real sync report</div>
        <div style="margin-top:8px">{rows}</div>
        <div class="row" style="gap:12px;margin-top:22px;flex-wrap:wrap">
          <span class="chip"><span class="cell t" style="width:18px;height:18px"></span>translated in this sync</span>
          <span class="chip"><span class="cell" style="width:18px;height:18px"></span>reused</span>
          <span{vis(state >= 2, "chip ok")}>{ICON_CHECK} code blocks identical in 7 of 7 files</span>
          <span{vis(state >= 2, "chip ok")}>{ICON_CHECK} 0 broken commands</span></div>
      </div>
    </div>"""
    return "Proof on real docs", body, 1.0


# --------------------------------------------------------------------------- s07
def s07(state: int) -> tuple[str, str, float]:
    items = [
        ("Agents with typed output", "Agent(output_type=TranslationBatch)", "translator and reviewer"),
        ("Read-only tool", '@tool(min_scope="READ_ONLY")', "glossary_lookup runs without prompts"),
        ("Approval callback", "run(approval_callback=decide)", "a human approves every glossary write"),
        ("Forced tools", 'forced_tools=["add_glossary_term"]', "the keeper must use the gated tool"),
        ("Subagent", 'subagent(parent, name="reviewer")', "own instructions, output type, timeout"),
        ("Sessions + diagnostics", "ProviderError &middot; run_id &middot; stats", "a per-turn table in every report"),
    ]
    lit = {0: 0, 1: 2, 2: 6}[state]
    cards = "".join(
        f'<div class="card {"" if i < lit else "fade"}" style="padding:30px 30px 34px;{"border-color:rgba(31,63,208,.6)" if i < lit else ""}">'
        f'<h3>{t}</h3><div class="mono" style="font-size:19.5px;color:var(--sky);margin-top:14px">{c}</div>'
        f'<div class="sub" style="font-size:21px;margin-top:12px">{d}</div></div>'
        for i, (t, c, d) in enumerate(items)
    )
    body = f"""
    <div style="height:100%;display:flex;flex-direction:column;justify-content:center">
    <h2>Built on the OpenMinion 0.1 Python SDK</h2>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:32px">{cards}</div></div>"""
    return "OpenMinion SDK", body, 1.15


# --------------------------------------------------------------------------- s08
def s08(state: int) -> tuple[str, str, float]:
    def card(kind: str, title: str, text: str, show: bool, violet: bool = False) -> str:
        return (f'<div{vis(show, "card")}><div class="k {"v" if violet else ""}">{kind}</div><h3>{title}</h3>'
                f'<div class="d">{text}</div></div>')

    check = ('<div class="mono" style="font-size:19px;margin-top:12px;line-height:1.5"><span class="badc">0.1.23 &rarr; json_invalid</span><br>'
             '<span class="okc">0.1.24 &rarr; missing: summary</span></div>')
    body = f"""
    <div class="browser"><div class="bar"><b></b><b></b><b></b><span class="url">github.com/openminion/openminion/pull/810</span></div>
      <div class="crop"><img src="../../assets/pr810.png"></div></div>
    <div class="flow">
      {card("Reported", "Issue #803", "Validation errors hid the real cause of a failure.", state >= 1)}
      {card("Confirmed", "In scope", "The maintainers reproduced it and asked for the fix.", state >= 2)}
      {card("Merged", "PR #810", "Our fix and tests. 18 of 18 hosted checks passed.", state >= 2, True)}
      {card("Shipped", "OpenMinion 0.1.24", "Verified on the published package." + check, state >= 2, True)}
      {card("Reported + proposed fix", "Issue #804", "A message over 12,000 characters returns a canned reply marked completed.", state >= 3)}
    </div>"""
    return "Giving back to OpenMinion", body, 1.0


# --------------------------------------------------------------------------- s09
def s09(state: int) -> tuple[str, str, float]:
    direct = [
        ("oss-20b &middot; plain chat", 17.4, False), ("oss-20b &middot; one tool call", 19.9, False),
        ("oss-20b &middot; forced tool_choice", 24.9, False), ("oss-20b &middot; OpenMinion's request", 69.6, False),
        ("gemma4 &middot; OpenMinion's request", 62.5, False), ("qwen &middot; same request", 300.0, True),
    ]
    scale = 130.0
    bars = "".join(
        f'<div class="bar-row"><span class="n">{n}</span><span class="trk"><span class="fill {"x" if bad else ""}" style="width:{min(v, scale) / scale * 100:.1f}%"></span></span>'
        f'<span class="v {"badc" if bad else ""}">{"&gt; 300 s" if bad else f"{v:.1f} s"}</span></div>'
        for n, v, bad in direct
    )
    runs = ["stall, 478 s", "502, then timeout", "stall, 481 s", "502 on tool arguments", "canned reply (#719)", "prose, not JSON", "stall, 904 s"]
    dots = "".join(f'<div class="dot"><b>&#10007;</b><span>run {i}<br>{r}</span></div>' for i, r in enumerate(runs, 1))
    body = f"""
    <div style="height:100%;display:flex;flex-direction:column;justify-content:center">
    <div class="row" style="align-items:center;gap:14px;flex-wrap:wrap">
      <h2 style="font-size:44px;margin-right:14px">Cortensor Portal, tested for real</h2>
      <span class="chip sky">free-plan key</span><span class="chip">oss-20b</span><span class="chip">gemma4</span><span class="chip">qwen</span></div>
    <div class="row" style="align-items:stretch;margin-top:26px">
      <div{vis(state >= 1, "card grow")}><div class="lab okc">Direct API calls &middot; seconds per request</div>
        <h3>They work, tool calls included</h3><div style="margin-top:14px">{bars}</div></div>
      <div{vis(state >= 2, "card")} style="width:600px"><div class="lab badc">Full OpenMinion turns</div>
        <h3>0 of 7 completed</h3><div class="dots" style="grid-template-columns:repeat(4,1fr)">{dots}</div></div>
    </div>
    <div{vis(state >= 3, "card")} style="margin-top:20px;display:flex;align-items:center;gap:18px;padding:18px 26px">
      <span class="chip sky">request IDs logged</span>
      <span style="font-size:22px;color:var(--fg2)">Every run is in WHAT_WE_LEARNED.md, Part D. Raw logs are in evidence/portal/.</span></div></div>"""
    return "Cortensor Portal + Gemma4", body, 1.25


# --------------------------------------------------------------------------- s10
def s10(state: int) -> tuple[str, str, float]:
    body = f"""
    <div style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
      <div class="word"><div class="mark"><i></i><i></i></div><span>DocTwin</span></div>
      <div{vis(state >= 1, "sub")} style="font-size:44px;color:var(--fg2);margin-top:30px">Translated docs that stay in sync, and stay correct.</div>
      <div{vis(state >= 1, "row")} style="gap:14px;margin-top:36px;justify-content:center">
        <span class="chip sky" style="font-size:25px;padding:9px 20px">github.com/bagusardin25/openminion-docdrift</span>
        <span class="chip" style="font-size:25px;padding:9px 20px">OpenMinion 0.1 SDK</span>
        <span class="chip" style="font-size:25px;padding:9px 20px">20 tests</span><span class="chip" style="font-size:25px;padding:9px 20px">MIT</span></div>
      <div{vis(state >= 1)} style="margin-top:46px;font-size:21px;color:var(--mut);max-width:1300px;line-height:1.5">
        Terminal scenes are a screen recording of a real run on gpt-4.1-mini; waiting is fast-forwarded.<br>
        The whole recording, uncut and in real time, is demo/screen-recording.mp4 in the repository.<br>
        The voice-over is AI-generated (OpenAI text-to-speech).</div>
    </div>"""
    return "Cortensor Hackathon #5", body, 1.0


SCENES = {
    "s01-problem": s01, "s02-intro": s02, "s03-how": s03, "s04-live": s04, "s05-guardrails": s05,
    "s06-results": s06, "s07-sdk": s07, "s08-upstream": s08, "s09-portal": s09, "s10-close": s10,
}

# For every scene: one list per narration beat, holding the visual states shown during that beat.
# A state is a number, or (number, weight) to give it a larger or smaller share of the beat.
STATES = {
    "s01-problem": [[0, 1, 2], [3], [4]],
    "s02-intro": [[0], [1], [2]],
    "s03-how": [[0], [1], [2], [3], [4], [5], [6]],
    "s04-live": [[(0, 2), (1, 1)], [(2, 3), (3, 1)], [4, 5], [(6, 3), (7, 11)], [(8, 2), (9, 3)]],
    "s05-guardrails": [[0], [1], [2], [3], [4, 5], [(6, 3), (7, 2)]],
    "s06-results": [[0], [1], [2]],
    "s07-sdk": [[0], [1], [2]],
    "s08-upstream": [[0], [1], [2], [3]],
    "s09-portal": [[0], [1], [2], [3]],
    "s10-close": [[0], [1]],
}

# Which part of the screen recording plays in which states: (scene, states, from, to), where from and
# to are (step mark, offset in seconds). A stretch longer than its time on screen is fast-forwarded.
CLIPS = [
    ("s04-live", [0], ("start", 0.3), ("plan.prompt", 0.65)),  # the prompt
    ("s04-live", [1], ("plan.prompt", 0.65), ("plan.typed", 0.15)),  # typing the plan command
    ("s04-live", [2, 3], ("plan.typed", 0.15), ("plan.done", 1.6)),  # the plan runs
    ("s04-live", [4], ("sync.prompt", 0.4), ("sync.typed", 0.4)),  # typing the sync command
    ("s04-live", [5, 6], ("sync.typed", 0.4), ("sync.done", -1.0)),  # the sync runs
    ("s04-live", [7], ("sync.done", -1.0), ("sync.done", 2.6)),  # its summary
    ("s04-live", [8], ("diff.typed", -0.1), ("diff.done", 2.3)),  # git diff of the translated file
    ("s05-guardrails", [3], ("glossary.prompt", 0.3), ("glossary.typed", 1.2)),
    ("s05-guardrails", [4], ("glossary.typed", 1.2), ("glossary.done", -1.5)),  # first term approved, then a long wait
    ("s05-guardrails", [5], ("glossary.done", -1.5), ("glossary.done", 1.5)),  # second term denied, result
    ("s05-guardrails", [6], ("edit.prompt", 0.3), ("resync.done", -0.6)),  # a human edit, then the next sync starts
    ("s05-guardrails", [7], ("resync.done", -0.6), ("resync.done", 1.6)),  # its output: the file is left alone
]
