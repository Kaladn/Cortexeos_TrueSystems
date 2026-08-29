# TrueCore Local Media AI Stack

## Purpose

TrueCore may use local-only open-source media tools and models for forensic processing, operator support, simulation, and accessibility. These systems must never create, alter, or replace primary evidence.

Core boundary:

```text
Evidence is observed.
Generated media is derivative.
Derivative artifacts must never become primary evidence.
```

Tiny law:

```text
Originals are evidence.
Derivatives are artifacts.
Generated media is simulation.
Central Writer labels everything.
Policy controls release.
```

## Allowed Uses

Use local media models and deterministic tools for:

```text
forensic processing
transcription
diarization
metadata extraction
frame extraction
object/person/scene detection
tamper/deepfake suspicion scoring
visual/audio summaries
operator training simulations
alert narration
case reconstruction mockups
```

## Forbidden Uses

Do not use media models for:

```text
creating evidence
altering evidence
filling evidence gaps
making synthetic media look original
silently repairing evidence
promoting generated media as observed fact
```

## Recommended Local Stack

### Media Foundation

```text
FFmpeg
  decode, extract frames/audio, normalize formats, generate spectrogram inputs

ExifTool
  metadata extraction for image, video, audio, and document files

MediaInfo
  technical media stream metadata

OpenCV
  frame analysis, motion analysis, object crops, visual diffing
```

### Image Generation And Visual Simulation

```text
FLUX.1-schnell
  fast local image generation; license pinned per exact model/version

Stable Diffusion 3.5 / SDXL
  broad ecosystem lane; license checked per model

Qwen Image
  possible image/edit lane; exact model and license must be verified before adoption
```

Allowed generation uses:

```text
training visuals
UI mockups
threat scenario illustration
operator education
synthetic decoy content
```

Generation may never repair, complete, or replace evidence.

### Video Generation And Simulation

```text
Wan2.1
  open video generation family; license pinned per exact model/version

CogVideoX / HunyuanVideo
  evaluate later; license checked before adoption
```

Allowed video generation uses:

```text
training scenarios
decoy or simulation clips
incident replay mockups clearly labeled synthetic
```

Generated video must be watermarked or manifest-labeled as derivative simulation.

### Audio Processing

```text
Whisper / faster-whisper
  local transcription

pyannote.audio
  speaker diarization and speaker segmentation

Piper / Kokoro
  local text-to-speech for alert narration and accessibility readouts

Coqui XTTS / F5-TTS
  richer local voice generation; voice cloning is restricted and approval-gated
```

Allowed audio uses:

```text
transcripts
speaker timelines
audio anomaly notes
operator alert narration
accessibility readouts
```

Voice cloning must be restricted, logged, labeled, and approval-gated.

## TrueCore Media Artifact Classes

Later artifact types:

```text
media_metadata_report
frame_extraction_bundle
audio_transcript
speaker_diarization_timeline
spectrogram_artifact
visual_diff_report
tamper_suspicion_report
deepfake_suspicion_report
synthetic_training_image
synthetic_training_video
synthetic_alert_audio
media_derivative_manifest
```

## Required Artifact Metadata

Every media artifact must include:

```text
source_artifact_id
source_hash
derivative_hash
tool_name
tool_version
model_id
model_hash
prompt_hash if generated
generation_params_hash
created_at_utc
created_by
synthetic=true/false
evidence=false for generated media
```

## Pipeline

```text
media file
  -> hash + metadata
  -> frame/audio extraction
  -> local model processing
  -> derivative artifact
  -> Central Writer request
  -> Artifact Engine storage/index/sign/version
  -> report/card/output
```

## Risk Gates

Approval required for:

```text
voice cloning
face generation
video generation involving real person likeness
evidence export
media redaction overwrite
publishing generated media externally
```

## First Build Priority

Start with processing before generation:

```text
Phase 1: FFmpeg + ExifTool + MediaInfo metadata reports
Phase 2: Whisper transcription
Phase 3: pyannote diarization
Phase 4: frame extraction + OpenCV visual diff
Phase 5: local image/video/audio generation for training/decoys only
Phase 6: UI media artifact cards
```

## TrueVision Fit

This stack should plug into the TrueVision media perception lane:

```text
TrueVision sees media.
Artifact Engine preserves it.
Forge relates it.
Temporal logger orders it.
Central Writer explains it.
Policy Gate controls release.
Originals remain evidence.
Models only derive.
```

## Agent Boundary

Media agents may:

```text
read approved media sources
extract metadata
create derivative artifact requests
emit structured findings upstream
request Central Writer output
request Policy Gate approval for restricted operations
```

Media agents may not:

```text
write operator-facing reports directly
emit alerts directly
overwrite originals
mutate evidence
publish externally
run live capture without explicit approval
perform voice cloning without approval
promote synthetic media as fact
```

## Sources To Pin Before Embedding

Exact licenses and versions must be pinned before embedding:

```text
FFmpeg
ExifTool
MediaInfo
OpenCV
Whisper / faster-whisper
pyannote.audio
Piper / Kokoro
Coqui XTTS / F5-TTS
FLUX.1-schnell
Stable Diffusion 3.5 / SDXL
Qwen Image
Wan2.1
CogVideoX / HunyuanVideo
SAM 2
GroundingDINO / Grounded SAM
YOLO
CLIP / SigLIP
```
