# TrueAudio

TrueAudio is the top-level audio-state system. It records deterministic
pre-output and replayable audio-state artifacts, hashes them, and replays those
artifacts. It does not own speech interpretation and it does not store raw media
as source truth.

Run its native tests from this directory with:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Machine capture reads the current default Linux output sink through the
PipeWire/Pulse `@DEFAULT_MONITOR@` endpoint. File-based state extraction and
deterministic replay use NumPy and FFmpeg.
