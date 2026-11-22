"""Render the YouTube thumbnail, 1280x720, in the same palette as the video.

    uv run --with numpy python demo/make_thumbnail.py      # writes demo/thumbnail.png
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenes as S  # noqa: E402
from build_video import browser  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "thumbnail.png"
RUN = S.MARKS["run"]

CSS = S.CSS + """
html,body{width:1280px;height:720px}
.t-top{position:absolute;left:56px;right:56px;top:38px;padding-bottom:18px;border-bottom:2px solid var(--fg);display:flex;justify-content:space-between;align-items:center}
.t-top .brand{font-size:36px;gap:14px}.t-top .mark i{width:12px;height:36px;border-radius:4px}
.t-top .eyebrow{font-size:18px;color:var(--fg2)}
h1{position:absolute;left:56px;top:150px;font-size:98px;line-height:1.03;letter-spacing:-.045em;font-weight:720}
h1 span{background:linear-gradient(transparent 46%,var(--hl) 46%,var(--hl) 94%,transparent 94%);padding:0 14px;margin-left:-14px}
.t-sub{position:absolute;left:56px;top:488px;font-size:31px;line-height:1.32;color:var(--fg2);font-weight:500}
.t-run{position:absolute;left:56px;bottom:40px;background:var(--fg);color:#F4F0E6;border-radius:12px;padding:13px 22px;font-family:var(--mono);font-size:22px}
.t-run b{color:#7BD3A4;letter-spacing:.08em;margin-right:14px}
.sheet{position:absolute;width:250px;background:#FFFEFA;border:1px solid var(--line2);border-radius:16px;padding:24px 22px;box-shadow:0 34px 54px -30px rgba(25,24,20,.55)}
.sheet .hd{font-size:14.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;margin-bottom:16px}
.sheet .ln{height:13px;border-radius:7px;background:#E0DACC;margin:13px 0}
.sheet .ln.src{background:#B7C4F6}.sheet .ln.new{background:var(--hl);box-shadow:0 0 0 1.5px #D6AE36}
.sheet .cb{margin:17px 0;font-size:13.5px;border:1.5px solid var(--ok);box-shadow:0 0 0 4px rgba(18,120,74,.16)}
.sheet .same{display:inline-flex;gap:7px;font-size:15px;font-weight:650;color:var(--ok)}
.swap{position:absolute;left:940px;top:246px;width:60px;height:60px;border-radius:50%;background:var(--sky);color:#fff;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:700;box-shadow:0 0 0 6px var(--bg)}
"""


def sheet(title: str, cls: str, left: int, top: int, turn: float, new: str) -> str:
    lines = lambda widths: "".join(f'<div class="ln" style="width:{w}%"></div>' for w in widths)  # noqa: E731
    return (
        f'<div class="sheet" style="left:{left}px;top:{top}px;transform:rotate({turn}deg)">'
        f'<div class="hd {cls}">{title}</div>{lines([94, 80, 88])}'
        '<div class="cb">openminion setup \\<br>&nbsp;&nbsp;--provider openai</div>'
        f'{lines([90, 66])}<div class="ln {new}" style="width:84%"></div>'
        f'<div class="same" style="margin-top:6px">{S.ICON_CHECK} code identical</div></div>'
    )


def page() -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>' + CSS + "</style></head><body>"
        '<div class="t-top"><div class="brand"><div class="mark"><i></i><i></i></div>DocTwin</div>'
        '<div class="eyebrow">OpenMinion 0.1 SDK &middot; Cortensor Hackathon #5</div></div>'
        "<h1>Docs change.<br>Translations<br><span>keep up.</span></h1>"
        '<div class="t-sub">Agents that sync translated docs,<br>without breaking a single command.</div>'
        f'<div class="t-run"><b>REAL RUN</b>{RUN["translated"]} translated &middot; {RUN["reused"]} reused &middot; 0 broken commands</div>'
        + sheet("English", "sky", 700, 176, -3.5, "src")
        + sheet("Bahasa Indonesia", "amber", 976, 204, 3, "new")
        + '<div class="swap">&rarr;</div></body></html>'
    )


def main() -> int:
    html = Path(tempfile.gettempdir()) / "doctwin-thumbnail.html"
    html.write_text(page(), encoding="utf-8")
    subprocess.run(
        [browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--user-data-dir={Path(tempfile.gettempdir()) / 'doctwin-video-profile-0'}", "--window-size=1280,720",
         "--virtual-time-budget=1500", f"--screenshot={OUT}", html.as_uri()],
        capture_output=True, timeout=120, check=False,
    )
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
