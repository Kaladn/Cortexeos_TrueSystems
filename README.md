# Linux TrueSystems

Start with [`OPERATORS_MANUAL.md`](OPERATORS_MANUAL.md). Agent and capability
callers must also obey [`AGENTS.md`](AGENTS.md). Documentation claims excluded
from current truth are recorded in
[`SUSPECT_DOCUMENTATION.md`](SUSPECT_DOCUMENTATION.md).

For data-first studies in which the operator agent profiles supplied data,
chooses and discloses technical settings, and then answers the human's questions,
use the [parameterized evidence-study contract](docs/PARAMETERIZED_EVIDENCE_STUDY_CONTRACT.md).

Local Linux source workspace for the cooperating TrueSystems components.

## Components

- `TrueCore/` — coded security agents and bounded capabilities.
- `TrueMachine/` — the Linux temporal cognition machine formerly discussed as CompuCog.
- `TrueVision/` — canonical TrueVision visual-state capture and generation/replay integration.
- `TrueAudio/` — deterministic audio-state logging and replay.
- `TrueSpeech/` — deterministic speech-region detection and caller-supplied lyric-candidate alignment.
- `TrueVisionIntake/` — authoritative DocuFilm document/glyph intake and TrueMem handoff.
- `TrueMem/` — dataset-native anchor mapping, relationship prediction, retrieval, and citations behind DocuFilm.
- `LocalMemoryChat/` — the small local chat-continuation and cited-memory system.
- `clearbox-chat-chain/` — the local chat-chain service and plugin source.
- `control-api/` — a thin localhost API that delegates to the existing systems.

Each component remains a distinct source boundary inside this umbrella repository.
Linux-specific dependencies and global sibling imports were changed in place;
the system authority boundaries were not merged or replaced.

The current verification state, including unresolved failures, is recorded in
[`docs/LINUX_PORT_STATUS.md`](docs/LINUX_PORT_STATUS.md).

## Assembly boundary

This repository contains current source working trees. It intentionally excludes:

- nested `.git` directories;
- runtime, state, and machine-local data;
- Python bytecode and test caches;
- external test logs and generated test artifacts.

The original canonical working directories remain unchanged. `SOURCES.md` records
their locations and the directory mapping used for this assembly.

## Human control surface

The retained Omarchy bar widget points to the unified local API on
`127.0.0.1:3220`. The API delegates to existing component code; it does not own
their business logic. The existing chat-chain service and database remain the
durable conversation boundary.
