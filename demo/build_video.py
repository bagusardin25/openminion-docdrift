"""Build the demo video from the screen recording, the scene pages and the voice-over.

    uv run --with pillow --with numpy --with imageio-ffmpeg python demo/build_video.py            # full build
    uv run --with pillow --with numpy --with imageio-ffmpeg python demo/build_video.py --stills   # screenshots only

Scenes are HTML (demo/scenes.py), rasterized with headless Edge or Chrome and
cross-faded to the narration timing. Terminal scenes have a slot that is filled,
frame by frame, with demo/screen-recording.mp4. Output: demo/out/doctwin-demo.mp4
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenes as S  # noqa: E402
from make_voice import wav_info  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "out"
HTML, PNG, AUDIO = OUT / "html", OUT / "png", OUT / "audio"
W, H, FPS = 1920, 1080, 30
LEAD, TAIL, FADE, SCENE_FADE = 0.45, 0.55, 0.28, 0.5
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def browser() -> str:
    for path in BROWSERS:
        if Path(path).exists():
            return path
    found = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")
    if not found:
        raise SystemExit("no Edge or Chrome found for rendering the scenes")
    return found


def beat_starts(pcm: bytes, rate: int, weights: list[int]) -> list[float]:
    """When each beat starts inside one scene's narration.

    The voice-over is one file per scene, so a beat's start is first estimated
    from the length of the text before it, then moved to the nearest pause in
    the audio (the gap between two sentences).
    """

    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
    win = rate // 50  # 20 ms
    n = len(samples) // win
    rms = np.sqrt((samples[: n * win].reshape(n, win) ** 2).mean(axis=1))
    quiet = rms < max(90.0, 0.035 * float(rms.max()))
    spoken = np.concatenate([[0.0], np.cumsum(~quiet) * 0.02])  # seconds of speech before each window
    pauses, i = [], 0  # (speech before the pause, time speech resumes, length of the pause)
    while i < n:
        if not quiet[i]:
            i += 1
            continue
        j = i
        while j < n and quiet[j]:
            j += 1
        if 0 < i and j < n and (j - i) * 0.02 >= 0.2:
            pauses.append((float(spoken[i]), j * 0.02, (j - i) * 0.02))
        i = j
    starts = [0.0]
    for k in range(1, len(weights)):
        # Speech time, unlike clock time, is close to proportional to the amount of text.
        guess = float(spoken[-1]) * sum(weights[:k]) / sum(weights)
        near = [p for p in pauses if abs(p[0] - guess) <= 1.0 and p[1] > starts[-1] + 0.5]
        # Prefer the closest pause, with a bonus for long ones: sentence ends pause longer than commas.
        best = min(near, key=lambda p: abs(p[0] - guess) - 1.2 * p[2], default=None)
        if best:
            starts.append(best[1] - 0.1)
        else:
            starts.append(float(np.searchsorted(spoken, guess)) * 0.02)
    return starts


def plan() -> tuple[list[dict], list[dict], float]:
    """Return (stills to render, timeline, total seconds). Timing follows the narration audio."""

    spec = json.loads((ROOT / "demo" / "narration.json").read_text(encoding="utf-8"))
    shots, timeline, t = [], [], 0.0
    for scene in spec["scenes"]:
        sid = scene["id"]
        rate, ch, bits, pcm = wav_info((AUDIO / f"{sid}.wav").read_bytes())
        assert (ch, bits) == (1, 16), (ch, bits)
        dur = len(pcm) / (rate * 2)
        beats = scene["beats"]
        bounds = [*beat_starts(pcm, rate, [len(b["say"]) for b in beats]), dur]
        start = t + LEAD
        scene_first = True
        for i, (beat, states) in enumerate(zip(beats, S.STATES[sid], strict=True)):
            b0, b1 = start + bounds[i], start + bounds[i + 1]
            items = [(s, 1) if isinstance(s, int) else s for s in states]
            share, acc = sum(w for _, w in items), 0
            for state, weight in items:
                name = f"{sid}-{state:02d}-{len(shots):03d}"
                shots.append({"name": name, "scene": sid, "state": state, "cap": beat["cap"]})
                at = t if scene_first else b0 + (b1 - b0) * acc / share
                acc += weight
                timeline.append({"t": at, "png": name, "scene": sid, "state": state,
                                 "fade": SCENE_FADE if scene_first else FADE})
                scene_first = False
        timeline.append({"audio": sid, "at": start})
        t = start + dur + TAIL
    total = t + 1.2

    # Hand each terminal state its stretch of the screen recording.
    cues = [c for c in timeline if "png" in c]
    for i, cue in enumerate(cues):
        cue["end"] = cues[i + 1]["t"] if i + 1 < len(cues) else total
    by_state = {(c["scene"], c["state"]): c for c in cues}
    for sid, states, (mark_a, off_a), (mark_b, off_b) in S.CLIPS:
        run = [by_state[(sid, s)] for s in states]
        a = S.V[mark_a] + off_a
        b = min(S.V[mark_b] + off_b, S.MARKS["duration"] - 0.1)
        shown = run[-1]["end"] - run[0]["t"]
        speed = max(1.0, (b - a) / shown)
        for cue in run:
            cue["clip"] = (a + (cue["t"] - run[0]["t"]) * speed, min(b, a + (cue["end"] - run[0]["t"]) * speed), speed)
            S.SPEED[(sid, cue["state"])] = speed
    return shots, timeline, total


def render_stills(shots: list[dict]) -> None:
    HTML.mkdir(parents=True, exist_ok=True)
    PNG.mkdir(parents=True, exist_ok=True)
    for old in [*HTML.glob("*.html"), *PNG.glob("*.png")]:
        old.unlink()
    exe = browser()
    for shot in shots:
        label, body, zoom = S.SCENES[shot["scene"]](shot["state"])
        (HTML / f"{shot['name']}.html").write_text(S.page(label, body, shot["cap"], zoom), encoding="utf-8")

    def shoot(job: tuple[int, dict]) -> str:
        worker, shot = job
        profile = Path(tempfile.gettempdir()) / f"doctwin-video-profile-{worker % 4}"
        png = PNG / f"{shot['name']}.png"
        subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--user-data-dir={profile}", f"--window-size={W},{H}", "--virtual-time-budget=1500",
             f"--screenshot={png}", (HTML / f"{shot['name']}.html").as_uri()],
            capture_output=True, timeout=120, check=False,
        )
        return shot["name"] if png.exists() else f"FAILED {shot['name']}"

    # One browser per profile at a time: run 4 lanes, each lane sequential.
    lanes = [[(lane, s) for i, s in enumerate(shots) if i % 4 == lane] for lane in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda lane: [shoot(j) for j in lane], lanes))
    failed = [r for lane in results for r in lane if r.startswith("FAILED")]
    print(f"rendered {len(shots) - len(failed)}/{len(shots)} stills" + (f"; failed: {failed}" if failed else ""))


def build_audio(timeline: list[dict], total: float) -> Path:
    rate = 24000
    track = bytearray(int(total * rate) * 2)
    for item in timeline:
        if "audio" not in item:
            continue
        r, ch, bits, pcm = wav_info((AUDIO / f"{item['audio']}.wav").read_bytes())
        assert (r, ch, bits) == (rate, 1, 16), (r, ch, bits)
        pos = int(item["at"] * rate) * 2
        track[pos:pos + len(pcm)] = pcm
    path = OUT / "voice.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(track[: int(total * rate) * 2]))
    return path


class Footage:
    """One stretch of the screen recording, decoded in step with the output frames."""

    MAGENTA = np.array([255.0, 0.0, 255.0], dtype=np.float32)

    def __init__(self, ffmpeg: str, still: np.ndarray, clip: tuple[float, float, float]) -> None:
        # The slot is the magenta rectangle in the still; alpha is 1 inside it and fades on its rounded corners.
        r, g, b = (still[..., i].astype(np.float32) for i in range(3))
        alpha = np.clip((np.minimum(r, b) - g) / 255.0, 0.0, 1.0)
        ys, xs = np.where(alpha > 0.5)
        if len(ys) == 0:
            raise SystemExit("a terminal scene has no slot for the screen recording")
        self.y0, self.y1, self.x0, self.x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        h, w = self.y1 - self.y0, self.x1 - self.x0
        if w > S.CLIP_W or h > S.CLIP_H:
            raise SystemExit(f"slot {w}x{h} is larger than the recording {S.CLIP_W}x{S.CLIP_H}")
        self.alpha = alpha[self.y0:self.y1, self.x0:self.x1, None]
        self.base = still[self.y0:self.y1, self.x0:self.x1].astype(np.float32) - self.alpha * self.MAGENTA
        a, b_, speed = clip
        self.shape, self.last = (h, w, 3), np.zeros((h, w, 3), dtype=np.float32)
        self.proc = subprocess.Popen(
            [ffmpeg, "-loglevel", "error", "-ss", f"{a:.3f}", "-t", f"{max(0.1, b_ - a):.3f}", "-i", str(S.RECORDING),
             "-vf", f"setpts=(PTS-STARTPTS)/{speed:.5f},fps={FPS},crop={w}:{h}:0:0",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE,
        )

    def paint(self, frame: np.ndarray) -> None:
        assert self.proc.stdout is not None
        size = self.shape[0] * self.shape[1] * 3
        buf = self.proc.stdout.read(size)
        if len(buf) == size:  # at the end of the stretch the last frame stays on screen
            self.last = np.frombuffer(buf, dtype=np.uint8).reshape(self.shape).astype(np.float32)
        region = self.base + self.alpha * self.last
        frame[self.y0:self.y1, self.x0:self.x1] = np.clip(region, 0, 255).astype(np.uint8)

    def close(self) -> None:
        self.proc.kill()


def encode(timeline: list[dict], total: float, audio: Path) -> Path:
    import imageio_ffmpeg
    from PIL import Image

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cues = [c for c in timeline if "png" in c]

    def load(name: str) -> np.ndarray:
        im = Image.open(PNG / f"{name}.png").convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        return np.asarray(im, dtype=np.uint8).copy()

    out = OUT / "doctwin-demo.mp4"
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    frames = int(total * FPS)
    accent = np.array([31, 63, 208], dtype=np.uint8)
    track = np.array([222, 216, 202], dtype=np.uint8)
    paper = np.array([244, 240, 230], dtype=np.float32)  # the page background; the video fades from and to it
    k = -1
    still = shown = previous = None
    footage: Footage | None = None
    for f in range(frames):
        t = f / FPS
        while k + 1 < len(cues) and cues[k + 1]["t"] <= t:
            k += 1
            previous = shown  # the last picture of the state we are leaving
            still = load(cues[k]["png"])
            if footage:
                footage.close()
            footage = Footage(ffmpeg, still, cues[k]["clip"]) if "clip" in cues[k] else None
        assert still is not None
        shown = still.copy()
        if footage:
            footage.paint(shown)
        frame = shown
        since, fade = t - cues[k]["t"], cues[k]["fade"]
        if previous is not None and since < fade:
            a = since / fade
            a = a * a * (3 - 2 * a)  # smoothstep
            frame = (previous.astype(np.float32) * (1 - a) + shown.astype(np.float32) * a).astype(np.uint8)
        if t < 0.5:  # fade in
            frame = (paper + (frame.astype(np.float32) - paper) * (t / 0.5)).astype(np.uint8)
        if total - t < 0.8:  # fade out
            frame = (paper + (frame.astype(np.float32) - paper) * max(0.0, (total - t) / 0.8)).astype(np.uint8)
        if frame is shown:
            frame = shown.copy()
        x = int(W * t / total)
        frame[H - 6:, :x] = accent
        frame[H - 6:, x:] = track
        proc.stdin.write(frame.tobytes())
        if f % (FPS * 20) == 0:
            print(f"  encoded {t:5.0f}s / {total:.0f}s", flush=True)
    if footage:
        footage.close()
    proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg failed with exit code {code}")
    return out


def main() -> int:
    shots, timeline, total = plan()
    print(f"{len(shots)} stills, {total:.1f}s ({int(total // 60)}:{int(total % 60):02d})")
    for cue in timeline:
        if "clip" in cue:
            a, b, speed = cue["clip"]
            print(f"  {cue['scene']} state {cue['state']}: recording {a:6.1f}-{b:6.1f}s shown for "
                  f"{cue['end'] - cue['t']:4.1f}s at {speed:.1f}x")
    if "--no-stills" not in sys.argv:
        render_stills(shots)
    if "--stills" in sys.argv:
        return 0
    audio = build_audio(timeline, total)
    out = encode(timeline, total, audio)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
