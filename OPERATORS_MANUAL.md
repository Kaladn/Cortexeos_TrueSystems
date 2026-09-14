# Linux TrueSystems operator manual

This is the canonical operating map for a small deterministic capability model
and for human or model callers. It teaches selection and handoff, not prose
generation. The model chooses a real operation, supplies its exact inputs, and
returns the operation's result and citations to the calling model.

The operator-model learning boundary is defined in
`docs/OPERATOR_MODEL_TRAINING_CONTRACT.md`. TrueMem map training and operator
model training are separate processes. The operator may call, inspect, verify,
continue, and explain; it never becomes evidence, memory, relationship, or
action authority.

The live operator and evidence-handoff roles are fixed by
`docs/CODEX_TRUESYSTEMS_OPERATOR_HANDOFF_CONTRACT.md`: the calling LLM preserves
and rearranges the human request into a bounded work order, TrueSystems returns
deterministic evidence and operation receipts, and the calling LLM reasons and
communicates from that handoff. TrueSystems does not compose the final answer.

Data-first, user-directed investigations additionally follow
`docs/PARAMETERIZED_EVIDENCE_STUDY_CONTRACT.md`. The operator requests or locates
data, profiles and shapes it, tells the human what it can support, asks what the
human wishes to know, sets and discloses technical parameters, then freezes the
plan before computation. The deterministic freeze tool is
`TrueCore/truecore/agents/parameterized_study.py`; it validates the plan but does
not perform the operator's reasoning or analysis.

## Whole-system map

### Method supersession — September 8, 2026

Conventional gradient-based model training is paused by owner direction.
The 3.322B run remains an unpromoted historical experiment. Current development
targets observed state, provenance, deterministic counts/weights/relationships,
and measured GPU execution of those structures. This instruction does not
claim deterministic language or visual construction is already qualified.

DocuFilm's stored-state pause/child/return implementation and its exact limits
are documented in `TrueVisionIntake/docs/INTAKE_CONTROL.md`. This adds no model
tool route and does not replace TrueCore authorization.

```text
Linux/native state artifacts -> TrueMachine -> verified Fusion Packs
operator-selected desktop action -> TrueComputer -> redacted action receipt
documents/glyph state -> TrueVision Intake/DocuFilm -> TrueMem map -> cited retrieval/prediction packets
decoded or machine audio -> TrueAudio state -> TrueSpeech bounded speech-state candidates
local files/chats -> LocalMemoryChat -> cited memory packets
Fusion/evidence packets -> TrueCore -> coded decisions and bounded tools
conversation turns -> Clearbox Chat-Chain -> durable ordered conversation
caller -> control-api -> existing component callable -> result/receipt
```

These arrows describe intended handoffs. Only the control API routes listed
below are currently wired across component boundaries. File artifacts may be
passed explicitly where a component exposes a path argument.

## Selection table

| Need | System | Real entrypoint | Authoritative result |
| --- | --- | --- | --- |
| Observe Linux machine state over time | TrueMachine | `python -m truemachine run` | Fusion Pack plus WAL/index state |
| Inspect or perform one bounded Linux desktop action | TrueComputer | `truecomputer inspect|validate|execute` | live Hyprland state or atomic redacted action receipt |
| Verify a TrueMachine state directory | TrueMachine | `python -m truemachine verify` | JSON verification result |
| Read document/glyph state | TrueVision Intake / DocuFilm | `truevision_intake.document_state` | document read plus stable glyph-state records |
| Admit a document and build its deterministic map | TrueVision Intake / DocuFilm + TrueMem | `python -m truemem.cli docufilm-intake` | parent/contained anchors, a dataset-scoped range from the active workspace symbolizer, counts, coordinates, relationships, citations |
| Record or replay derived audio state | TrueAudio | `TrueAudio/scripts/trueaudio_*.py` | audio-state artifacts, manifests, and receipts |
| Detect bounded speech regions | TrueSpeech | `TrueSpeech/scripts/truespeech_detect_segments.py` | speech/background candidates without transcript claims |
| Retrieve a cited evidence packet | TrueMem | `python -m truemem.cli query` | exact occurrence/cloud packet for a structured `EvidenceNeed`; `model_used` is `none` |
| Inspect a legacy prediction walk diagnostically | TrueMem | `python -m truemem.cli deeper-wider` | separate diagnostic packet; not part of EvidenceNeed retrieval |
| Search local remembered material | LocalMemoryChat | `python -m local_memory_chat.cli ask` | cited memory packet and receipt |
| Retain/continue ordered conversation | Clearbox Chat-Chain | local HTTP server | persisted conversation/turn result |
| Observe or invoke a coded security agent | TrueCore | `python -m truecore.cli.main agents ...` | agent state/decision/receipt |
| Validate/freeze a parameterized evidence study | TrueCore | `python -m truecore.agents.parameterized_study` | canonical locked plan and deterministic freeze hash |
| Call the currently unified subset | control-api | localhost HTTP | delegated component result |

Run module commands from the named component directory with its `src` (or repo
root for TrueCore) on `PYTHONPATH`. No installation is implied by this manual.

## TrueMachine

One-minute Linux run:

```bash
cd TrueMachine
PYTHONPATH=src python -m truemachine run --duration 60 --interval 1 --state-dir state
PYTHONPATH=src python -m truemachine verify --state-dir state
```

Optional repeatable inputs are `--truevision-state`, `--trueaudio-state`,
and `--truemem-state`. Each input must be JSON or JSONL and must
declare `schema` or `schema_version`. TrueMachine samples time once per pulse,
appends the pulse to its WAL, then atomically publishes the current Fusion Pack.
The exact timestamp and durability rules are in `TrueMachine/docs/CONTRACT.md`.

## TrueComputer

TrueComputer is the bounded Wayland/Hyprland desktop actuator. It observes live
Hyprland JSON state, validates one action against an exact active-window
precondition, delegates to Hyprland IPC or `wtype`, checks a backend-specific
postcondition, and atomically writes a redacted receipt. Execution status and
verification status are separate. A receipt may explicitly say
`executed_but_outcome_unverified`; receipt creation never proves application
success. TrueComputer is not a shell, planner, screen-understanding system, or
source of human authorization.

```bash
cd TrueComputer
CARGO_TARGET_DIR=/tmp/truecomputer-target cargo build --release
/tmp/truecomputer-target/release/truecomputer inspect
/tmp/truecomputer-target/release/truecomputer validate REQUEST.json
/tmp/truecomputer-target/release/truecomputer execute REQUEST.json --receipt-dir RECEIPTS --execute
```

The live first slice supports focusing an existing window, switching to an
existing workspace, moving the pointer within current monitor bounds, and typing
printable text into the exact active window. Clicks, arbitrary commands,
application launch, screenshots, and visual target selection are not implemented.
Read `TrueComputer/AGENTS.md` and `TrueComputer/docs/CONTRACT.md` before use.

## TrueMem

The trained object is the deterministic anchor map. DocuFilm is the only intake
authority. Its admitted strings and glyph-state objects are mapped into paragraph
blocks, numbered sentences, counts, coordinates, citations, and the six-before
/ current / six-after neighborhood. Query walks the mapped candidate field; it
does not ask an LLM to search, rank, or establish truth.

Core Linux sequence:

```bash
cd TrueMem
PYTHONPATH=src python -m truemem.cli init --runtime-root runtime --dataset-id DATASET
PYTHONPATH=src python -m truemem.cli docufilm-intake --runtime-root runtime --dataset-id DATASET --source DOCUMENT.txt
PYTHONPATH=src python -m truemem.cli status --runtime-root runtime --dataset-id DATASET
PYTHONPATH=src python -m truemem.cli query --runtime-root runtime --dataset-id DATASET --evidence-need EVIDENCE_NEED.json
```

Interactive `docufilm-intake` asks whether to publish `split` or `native`
before writing. Enter keeps the current split layout. The prompt explains that
native is the compact all-in-one publication intended for measured size and
query-speed comparisons, while deterministic answers must remain unchanged.
Headless callers must pass `--output-format split|native`. Native publication
retains the split artifacts as the active query authority until native query
integration and parity are separately proven.

For staged chat sources, native publication also stores explicit `CHAT_TURN`
nodes and conversation-local `NEXT_TURN` edges. One turn may own several
paragraph blocks. Edges use declared conversation IDs and integer turn indexes;
timestamps are properties, not unique identity. Ambiguous duplicate turn
indexes are counted and excluded, and no semantic or cross-conversation edge is
inferred. This is the built-in bounded temporal traversal layer; Neo4j may be a
disposable projection later, but is not an intake or evidence authority.

The public query boundary accepts only `truemem_evidence_need@1`. It rejects
raw questions, claims, prompts, expected answers, and TopK. The operator must
provide subject, relation, qualifier groups, quantity, and requested proof
form. Query returns every exact subject occurrence with its signed 6-1-6 cloud,
plus set-intersection proof locations. It does not decide whether a claim is
true. The older answer-shaped ranked path remains diagnostic code and is not
the public operator retrieval interface.

`deeper-wider` accepts the older prediction-walk packet shape only. It remains
a separate diagnostic and cannot be invoked on, or substituted for, the public
EvidenceNeed result. Use each command's `--help` for the complete current
option set.

Relationship mechanics are specified in
`TrueMem/system/contracts/RELATIONSHIP_GRAPH_616.md`. The predictor exposes all
relationship measurements and uses deterministic lexicographic branch ordering;
it does not use a weighted magic score.

The exact implemented training/storage path, active six-byte record formats,
dormant four-byte alternative, and safe boundary for adding relationship
measurements are recorded in
`docs/TRUEMEM_RELATIONSHIP_TRAINING_SHAPE.md`. Do not describe the dormant
four-byte writer as active intake.

Other coded CLI families include dataset metrics, Q/A ledger inspection,
packet/evidence speech diagnostics, pressure and Top-K diagnostics, batch,
source staging/adapters, crosslinking, special search, determinism receipts,
operator-state audit, and resonance adaptation. Their existence does not make
them part of the default answer path.

Collected material under `TrueMem/research_reference_not_runtime/` is
research evidence only. Its copied scripts are not TrueMem runtime.

Citation output must retain source identity and exact block/sentence or other
native coordinates. The calling LLM may verify those locations and compose the
final answer; it may not replace the cited evidence.

## TrueVision Intake, TrueAudio, and TrueSpeech

TrueVision Intake owns the extracted DocuFilm document/glyph-state reader and
the parent/contained TrueMem handoff. TrueAudio owns audio-state logging and
replay. TrueSpeech consumes replayable TrueAudio state for speech-region
detection and caller-supplied lyric-candidate alignment. TrueSpeech does not
transcribe or invent lyrics.

```bash
cd TrueAudio
PYTHONPATH=. python scripts/trueaudio_log_file_replayable.py --help

cd ../TrueSpeech
PYTHONPATH=.:../TrueAudio python scripts/truespeech_detect_segments.py --help
```

## LocalMemoryChat

```bash
cd LocalMemoryChat
PYTHONPATH=src python -m local_memory_chat.cli init --profile demo
PYTHONPATH=src python -m local_memory_chat.cli import-demo --profile demo
PYTHONPATH=src python -m local_memory_chat.cli add-file data/demo/project_note.md --profile demo --label project-note
PYTHONPATH=src python -m local_memory_chat.cli ask "what did we decide?" --profile demo
```

The implemented CLI also attaches read-only sources, lists them, indexes an
attached source, inspects an opaque chat binary without decoding it, and builds
SQLite support binaries. Counts locate the field; addresses and citations prove
the source. Runtime data stays under the selected profile.

## Clearbox Chat-Chain

```bash
cd clearbox-chat-chain
PYTHONPATH=src python -m clearbox_chat_chain.server --host 127.0.0.1 --port 3219
```

It owns conversation, turn, continuation, branch, and recovery state. It does
not contain TrueMem, TrueMachine, TrueVision, training, or a general tool system.
Its systemd unit is deployment material, not UI.

The locked daily-chat and machine-query design is defined in
`docs/CHAT_LEXICON_BINARY_QUERY_CONTRACT.md`. One day is one logical chat;
dataset symbols remain local; exact strings cross dataset boundaries. Automatic
00:01 sealing and SQLite-to-TrueMem binary conversion are required but are not
yet implemented, so operators must not claim that lifecycle is active.

## TrueCore

TrueCore is a distinct localhost defensive runtime. Its current command map
comes from `truecore/cli/main.py`: `status`, `tail`, `cells`, `reaper`,
`forge`, `help`, and `agents`. Read-only inspection comes before any action.
Containment remains policy-gated and must produce a real receipt.

```bash
cd TrueCore
PYTHONPATH=. python -m truecore.cli.main --help
PYTHONPATH=. python -m truecore.cli.main status
PYTHONPATH=. python -m truecore.cli.main agents
```

The formerly cited `TrueCore/docs/security/TRUECORE_OPERATIONAL_TRUTH_LOCK.md`
is absent in this generation. Inspect executable boundaries and
`TrueCore/TRUECORE_TRUTH_STABILITY_AUDIT_RAIL.md` without treating that audit
rail as a substitute execution witness. Its static help
prompt and factual audit prompt library are real selectable instruction assets,
but they are guidance, not agents, memory, evidence, or action authority.

## Finite host-admitted TrueCore jobs

The operator boundary exposes `job.invoke` with only a caller-selected `job_id`.
The host admits an exact hashed finite plan and its output/resource bindings.
TrueCore invokes registered workers, preserves unsupported or failed steps,
and publishes one terminal job receipt for inspection. The worker family covers
exact source patches, external acceptance, graph review and historical evidence
readiness/order. It does not author code, infer instruction ownership, or make
causal claims. Read `docs/TRUECORE_BOUNDED_JOBS_CONTRACT.md` for the scope,
recovery limits and application-versus-OS protection boundary.

## Unified localhost API

```bash
PYTHONPATH=control-api/src python -m truesystems_api.server --host 127.0.0.1 --port 3220
```

Real routes are:

- `GET /health` and `GET /api/v1/systems`
- `POST /api/v1/truemachine/pulse`
- `POST /api/v1/truemem/query`
- `POST /api/v1/truemem/deeper-wider`
- `POST /api/v1/memory/ask`
- `GET|POST /api/v1/chat/conversations`
- `POST /api/v1/chat/turns`
- `POST /api/v1/chat/continue`
- `GET /api/v1/help/topics`
- `POST /api/v1/help/query`

Help has three read-only depths: layer 1 `quick`, layer 2 `operate`, and layer 3
`source`. Chat access uses provider `truesystems-help` with the matching model
name. See `docs/HELP_SYSTEM.md` for the exact request shape.

TrueCore is health-probed as its own organism; importing its Flask app into
the control API would start agents as a side effect, so the API does not do it.

## Required return discipline

Return the component result unchanged enough to preserve IDs, timestamps,
citations, coordinates, hashes, and receipts. Label failures as failures. A
successful test proves only the path it exercised, not architectural fidelity
or an untested capability. When a requested operation has no real callable,
return `NOT_IMPLEMENTED` and cite the missing boundary; do not substitute an
easier mechanism.

## Provenance

### September 8, 2026 intake and entrypoint qualification

`TrueMem/src/truemem/engine/hardware.py` uses Linux `/proc/meminfo`
`MemAvailable` for available-memory planning when valid, with the existing
sysconf fallback. `docufilm_intake` and its CLI default to no explicit RAM
budget and zero reserved fraction. Explicit caller limits remain supported;
these are application planning values, not operating-system containment.
The worker/resource preflight remains in effect.

`docufilm_intake` rejects visible unsupported source files with
`UNSUPPORTED_INTAKE_SOURCES` before creating the dataset. Declared native
attachments are allowed only for native publication; their inclusion does not
establish media recognition. Hidden-directory exclusion remains unchanged.
Resource preflight also precedes dataset creation.

TrueMachine's command parser registers each state-source option once.
TrueVision recorder and watcher standalone help entrypoints are qualified;
the watcher loads optional audiovisual tools only when post-capture calls run.
This does not qualify the legacy desktop capture backend, resumable playback,
or recursive embedded-media intake.

External verification lives under
`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/`:
`test_intake_ram_policy.py` and `test_system_repairs.py`.

This manual incorporates only code-verified operating laws recovered from the
component source repositories recorded during assembly, checked 2026-08-28.
Excluded or removed claims are recorded in `SUSPECT_DOCUMENTATION.md`.
