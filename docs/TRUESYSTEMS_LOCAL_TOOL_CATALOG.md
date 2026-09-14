# TrueSystems Local Tool Catalog

Status: code-derived working catalog
Catalog date: 2026-09-14
Repository state inspected: the containing commit on `alignment/truecore-boundary`
Purpose: provide one inexpensive navigation index for local TrueSystems operations and the bounded operations still to be built.

## Authority legend

| Mark | Meaning |
| --- | --- |
| `MODEL-LIVE` | Connected to the current model-facing TrueCore boundary. |
| `REGISTERED` | Has a validated TrueCore agent manifest, but is not necessarily exposed to the model. |
| `DECLARED` | Has a code or tool declaration; connection and qualification must be checked separately. |
| `CLI-LIVE` | Has a directly callable command-line entrypoint. |
| `PLANNED` | Required future capability; not executable today. |
| `PARKED` | Explicitly not active. |
| `APPROVAL` | Must pass an explicit TrueCore approval gate before execution. |

This catalog does not promote a script, HTTP route, documentation claim, or manifest declaration into a model tool. Current capability truth comes from executable code, its registered boundary, and passing qualification tests.

## Governing operation law

```text
human or model
-> bounded request
-> TrueCore validates identity, arguments, scope, grant, and approval
-> registered worker
-> TrueMachine or owning TrueSystems component
-> result plus verification receipt
```

All destructive operations are permitted only through an explicit approval gate. A destructive capability must also require a dry run when meaningful and publish an execution/postcondition receipt. Canonical datasets, frozen manifests, receipts, security policy, and TrueCore authority configuration require dedicated admission or supersession workflows; a generic filesystem worker may not silently modify them.

## Current model-facing TrueCore operations

Source: `TrueCore/truecore/operator_boundary.py`

| Operation | Mark | Function |
| --- | --- | --- |
| `help.list` | `MODEL-LIVE` | List this boundary, contracts, limits, and granted workers. |
| `sensory.inspect` | `MODEL-LIVE` | Inspect one host-admitted TrueMachine Fusion Pack. |
| `help.query` | `MODEL-LIVE` | Read the code-grounded help map. Guidance is not execution proof. |
| `source.classify` | `MODEL-LIVE` | Classify a host-admitted text source without admitting it. |
| `media.describe` | `MODEL-LIVE` | Describe an admitted media tool declaration without executing it. |
| `worker.invoke` | `MODEL-LIVE` | Invoke one host-granted read-only repository worker on one host-bound repository map. |
| `machine.invoke` | `MODEL-LIVE` | Invoke one host-granted read-only TrueMachine worker on one worker-bound resource. |

The model cannot supply filesystem paths, executable commands, Python modules, manifests, permissions, grants, or approval records through this boundary.

## Current model-eligible repository workers

Source: `TrueCore/truecore/agents/repository_graph_workers.py`
Result schema: `truecore.worker_result@1`
Authority: read-only static investigation over a host-bound TrueMachine repository map.

| Worker ID | Returns |
| --- | --- |
| `repo_agent_registration` | Agent-registration candidates. |
| `repo_canonical_evidence_writers` | Returns `NOT_IMPLEMENTED` until a canonical-evidence object registry and data-flow authority exist. |
| `repo_code_without_documentation` | Returns `NOT_IMPLEMENTED` until documentation-claim relationships and code-capability classification exist. |
| `repo_detached_subgraphs` | Detached static subgraph candidates. |
| `repo_direct_truemem_references` | Direct TrueMem reference locations and relationships. |
| `repo_documentation_without_code` | Returns `NOT_IMPLEMENTED` until documentation-claim relationships and semantic claim-to-code bindings exist. |
| `repo_duplicate_implementations` | Static duplicate-implementation candidates. |
| `repo_external_entrypoints` | External entrypoint candidates. |
| `repo_filesystem_writers` | Filesystem-write call candidates. |
| `repo_no_incoming_dependencies` | Objects with no resolved incoming dependency in the map. |
| `repo_process_execution` | Process-execution call candidates. |
| `repo_security_config_writers` | Returns `NOT_IMPLEMENTED` until a security-configuration object registry and data-flow authority exist. |
| `repo_truecore_bypass` | Returns `NOT_IMPLEMENTED` until expected-route policy, security roles, and control/data-flow authority exist. |
| `repo_unresolved_privileged_reachability` | Returns `NOT_IMPLEMENTED` until a privileged-sink registry and control/data-flow authority exist. |
| `repo_untested_privileged_sinks` | Returns `NOT_IMPLEMENTED` until privileged-sink and test-target relationships exist. |

These workers locate and classify evidence. They do not pronounce vulnerabilities from names, textual proximity, or unresolved calls.

## Other registered TrueCore workers

Manifests: `TrueCore/truecore/live_agents/AGENTS/agents/*.agent.json`

| Worker | Mark | Mutation class | Approval |
| --- | --- | --- | --- |
| `evidence_workspace_agent` | `REGISTERED` | Read-only | No |
| `temporal_causality_log_checker` | `REGISTERED` | Read-only | No |
| `process_change` | `REGISTERED` | Local agent-state write | No |
| `truemachine_repository_map` | `REGISTERED` | Derived-artifact write | No |
| `docs_folder_to_pdf` | `REGISTERED` | Generated PDF artifact write | `APPROVAL` |

These workers are not accepted by the present model bridge because that bridge admits only the read-only repository-graph family.

## TrueCore capability registry

Source: `TrueCore/truecore/tools/capabilities.py`

| Capability | Class | Approval | State |
| --- | --- | --- | --- |
| `temporal.read` | Read | No | `DECLARED` |
| `forge.relationships.trace` | Analyze | No | `DECLARED` |
| `truevision.code_glyph.read` | Analyze | No | `DECLARED` |
| `central_writer.report_request` | Write | No | `DECLARED` |
| `firewall.block_ip` | Mutate | Yes, with dry run | `DECLARED` |

The registry rejects every `mutate` capability unless `requires_approval`, `dry_run_required`, and `central_writer_required` are all true. A declaration alone does not prove that the backend is connected or qualified.

## TrueCore action registry

Source: `TrueCore/truecore/actions/registry.py`

| Action | State | Notes |
| --- | --- | --- |
| `worker.diagnostics.inspect` | Live read route | Reads toolbox diagnostics. |
| `runtime.start_baseline` | `PLANNED` | Backend and validation routes are missing. |
| `mapping.window.update` | `PLANNED` | Backend and validation routes are missing; approval and dry run are declared. |

## TrueCore operator CLI

Source: `TrueCore/truecore/cli/main.py`

```text
status
tail
cells
reaper
forge
help
agents
```

These are operator/developer CLI surfaces, not automatically model-facing tools.

## TrueMachine

Source: `TrueMachine/src/truemachine/cli.py`

| Command | Mark | Function |
| --- | --- | --- |
| `truemachine run` | `CLI-LIVE` | Record bounded identity, memory, process, network, and admitted component-state observations. |
| `truemachine verify` | `CLI-LIVE` | Verify the Fusion Store state directory. |
| `truemachine map-repository` | `CLI-LIVE` | Build an exact source-grounded ownership/source-order/dependency repository map. |
| `truemachine query-repository` | `CLI-LIVE` | Return a location-only N-N-N packet. |
| `truemachine verify-repository-map` | `CLI-LIVE` | Verify map artifacts against their observed source. |

Current collectors:

```text
IdentityCollector
MemoryCollector
ProcessCollector
NetworkCollector
StateArtifactCollector(truevision)
StateArtifactCollector(trueaudio)
StateArtifactCollector(truemem)
```

TrueMachine contains fourteen qualified read-only filesystem and machine
observation workers. It still contains no general process-control,
arbitrary-execution, or mutation housekeeping worker.

## TrueComputer

Source: `TrueComputer/src/main.rs`

Commands:

```text
truecomputer inspect
truecomputer validate REQUEST.json
truecomputer execute REQUEST.json --receipt-dir DIR --execute
```

Bounded desktop actions:

```text
focus_window
switch_workspace
move_pointer
type_text
```

`--execute` is an accident-prevention interlock, not authenticated human approval. TrueComputer is not connected to the current model boundary. It does not implement clicking, scrolling, dragging, key chords, screenshots, visual grounding, arbitrary process launch, deletion, password entry, payment, publication, or unattended action loops.

## TrueMem

Source: `TrueMem/src/truemem/cli.py`

```text
init
docufilm-intake
status
system-metrics
dataset-overview
query
deeper-wider
qa-recent
qa-export
qa-show
packet-speech
evidence-speech
pressure-probe
topk-diagnostic
answer-reasoning-reverse-walk
pressure-coordination-audit
count-walk-speech
batch
adapters
prepare
stage-codex
stage-codex-md
stage-chatgpt
crosslink
special-search
determinism
operator-state-audit
resonance-adapt
```

TrueMem CLI operations are not automatically TrueCore tools.

## TrueVision Intake

Manifests: `TrueVisionIntake/tool_drop/*.tool.json`

| Tool | Mark | Effect |
| --- | --- | --- |
| `truevision_code_glyph_reader` | `DECLARED` active callable | Read-only exact code-state analysis. |
| `truevision_document_state_movie` | `DECLARED` active callable | Writes document-state artifacts and receipts; optionally surfaces state. |

## TrueVision

Manifests: `TrueVision/tool_drop/**/*.tool.json`

### Contract references

```text
truevision_receipt_manifest_rules
truevision_state_loop_law
truevision_state_source_law
```

### Active capture and observation

```text
truevision_region_snip
truevision_resonance_recorder
truevision_state_video_watcher
truevision_still_image_capture
truevision_capture_rs
```

### Active recognition and profiling

```text
truevision_exact_photo_state_snap
truevision_extract_lightning_signature
truevision_geometry_engine
truevision_signature_profile_extract
truevision_state_focus_lens
truevision_state_recognition
atmosphere_profile_from_capture
atmosphere_toolset_create
element_creation_profile_from_capture
meter_grid_from_capture
truevision_atmosphere_tools
truevision_driving_school
truevision_meter_grid
```

### Active audio/media helpers

```text
audio_probe_duration
audio_analyze_levels
audio_extract_features
```

### Active replay, rendering, and studio surfaces

```text
truevision_state_media_qa_receipt
truevision_state_replay
render_stem_art_state_transform_lab
render_truedepth_fog_reveal_samples
truevision_render_template
manifest_browser
render_preset_library
truevision_studio_server
trueframegen_stream_rs
```

### Finalized/native operations whose manifests require operator approval

```text
cleveland_graffiti_state_proof
truevision_cortex_photo_state_rs
truevision_phoenix_flats_state_rs
```

### Parked

```text
render_stem_state_nightmare
render_trudepth_rave_laser_sample
truevision_project_edge_from_capture
truevision_yolo_event_focus
```

TrueVision contains additional executable scripts. Only the declarations above are cataloged as tool surfaces; executable presence alone is not qualification or TrueCore registration.

## TrueAudio

Manifests: `TrueAudio/tool_drop/**/*.tool.json`

| Tool | Mark | Required boundary |
| --- | --- | --- |
| `trueaudio_log_file_replayable` | `DECLARED` active callable | Local-file read and state-write gate |
| `trueaudio_log_machine_pre_sound` | `DECLARED` active callable | Audio-capture gate |
| `trueaudio_log_machine_replayable` | `DECLARED` active callable | Audio-capture gate |
| `trueaudio_log_pre_sound` | `DECLARED` active callable | Local-file read and state-write gate |
| `trueaudio_replay_replayable` | `DECLARED` active callable | Generated-audio write gate |
| `trueaudio_replay_state` | `DECLARED` active callable | Generated-audio write gate |

## TrueSpeech

Manifests: `TrueSpeech/tool_drop/*.tool.json`

| Tool | Mark | Effect |
| --- | --- | --- |
| `truespeech_detect_segments` | `DECLARED` active callable | Writes candidate reports, manifests, and receipts. |
| `truespeech_align_lyrics_candidate` | `DECLARED` active callable | Writes candidate alignment reports, manifests, and receipts. |

Candidate output is not automatically factual authority.

## LocalMemoryChat

Source: `LocalMemoryChat/src/local_memory_chat/cli.py`

```text
init
import-demo
add-file
attach-source
sources
index-source
inspect-binary
sqlite-support
ask
```

## Other executable surfaces

| Surface | Entrypoint | Classification |
| --- | --- | --- |
| Clearbox Chat Chain | `clearbox-chat-chain` | Local server CLI; not a model tool |
| Control API | `truesystems-api` | HTTP server; routes are not automatically model operations |
| Training programs | `training/*.py` | Offline developer/research scripts; not model tools |
| TrueCore front door | `TrueCore/frontdoor/src/main.rs` | Native component entrypoint; inspect contract before exposure |

## Qualified bounded machine observation

The following operations are `MODEL-LIVE` through `machine.invoke`. Their
registered agent manifests and code-derived help bind to
`TrueCore/truecore/agents/machine_navigation_workers.py`; observation is owned by
`TrueMachine/src/truemachine/navigation.py`,
`TrueMachine/src/truemachine/system_observation.py`, and
`TrueMachine/src/truemachine/command_observation.py`.

| Operation | Bounded result |
| --- | --- |
| `fs.list` | Direct child locations under a host-bound directory; symlinks are reported but not followed. |
| `fs.find` | Substring name matches under bounded depth, entry, and result limits. |
| `fs.read_metadata` | Type, size, mode, timestamps, device, and inode for one location. |
| `fs.hash` | SHA-256 and byte count for one bounded regular file. |
| `fs.disk_usage` | Bounded recursive file, directory, and byte measurements. |
| `fs.duplicate_scan` | SHA-256-backed duplicate-location groups; no deletion recommendation. |
| `process.list` | Bounded procfs process-status locations; unreadable records remain unresolved. |
| `package.inventory` | Bounded installed-package facts from host-bound pacman database records. |
| `device.inventory` | Bounded sysfs block-device facts and stable kernel identities where present. |
| `mount.inspect` | Procfs mount records; UUID remains explicitly unresolved pending separate device identity. |
| `network.status` | Bounded sysfs interface state and counters; no socket or routing claim. |
| `log.query` | Matching physical UTF-8 lines from one host-bound regular log file. |
| `service.status` | Fixed-argv status fields from one hash-bound systemctl executable. |
| `repo.status` | Fixed-argv Git branch/status and optional remote locations from one host-bound repository. |

The model cannot provide an absolute path, command, executable, module, root
binding, resource-to-worker assignment, grant, or host budget. All results use
`truecore.worker_result@1` and contain no answer.

## Morning build list: bounded local housekeeping

These IDs are proposed catalog names only. They are not live until code,
schemas, grants, approval behavior, receipts, and external acceptance tests exist.

### Reversible/scoped writes

| Proposed operation | Required boundary |
| --- | --- |
| `fs.mkdir` | Host-bound destination, scoped write grant, receipt |
| `fs.copy` | Exact source/destination, collision policy, pre/post hashes |
| `fs.move` | Exact source/destination, rollback information, pre/post hashes |
| `fs.rename` | Same-filesystem exact rename with collision refusal |
| `fs.write_new` | Create-new only; refuse an existing target |
| `archive.create` | Exact input manifest and create-new output |
| `archive.extract_staging` | Staging directory only; path traversal and collision rejection |

### Destructive or privileged operations

| Proposed operation | Mandatory boundary |
| --- | --- |
| `fs.delete` | `APPROVAL`, exact resolved target, dry run, pre-state receipt, postcondition |
| `fs.overwrite` | `APPROVAL`, exact target, recoverable backup when possible, pre/post hashes |
| `fs.truncate` | `APPROVAL`, exact regular file, prior size/hash, postcondition |
| `fs.chmod` | `APPROVAL`, exact mode transition and postcondition |
| `fs.chown` | `APPROVAL`, exact principal transition and postcondition |
| `process.stop` | `APPROVAL`, exact PID plus observed identity, bounded signal |
| `process.kill` | `APPROVAL`, exact PID plus observed identity, last-resort signal |
| `service.disable` | `APPROVAL`, exact unit and before/after state |
| `package.remove` | `APPROVAL`, exact package set and dependency preview |
| `firewall.change` | `APPROVAL`, dry-run ruleset diff and rollback artifact |
| `mount.mount` | `APPROVAL`, stable device identity, mountpoint, filesystem and options |
| `mount.unmount` | `APPROVAL`, exact mounted filesystem and busy-state check |

Arbitrary shell text is not a housekeeping operation. Any future execution worker must use a fixed operation registry or executable allowlist, typed argument vectors, explicit working directory, environment restrictions, time/output budgets, approval classification, and receipts.

## Common result and receipt requirements

Every new worker must return `truecore.worker_result@1` or a formally superseding schema. A mutating operation receipt must identify at least:

```text
principal
worker_id
operation
resource_class
source
destination
resolved_targets
pre_hash
post_hash
grant_id
approval_id
started_at
completed_at
execution_status
verification_status
rollback_or_recovery
```

Required resource classes:

```text
EXTERNAL_UNADMITTED
WORKSPACE_MUTABLE
DERIVED_ARTIFACT
ADMITTED_CANONICAL
FROZEN_CANONICAL
SECURITY_AUTHORITY
```

A valid approval authorizes only the resolved operation, targets, and arguments recorded in that approval. It is not a reusable permission to perform adjacent destructive work.

## Next qualification order

1. Freeze exact schemas for the read-only housekeeping primitives.
2. Implement them in TrueMachine and expose them only through host-granted TrueCore workers.
3. Establish the common receipt envelope.
4. Qualify create-new, copy, move, rename, archive, and staging extraction.
5. Implement the TrueCore approval object and bind it cryptographically to one operation request.
6. Add destructive operations individually, beginning with exact-target deletion.
7. Connect TrueComputer through the same TrueCore grant/approval boundary.
8. Register qualified TrueVision, TrueAudio, TrueSpeech, TrueMem, and LocalMemoryChat operations without exposing their raw CLIs.
9. Test each instruction and failure state externally before model exposure.
