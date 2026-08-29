# TrueVision on Linux

TrueVision records deterministic visual state and can regenerate state-derived
media. Native capture is Linux-only in this combined repository.

## Authority boundary

```text
PipeWire/Wayland live stream
-> transient BGRA memory
-> addressed cell-state measurements
-> .tvcells chunks and JSON/JSONL receipts
```

The live source frame is never written. Native capture writes no screenshot,
PNG, raw-frame file, or video. Generated media belongs only to the separate
generation/replay lane and is never source evidence.

TrueVision owns visual state capture and generation/replay. `../TrueVisionIntake`
owns DocuFilm document and glyph intake. `../TrueAudio` and `../TrueSpeech` are
independent sibling systems. TrueCore receives admitted references and receipts;
it does not embed or replace TrueVision.

## Native Linux capture

Requirements are the Linux desktop portal, a Wayland compositor portal backend,
PipeWire, GStreamer with `pipewiresrc`, and Rust. On this machine the portal is
`xdg-desktop-portal-hyprland`.

Build:

```bash
cd native/truevision_capture_rs
/home/lamercey/.cargo/bin/cargo build --release
```

Capture two seconds of cell state:

```bash
./target/release/truevision_capture_rs \
  --duration 2 \
  --fps 3 \
  --resolution 320x180 \
  --grid 32x18 \
  --cell-chunk-frames 3 \
  --output-root storage/capture_units/incoming \
  --run-id sample_capture
```

The compositor presents its native monitor chooser. After approval, the process
reads the authorized PipeWire node directly. Outputs are limited to:

```text
<run-id>_records.jsonl
<run-id>_summary.json
<run-id>_manifest.json
cell_state_native/<run-id>_cells_*.tvcells
```

## TrueFrameGen

The compiled generation binaries live in the same Rust crate. They consume
TrueVision state and produce derived output. They do not alter capture authority
or turn generated pixels into evidence.

Example:

```bash
./target/release/trueframegen_stream_rs \
  --run-dir storage/capture_units/incoming/sample_capture \
  --output-dir storage/trueframegen/sample_capture_60fps \
  --duration 10 \
  --capture-fps 10 \
  --target-fps 60 \
  --motion-mode segment-field
```

## Python tools and tests

Run the repository preflight:

```bash
python scripts/truevision_preflight.py
python scripts/truevision_preflight.py --json
```

Run repository-native tests:

```bash
python -m pytest -q tests
```

User-authored acceptance tests and all verification logs belong outside this
repository under:

```text
/home/lamercey/Documents/User System Test/repositories/linux TrueSystems/
```

## Runtime data

Capture chunks, manifests, reports, generated media, and temporary artifacts are
runtime data and stay outside Git. Use explicit Linux paths; this repository has
no Windows drive defaults, PowerShell entrypoints, Win32 capture calls, or WASAPI
capture authority.

The current system map and laws are in `docs/`, especially:

```text
docs/TRUEVISION_LOCAL_PRODUCT_MAP.md
docs/TRUEVISION_RECEIPT_AND_MANIFEST_RULES.md
docs/REPO_SYSTEM_GUIDE.md
```
