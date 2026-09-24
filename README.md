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
- `TrueComputer/` — bounded Hyprland/Wayland desktop actions with live
  preconditions and redacted receipts.
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

## Cortexeos umbrella contract

© 2026 Lee Mercey. All Rights Reserved.
**Cortexeos™ — Umbrella Architecture**
TrueSystems • AnchorWorks • SecureCore • CompuCog
Proprietary and confidential. Not open source. No copying, modification,
redistribution, derivative works, reverse engineering, or reuse without express
written permission from Lee Mercey.

This repository is the assembled TrueSystems alignment workspace. It is a set
of separate source boundaries governed by explicit contracts, not a monolithic
application and not an authority-free collection of scripts.

### Ownership law

- **SecureCore** owns coded workers, capability gates, approvals, registration,
  permission decisions, and receipts.
- **AnchorWorks** owns exact recognition, evidence retrieval, relationship
  navigation, ownership qualification, and work archaeology.
- **TrueMem / Anchor Index** owns dataset-local anchors, occurrences, signed
  6-1-6 relationships, structural records, parent bindings, locations, and
  citations.
- **TrueVision** owns observed/renderable visual state, capture, replay,
  generation, and state profiles.
- **TrueAudio / TrueSpeech** own deterministic audio state and bounded speech
  detection/alignment.
- **CompuCog** (legacy `TrueMachine` paths) owns temporal machine, activity,
  and its machine I/O observations; these observations do not grant authority.
- **TrueComputer** owns bounded host actions and postcondition checks; its
  component CLI is not arbitrary shell access or a system-level grant.
- **LocalMemoryChat** owns cited local-memory packets and daily chat history;
  it is not general truth authority.
- The **operator model** decomposes questions, requests capabilities, reasons
  over returned evidence, and communicates. It does not own tools, grants,
  roots, executable paths, or raw stores.

### Live admission spine

The intended always-on path is a bounded admission spine, not a new intelligence
layer or a second memory system:

```text
user/model/tool/file/commit/test/receipt event
→ SecureCore admission
→ AnchorWorks recognition and append
→ TrueMem / Anchor Index records
→ deterministic relationship rebuild and reconciliation
```

New derived records are append-only. Accepted source evidence is read-only.
Every event must preserve exact text or bytes, dataset/session/project identity,
coordinates, timestamp, source hash, relation direction, and receipt. No
co-occurrence may silently become ownership or semantic meaning.

### Relationship law

```text
recognition
→ commonality/frequency
→ signed positional neighborhood (6-1-6)
→ structural relation
→ ownership
→ parent/reference identity transfer
→ proof drill-down
→ operator reasoning
```

Frequency is commonality, not significance. Similarity is not proof.
Co-occurrence is not ownership. Temporal adjacency is not causality. Inferred
bridges never silently become direct evidence. Projection never becomes
observed truth.

### Provenance and storage

Raw source remains immutable. Derived structures live beside it:

```text
dataset/
├── source/       exact admitted material
├── anchors/      exact surfaces and counts
├── occurrences/  coordinates and provenance
├── relations/    signed, structural, and reference records
├── evidence/     bounded packets and citations
├── receipts/     hashes, manifests, and run records
└── projections/  temporary graphs, reports, and HTML views
```

Graphs are deterministic temporary projections. A viewer presents records; it
does not become an authority layer.

### SecureCore worker law

Every production worker declares its identity, runtime, coded entrypoint,
entrypoint hash, typed input/output, allowed reads/writes, risk, approval,
mutation class, timeout/budget, test command, and receipt stream. Directory
presence does not activate a worker. Prompt-only production workers are
forbidden. Recipes describe capabilities; they never contain executable
commands or hidden authority.

### TrueVision law

```text
record state
→ plan state
→ transform state
→ render pixels last
→ prove every run
```

Native/compiled lanes own sustained capture and heavy frame work. Python may
orchestrate, validate, and write manifests/receipts. Generated media is a
synthetic output, not evidence.

### Verification vocabulary

Use these states literally:

```text
EXISTS              implementation located
REGISTERED          owning registry exposes it
CALLABLE            real invocation boundary exists
TESTED              invocation exercised
ACCEPTANCE-VERIFIED exact external acceptance path passed
UNRESOLVED          inspection was insufficient
NOT_IMPLEMENTED     no real callable exists
INCOMPATIBLE        callable violates the required contract
```

Documentation cannot promote one state into another. A manifest does not prove
an entrypoint works; a passing test proves only the exercised path.

### Safety and development rules

Before changing anything, read `AGENTS.md` and the owning component contract;
inspect the exact implementation and Git state; create an external acceptance
test; preserve raw data; make the smallest additive change; run the actual
user-facing path; record hashes, receipts, limitations, and rollback data; and
commit only relevant source or documentation.

Do not add a daemon, database, model host, bridge, or UI merely because a
lower-level seam is inconvenient. Locate the existing contract first and
record whether it is available, registered, callable, tested, and verified.

### Ownership and license

© 2026 Lee Mercey. All Rights Reserved. Cortexeos™ and the TrueSystems
subsystem names, methods, architecture, documentation, and code are
proprietary. No reuse, modification, redistribution, derivative work, reverse
engineering, or incorporation into another system is permitted without express
written authorization from Lee Mercey.
