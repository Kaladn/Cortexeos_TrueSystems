# TrueVision local product map

```text
Linux Wayland/PipeWire state capture -> TrueVision state artifacts
TrueVision state artifacts          -> generation/replay proof lane
DocuFilm documents and glyphs       -> ../TrueVisionIntake -> ../TrueMem
Linux audio state                    -> ../TrueAudio
speech timing state                  -> ../TrueSpeech
machine temporal Fusion Packs        -> ../TrueMachine
coded security agents and tools      -> ../TrueCore
```

TrueVision answers: “What was the visual state shape at this moment?” It does
not interpret language, own machine-wide logging, embed TrueCore, or treat raw or
generated pixels as evidence.

## Repository law

Code stays in the repository. Runtime state, manifests, receipts, previews, and
generated media stay in explicit Linux runtime paths outside Git.

## Active layout

```text
native/truevision_capture_rs/  Linux capture and compiled generation paths
truevision_runtime/            state, storage, AV contracts, and receipts
trueframegen/                  temporal reconstruction
scripts/                       command entrypoints
tests/                         repository-native tests
storage/                       ignored local runtime placeholder
```

Run preflight from the TrueVision root:

```bash
python scripts/truevision_preflight.py
python scripts/truevision_preflight.py --json
```

Preflight reports prerequisites and repository health. It does not install
packages, open browsers, or mutate system security state.
