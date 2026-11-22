"""Record the real terminal session that the demo video shows.

    uv run --with imageio-ffmpeg python demo/record_screen.py          # full session, about 100 s
    uv run --with imageio-ffmpeg python demo/record_screen.py --test   # one frame, to check the window

Opens a Windows Terminal window, runs demo/session.ps1 in it, and records only
that window (Windows Graphics Capture through ffmpeg's gfxcapture), so nothing
else on the desktop is captured. Writes to demo/out/rec/:

    session.mkv   the recording, real time, unedited
    marks.jsonl   wall-clock timestamps of every step, written by the session

and then the files the video build reads:

    demo/screen-recording.mp4   a playable copy of the whole recording
    demo/logs/marks.json        where each step starts in that file, plus the run's numbers
    demo/logs/section.json      the section the sync wrote, English and Indonesian
    demo/logs/sync-report.md    DocTwin's own report of the recorded sync
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "demo" / "out" / "rec"
LOGS = ROOT / "demo" / "logs"
VIDEO = ROOT / "demo" / "screen-recording.mp4"
SOURCE, TWIN, PAGE = ".cache/demo-source", ".cache/demo-twin", "docs/provider-capabilities.md"
HUMAN_NOTE = "Catatan dari editor manusia."
TITLE = "DocTwin demo"
X, Y, WIDTH, HEIGHT = 24, 24, 1240, 728  # physical pixels

user32 = ctypes.windll.user32
ctypes.windll.shcore.SetProcessDpiAwareness(2)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
]


def find_window(title: str) -> int | None:
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value == title:
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def rect(hwnd: int) -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def terminal() -> str:
    alias = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "wt.exe"
    found = shutil.which("wt.exe") or (str(alias) if alias.exists() else None)
    if not found:
        raise SystemExit("Windows Terminal (wt.exe) was not found")
    return found


def first_change(ffmpeg: str, path: Path) -> float:
    """Seconds into the recording at which the screen first changes: the session's 'start' mark."""

    w, h = 320, 188
    proc = subprocess.Popen(
        [ffmpeg, "-loglevel", "error", "-t", "40", "-i", str(path), "-vf", f"scale={w}:{h}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE,
    )
    assert proc.stdout is not None
    first, n = None, 0
    try:
        while True:
            buf = proc.stdout.read(w * h)
            if len(buf) < w * h:
                raise SystemExit("the recording never changes; nothing was captured")
            if first is None:
                first = buf
            elif sum(1 for a, b in zip(buf, first) if abs(a - b) > 40) >= 12:
                return n / 30
            n += 1
    finally:
        proc.kill()


def finish() -> int:
    """Turn the raw capture into the files the video build reads (all under demo/)."""

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    raw = REC / "session.mkv"
    LOGS.mkdir(parents=True, exist_ok=True)

    # 1. A playable copy of the whole recording, real time, uncut.
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-preset", "slow",
         "-crf", "18", "-g", "60", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(VIDEO)],
        check=True,
    )
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(VIDEO)], capture_output=True, text=True).stderr
    h, m, s = probe.split("Duration: ")[1].split(",")[0].split(":")
    duration = int(h) * 3600 + int(m) * 60 + float(s)

    # 2. Step timestamps as seconds into that file.
    marks = [json.loads(line) for line in (REC / "marks.jsonl").read_text(encoding="ascii").splitlines() if line.strip()]
    offset = first_change(ffmpeg, VIDEO)
    t0 = marks[0]["ms"]
    video = {m["name"]: round(offset + (m["ms"] - t0) / 1000, 2) for m in marks}

    # 3. What the recorded sync reported, and the section it wrote.
    reports = sorted((ROOT / TWIN / ".doctwin" / "reports").iterdir())
    report = next(r for r in reports if json.loads((r / "report.json").read_text(encoding="utf-8"))["counts"].get("translated"))
    data = json.loads((report / "report.json").read_text(encoding="utf-8"))
    shutil.copy2(report / "report.md", LOGS / "sync-report.md")
    wrote = next(s for s in data["sections"] if s["action"] == "translated")
    run = {
        "report": report.name,
        "translated": data["counts"].get("translated", 0),
        "reused": data["counts"].get("unchanged", 0),
        "files": len(data["files"]),
        "files_with_identical_code": sum(1 for f in data["files"] if f["code_blocks_identical"]),
        "validation": data["validation"]["summary"],
        "attempts": wrote["attempts"],
        "turns": [{"role": t["role"], "ok": t["ok"], "seconds": round(t["seconds"], 1)} for t in data["turns"]],
    }
    (LOGS / "marks.json").write_text(json.dumps({
        "recording": VIDEO.name, "duration": round(duration, 2), "start": offset,
        "sync_seconds": round(video["sync.done"] - video["sync.typed"], 1), "video": video, "run": run,
    }, indent=2) + "\n", encoding="utf-8")

    from doctwin.segment import split_sections

    en = split_sections((ROOT / SOURCE / PAGE).read_text(encoding="utf-8"))
    idn = split_sections((ROOT / TWIN / PAGE).read_text(encoding="utf-8"))
    index = next(i for i, s in enumerate(en) if s.key == wrote["key"])
    (LOGS / "section.json").write_text(json.dumps({
        "file": PAGE, "key": wrote["key"],
        "en": en[index].text, "id": idn[index].text.replace(HUMAN_NOTE, "").rstrip() + "\n",
        "new_en": "Reuse never shares a connection between two providers.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{VIDEO.relative_to(ROOT)}: {duration:.1f} s, {VIDEO.stat().st_size / 1e6:.1f} MB; session starts at {offset:.2f} s")
    print(f"sync took {video['sync.done'] - video['sync.typed']:.1f} s; run: {run}")
    return 0


def main() -> int:
    if "--finish" in sys.argv:
        return finish()
    test = "--test" in sys.argv
    REC.mkdir(parents=True, exist_ok=True)
    for name in ("go", "stop", "marks.jsonl"):
        (REC / name).unlink(missing_ok=True)
    if find_window(TITLE):
        print(f"a window titled '{TITLE}' is already open; close it first")
        return 2

    previous = user32.GetForegroundWindow()
    session = ["powershell.exe", "-NoLogo", "-NoProfile", "-File", "demo\\session.ps1", "-Rec", "demo/out/rec"]
    # This script may be running in a throwaway virtualenv (uv run --with ...); keep it out of the session.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    throwaway = os.sep.join(("uv", "cache"))
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if throwaway not in p)
    subprocess.Popen(
        [terminal(), "-w", "new", "new-tab", "--title", TITLE, "--suppressApplicationTitle", "-d", str(ROOT),
         *session, *(["-Test"] if test else [])],
        cwd=ROOT, env=env,
    )
    hwnd = None
    for _ in range(100):
        hwnd = find_window(TITLE)
        if hwnd:
            break
        time.sleep(0.1)
    if not hwnd:
        print("the terminal window did not appear")
        return 1
    # Keep it on top and in one place while recording, then hand the keyboard back.
    user32.SetWindowPos(hwnd, wintypes.HWND(-1), X, Y, WIDTH, HEIGHT, 0x0010)  # HWND_TOPMOST, SWP_NOACTIVATE
    if previous:
        user32.SetForegroundWindow(previous)
    time.sleep(1.2)
    print("window:", rect(hwnd))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    grab = f"gfxcapture=hwnd={hwnd}:capture_cursor=0:max_framerate=30:width=-2:height=-2,hwdownload,format=bgra"
    try:
        if test:
            out = REC / "test.png"
            done = subprocess.run(
                [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "lavfi", "-i", grab,
                 "-frames:v", "1", "-update", "1", str(out)],
                capture_output=True, text=True, timeout=60,
            )
            print(done.stderr.strip()[-600:] or "captured", out)
            return done.returncode

        out = REC / "session.mkv"
        log = (REC / "ffmpeg.log").open("w", encoding="utf-8")
        proc = subprocess.Popen(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-f", "lavfi", "-i", grab,
             "-fps_mode", "cfr", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "10",
             "-pix_fmt", "yuv444p", str(out)],
            stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
        )
        time.sleep(2.5)  # let the capture settle; the footage is aligned on the first screen change
        (REC / "go").write_text("go", encoding="ascii")
        started = time.time()
        marks = REC / "marks.jsonl"
        while time.time() - started < 240:
            if proc.poll() is not None:
                print("ffmpeg stopped early; see", REC / "ffmpeg.log")
                return 1
            if not find_window(TITLE):
                print("the terminal window was closed before the session ended")
                break
            if marks.exists() and '"end"' in marks.read_text(encoding="ascii", errors="replace"):
                break
            time.sleep(0.5)
        time.sleep(1.5)
        assert proc.stdin is not None
        proc.stdin.write(b"q")
        proc.stdin.flush()
        (REC / "stop").write_text("stop", encoding="ascii")  # closing the window ends the capture
        proc.wait(timeout=60)
        print(f"recorded {out} ({out.stat().st_size / 1e6:.1f} MB, {time.time() - started:.0f} s)")
        return finish()
    finally:
        (REC / "stop").write_text("stop", encoding="ascii")


if __name__ == "__main__":
    raise SystemExit(main())
