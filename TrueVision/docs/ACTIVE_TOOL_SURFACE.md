# Active TrueVision tool surface

This file lists only current Linux entrypoints.

## Capture

`native/truevision_capture_rs/target/release/truevision_capture_rs` obtains an
operator-approved monitor stream through the Wayland ScreenCast portal and
PipeWire. Frames exist transiently in memory. Its durable outputs are `.tvcells`
state, JSONL records, and JSON receipts only.

## State validation

```bash
python scripts/truevision_preflight.py
python scripts/truevision_timing_audit.py <manifest.json>
```

Frame index and FPS are timeline authority. Wall time measures performance.

## Generation and replay

TrueFrameGen binaries and Python reconstruction tools consume admitted state and
produce derived media. Their output is never capture evidence.

```bash
python scripts/trueframegen_upsample.py --help
python scripts/trueframegen_live_upsample.py --help
python scripts/trueframegen_fill.py --help
```

## Sibling boundaries

TrueAudio, TrueSpeech, and TrueVisionIntake are top-level sibling components.
Their commands must be run from their own directories. TrueVision does not carry
embedded copies or claim their authority.

Historical render experiments and research plans are reference material, not
the active capture surface.
