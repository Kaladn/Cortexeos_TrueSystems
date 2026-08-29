# Linux TrueSystems operator manual

This is the canonical operating map for a small deterministic capability model
and for human or model callers. It teaches selection and handoff, not prose
generation. The model chooses a real operation, supplies its exact inputs, and
returns the operation's result and citations to the calling model.

## Whole-system map

```text
Linux/native state artifacts -> TrueMachine -> verified Fusion Packs
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
| Verify a TrueMachine state directory | TrueMachine | `python -m truemachine verify` | JSON verification result |
| Read document/glyph state | TrueVision Intake / DocuFilm | `truevision_intake.document_state` | document read plus stable glyph-state records |
| Admit a document and build its deterministic map | TrueVision Intake / DocuFilm + TrueMem | `python -m truemem.cli docufilm-intake` | parent/contained anchors, dataset-local symbols, counts, coordinates, relationships, citations |
| Record or replay derived audio state | TrueAudio | `TrueAudio/scripts/trueaudio_*.py` | audio-state artifacts, manifests, and receipts |
| Detect bounded speech regions | TrueSpeech | `TrueSpeech/scripts/truespeech_detect_segments.py` | speech/background candidates without transcript claims |
| Retrieve a cited answer packet | TrueMem | `python -m truemem.cli query` | cited local packet; `model_used` is `none` |
| Search beyond the first packet | TrueMem | `python -m truemem.cli deeper-wider` | separate deeper/wider packet |
| Search local remembered material | LocalMemoryChat | `python -m local_memory_chat.cli ask` | cited memory packet and receipt |
| Retain/continue ordered conversation | Clearbox Chat-Chain | local HTTP server | persisted conversation/turn result |
| Observe or invoke a coded security agent | TrueCore | `python -m truecore.cli.main agents ...` | agent state/decision/receipt |
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
PYTHONPATH=src python -m truemem.cli query --runtime-root runtime --dataset-id DATASET --question "QUESTION"
```

Use `deeper-wider` only after the first query packet has been returned. It is a
second, wider relationship search and must remain a separate result so the
caller can compare it with the first answer. Use each command's `--help` for
the complete current option set.

Relationship mechanics are specified in
`TrueMem/system/contracts/RELATIONSHIP_GRAPH_616.md`. The predictor exposes all
relationship measurements and uses deterministic lexicographic branch ordering;
it does not use a weighted magic score.

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

TrueCore's current truth document is
`TrueCore/docs/security/TRUECORE_OPERATIONAL_TRUTH_LOCK.md`. Its static help
prompt and factual audit prompt library are real selectable instruction assets,
but they are guidance, not agents, memory, evidence, or action authority.

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

This manual incorporates only code-verified operating laws recovered from the
component source repositories recorded during assembly, checked 2026-08-28.
Excluded or removed claims are recorded in `SUSPECT_DOCUMENTATION.md`.
