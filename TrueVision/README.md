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

### One-command state logging on this machine

Run `truevision-record` from a desktop terminal and select the full monitor in
the portal chooser. Ctrl+C requests a native stop, flushes the partial state
chunk, and then hashes saved artifacts. Leave the terminal open until it exits.
Planned default output: `/mnt/truevision/TrueVision-Logs/<UTC timestamp>`.
The dedicated NVMe mount is not provisioned yet: default recording fails closed
until recovery verification and administrator-approved disk setup are complete.
It never falls back to the 5TB backup. Each run has a unique timestamp folder.
Ctrl+C, SIGTERM and terminal SIGHUP request a flush; a stopped run receives a
SHA-256 ledger and `SEALED.json` (failed native runs are `SEALED_FAILED`).
Forced kills, power loss, or storage failure can leave an unsealed directory.
Sealing is an integrity inventory, not proof of complete or sharp observation.
Existing data is never deleted. The command refuses a missing mount or the
system filesystem. It stops at 50 GiB free; it does not recycle old logs.
`truevision-record --check` reports readiness without observing the desktop.

The CLI explicitly uses 2560x1440, 640x360 cells, 9 FPS, and nine-frame chunks.
This restores the historical clarity-test configuration, not pixel-exact video.
Nominal uncompressed cell payload is 132,710,400 bytes/second, about 478 GB/hour.
Continuous multi-day retention is not qualified and will hit the disk guard.
No audio or semantic object-recognition pass is enabled by this command.
The native binary is built externally; the Python entrypoint is
`scripts/truevision_record.py`. Its `--binary` option can select a rebuilt binary.
CLI checks and native partial-chunk tests pass; this specific high-grid CLI
still needs a live monitor/stop qualification. Earlier 160x90 live success does
not qualify its higher storage load or clarity.

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

## Read-only visual identity experiment

### Live buffer ownership and failure handling

The native PipeWire source requests eight buffers and `always-copy=true`;
the application sink disables last-sample retention and keeps at most one
queued sample. On the installed PipeWire/GStreamer combination this gives
downstream processing owned memory rather than retaining the producer's scarce
buffers. This is a deliberate copy boundary, not a GPU extraction path.
`always-copy` is an exposed but deprecated plugin property, so its availability
must be checked when changing runtime versions.

If the observation loop returns an error, completed state still in the current
chunk is flushed, frame records are flushed, and `failure.json` reports
`OPERATION_FAILED` with `completed=false`. A failed run does not publish a success
manifest. This is graceful error handling, not a guarantee against power loss,
forced termination, or storage failure.

External native tests are under
`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/native_capture_contract`.
Live checks use the external `benchmark_native_state.py`; binary chunk/frame
accounting is independently checked by `analyze_native_observation.py`.

`scripts/truevision_visual_identity_intake.py` reads an already captured native
manifest, frame records, and `.tvcells` chunk. It does not capture, replay,
render, recognize, or train anything.

Each visual unit is only an existing cell-state address:

```text
artifact hash + frame order + timestamp + grid/pixel coordinates
+ exact native state bytes
```

Exact state bytes at the same coordinate in consecutive frames support
`persists_to` and `stable_identity`. Different bytes at the same coordinate
support only `changes_to` and `candidate_continuity`. Repeated state bytes at
multiple locations remain ambiguous. Object names, classes, meanings, and
appearance-derived identities are forbidden.

```bash
python scripts/truevision_visual_identity_intake.py \
  --experiment-manifest /path/to/experiment-manifest.json \
  --output-root /path/to/output \
  --workers 24
```

## Language-to-visual-identity bridges

`scripts/truevision_language_visual_identity_bridges.py` binds exact natural-
language phrases to units or relationships already present in a frozen visual-
identity release. It verifies the frozen manifest and accepted-ledger hashes,
returns a target only for a unique explicit binding, and preserves native
coordinates, timestamps, citations, and relationship IDs. Ambiguity is
quarantined. Missing, stale, invalid, and appearance-semantic requests are
rejected. It creates no visual relationship and executes no TrueVision action.

```bash
python scripts/truevision_language_visual_identity_bridges.py \
  --source-manifest /path/to/bridge-source-manifest.json \
  --output-root /path/to/output \
  --workers 24
```

`scripts/evaluate_visual_identity_bridges.py` resolves phrases against that
frozen bridge release without running TrueVision. It uses explicit frame/grid
coordinates, relation terms, timestamps, citations, and already-stored paths.
It returns a target only for unique evidence; ambiguity, missing or stale
authority, invalid coordinates, negation, and appearance meanings remain
non-target outcomes. Acceptance cases are explicitly separate from sealed
future model-evaluation reservations.

```bash
python scripts/evaluate_visual_identity_bridges.py \
  --bridge-release /path/to/frozen/visual-bridge-release \
  --cases /path/to/prerequisite-acceptance-cases.jsonl \
  --output-root /path/to/output \
  --workers 24
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
