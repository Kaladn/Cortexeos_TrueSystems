# TrueSpeech agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root `AGENTS.md`, then narrower instructions under
`truespeech_runtime/` or `scripts/`. TrueSpeech consumes replayable audio state
for bounded speech timing and candidate lyric alignment.

## Production entrypoints and allowed operations

`scripts/truespeech_detect_segments.py:main` calls
`truespeech_runtime.speech.detect_speech_segments_from_replayable_state`.
`scripts/truespeech_align_lyrics_candidate.py:main` calls
`truespeech_runtime.lyrics.align_lyrics_to_speech_segments`. Inspect their
argument parsers, call sites, and returned artifacts before use.

## Forbidden operations and authority boundary

The detector does not invent a transcript. Alignment uses caller-supplied lyric
candidates; it is not automatic speech recognition or proof of exact words.
Direct scripts are component mechanics, not a system authorization grant.

## Inputs, outputs, receipts, and provenance

Preserve replayable-state identity, segment timing, supplied lyric text,
candidate status, manifests, and receipts. Check the actual output files and
reported status; do not upgrade candidate timing to observed speech content.

## Known staged paths and next contract

Read the runtime source and observed output for the selected function. Treat
any wider transcription claim as unverified unless the real operation supports it.
