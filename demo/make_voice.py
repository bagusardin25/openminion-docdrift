"""Generate the voice-over, one WAV per scene, with OpenAI text-to-speech.

Reads demo/narration.json and OPENAI_API_KEY from .env. A scene whose WAV already
exists with the same text is skipped, so re-running costs nothing.

    uv run python demo/make_voice.py
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import urllib.request
from pathlib import Path

from docdrift.cli import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "demo" / "out" / "audio"


def wav_info(data: bytes) -> tuple[int, int, int, bytes]:
    """Return (sample_rate, channels, bits, pcm). Tolerates streamed headers with bogus sizes."""

    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE", "not a WAV file"
    pos, rate, channels, bits = 12, 24000, 1, 16
    while pos + 8 <= len(data):
        tag, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = pos + 8
        if tag == b"fmt ":
            _fmt, channels, rate, _br, _ba, bits = struct.unpack("<HHIIHH", data[body:body + 16])
        if tag == b"data":
            end = len(data) if size in (0, 0xFFFFFFFF) or body + size > len(data) else body + size
            return rate, channels, bits, data[body:end]
        pos = body + size + (size & 1)
    raise ValueError("no data chunk")


def main() -> int:
    load_dotenv()
    spec = json.loads((ROOT / "demo" / "narration.json").read_text(encoding="utf-8"))
    voice = spec["voice"]
    AUDIO.mkdir(parents=True, exist_ok=True)
    total_chars, total_seconds, new_chars = 0, 0.0, 0
    for scene in spec["scenes"]:
        text = " ".join(b["say"] for b in scene["beats"])
        digest = hashlib.sha1(json.dumps([voice, text]).encode()).hexdigest()[:10]
        wav = AUDIO / f"{scene['id']}.wav"
        mark = AUDIO / f"{scene['id']}.sha"
        if not (wav.exists() and mark.exists() and mark.read_text() == digest):
            body = json.dumps({
                "model": voice["model"], "voice": voice["voice"], "input": text,
                "instructions": voice["instructions"], "response_format": "wav",
            }).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/audio/speech", data=body, method="POST",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                wav.write_bytes(r.read())
            mark.write_text(digest)
            new_chars += len(text)
        rate, channels, bits, pcm = wav_info(wav.read_bytes())
        seconds = len(pcm) / (rate * channels * bits // 8)
        total_chars += len(text)
        total_seconds += seconds
        print(f"{scene['id']:16} {len(text):4} chars  {seconds:5.1f}s  {rate} Hz")
    print(f"total: {total_chars} chars, {total_seconds:.1f}s of speech; newly generated: {new_chars} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
