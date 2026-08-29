# TrueSpeech

TrueSpeech is the top-level speech-state system. It consumes replayable
TrueAudio state, deterministically detects candidate speech segments, and can
align caller-supplied lyric candidates. It does not transcribe, infer lyrics,
or own audio capture.

Run its native tests from this directory with both sibling runtimes visible:

```bash
PYTHONPATH=.:../TrueAudio python -m unittest discover -s tests -v
```
