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

Observe a Git repository as exact source plus witnessed structural relationships:

```bash
PYTHONPATH=src python -m truemachine map-repository \
  --repo /absolute/path/to/repository \
  --output-parent /absolute/path/to/maps
```

Query a completed map for a location-only `ownership-source_order-dependency`
neighborhood:

```bash
PYTHONPATH=src python -m truemachine query-repository \
  --map-dir /absolute/path/to/maps/repository-map-YYYYMMDDTHHMMSSZ \
  --exact exact.qualified.name
```

Verify all emitted artifacts, current source hashes and modes, code-object
spans, and relationship endpoints:

```bash
PYTHONPATH=src python -m truemachine verify-repository-map \
  --map-dir /absolute/path/to/maps/repository-map-YYYYMMDDTHHMMSSZ
```

The current mapper does not claim control flow or semantic data flow. Its
middle axis is witnessed source order; exact name accesses are retained as
evidence rather than promoted to data-flow authority. It returns no answer or
security judgment.

See `docs/CONTRACT.md` for the locked timestamp and durability contracts.

Bounded filesystem observation is available to registered TrueCore workers via
`truemachine.navigation`. It is a Python API rather than an unrestricted shell
or standalone path-taking CLI: the host binds the root and budgets, and the
request supplies relative paths only. The accepted operations are `fs.list`,
`fs.find`, `fs.read_metadata`, `fs.hash`, `fs.disk_usage`, and
`fs.duplicate_scan`.
