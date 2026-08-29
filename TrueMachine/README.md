# TrueMachine

TrueMachine is a Linux-native temporal cognition core. It observes the local
machine, assigns every observation one authoritative time sample, commits each
pulse to a write-ahead log, and publishes an atomic Fusion Pack describing
what the machine knows about itself at that moment.

TrueMachine is the Linux CompuCog cognition layer. TrueCore comes after it as
a consumer of its evidence; TrueCore is not part of this repository.

It has no third-party runtime dependencies and performs no screen, image,
video, key-content, or pointer-coordinate capture.

Run for one minute:

```bash
PYTHONPATH=src python -m truemachine run --duration 60 --interval 1 --state-dir state
```

Admit sibling state artifacts into the same Fusion Packs with repeatable
`--truevision-state`, `--trueaudio-state`, `--truemem-state`, and
`--truemem-state` arguments. Each JSON/JSONL artifact must declare its own
`schema` or `schema_version`; TrueMachine will not invent one.

Validate a generated state directory:

```bash
PYTHONPATH=src python -m truemachine verify --state-dir state
```

See `docs/CONTRACT.md` for the locked timestamp and durability contracts.
