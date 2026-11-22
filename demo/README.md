# Demo video

- The demo video is on YouTube: <https://youtu.be/YquM4dqjr7M> (3:22, 1080p, with voice-over). The file is
  not kept in the repo; `build_video.py` rebuilds it.
- [`screen-recording.mp4`](screen-recording.mp4) is the terminal session it is
  cut from: 2:25, real time, uncut.
- [`thumbnail.png`](thumbnail.png) is the YouTube thumbnail, made by `make_thumbnail.py`.
- [`preview.png`](preview.png) is a screenshot of one section of `translations/id/.doctwin/preview.html`,
  shown in the main README.

## What is real in it

- **The terminal scenes are a screen recording** of one real session on
  `gpt-4.1-mini`. [`session.ps1`](session.ps1) types each command at the
  PowerShell prompt and runs it; [`record_screen.py`](record_screen.py) records
  that one window. In the demo, waiting is fast-forwarded (the speed is shown in
  the corner) and the steps are cut together. Nothing else is edited: the
  commands and their output are exactly as they ran.
- **The numbers next to the recording** come from that same run:
  [`logs/marks.json`](logs/marks.json) and DocTwin's own report,
  [`logs/sync-report.md`](logs/sync-report.md).
- **The row the gates refused** (the model changed `33.76` to `33,76`) is taken
  from the first full sync's report:
  `translations/id/.doctwin/reports/20261119-144226/report.json`.
- **The pull request image** is a screenshot of
  <https://github.com/openminion/openminion/pull/810>.
- **The voice-over** is AI-generated with OpenAI text-to-speech from
  [`narration.json`](narration.json).

One thing the recording does not show on screen: the first translation attempt
of that sync came back as OpenMinion's canned "could not safely update the task
conditions" reply. DocTwin recognised it and tried again, and the second attempt
passed the gates and the reviewer. The report shows that 2 of 3 model turns
succeeded.

The video was recorded before our first complete sync on Cortensor Portal, so
its Portal part is out of date. The main README has the current state.

## Rebuild it

Needs Windows 11 with Windows Terminal, and Edge or Chrome.

```bash
uv run python scripts/make_demo_source.py                         # v0.1.23 docs with one sentence changed
uv run --with imageio-ffmpeg python demo/record_screen.py         # records the session, about US$0.02
uv run python demo/make_voice.py                                  # voice-over, about US$0.05; skipped if unchanged
uv run --with pillow --with numpy --with imageio-ffmpeg python demo/build_video.py
```

`build_video.py` renders each scene from `scenes.py`, plays the matching stretch
of the screen recording inside the terminal scenes, cross-fades everything to
the narration timing, and writes `demo/out/doctwin-demo.mp4`. A new recording
will have different timings, so update the "32 seconds" in `narration.json` to
match.
