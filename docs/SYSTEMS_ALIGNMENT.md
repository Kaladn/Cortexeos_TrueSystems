# Aligned development generation — bounded qualification

This worktree is `/home/lamercey/TrueSystems-Alignment`, branched from the frozen
combined generation `294a0da2324043ce4b5a02bc8b98e39d8a321054`.
It is the development authority for changes in this alignment task, not a
whole-system production promotion or a persistent-storage migration.

## Sensory plane: resolved mechanism, distinct name

The owner's TrueCog sensory-plane role maps to the existing documented system
order `TrueVision + TrueAudio + Linux state -> TrueMachine -> TrueCore`.
Evidence: `TrueMachine/README.md` identifies CompuCog as design lineage;
`TrueMachine/docs/CONTRACT.md` fixes the qualified pull boundary and denies an
automatic TrueMachine-to-TrueCore push.
`TemporalEngine.pulse`, `Observation`, `FusionPack` and `FusionStore.commit`
implement collection, per-source errors, pack time, per-collector monotonic
windows, cadence-overrun measurements, hashes, WAL and publication.

TrueCog remains the owner-facing role name, not a discovered package/entrypoint.
No new sensory engine is invented or renamed. This mapping does not claim that
every sensory modality or cross-system handoff is already connected.

## Generation authority

- Frozen combined source remains preserved at its original mount path/commit.
- This branch owns the new adapter/help changes only; no live installation.
- Anchor-Index remains a separate exact-anchor candidate. Its CPU/storage parity
  and GPU acceleration decisions are distinct. GPU promotion was not earned.
- Reasoning-Space remains its separately frozen Phase 0–3 reference engine.
- Independent TrueVision and TrueMachine checkouts are not silently substituted.
- CompuCog/SecureCore source is lineage, not current execution authorization.
- Model education remains paused until alignment is reviewed.

## TrueCore-only local-model boundary

`TrueCore/truecore/operator_boundary.py` exposes `OperatorBoundary.handle`.
Host integration supplies grants and artifact bindings; the request supplies only
schema, request_id, operation and arguments. The completed read-only host connects
`help.list`, `help.query`, `sensory.inspect`, `source.classify`, `media.describe`,
`worker.invoke`, and `machine.invoke`.
Unknown operations fail closed. See `MODEL_HOST_CONTRACT.md` for the transport,
component readers and exact qualification boundary.

The host provides the path and expected byte hash; the model provides an opaque
artifact reference and expected run/sequence from witnessed/request information.
The adapter reads already-admitted artifacts. It does not capture, start agents,
write a substrate, modify a dataset, invoke the legacy API or bypass HID controls.
Existing permission machinery is untouched. Grants authorize only these narrow
reads, not live mutation or a general-purpose runner.

The `machine.invoke` generation exposes fourteen registered read-only workers:
`fs.list`, `fs.find`, `fs.read_metadata`, `fs.hash`, `fs.disk_usage`, and
`fs.duplicate_scan`; `process.list`, `package.inventory`, `device.inventory`,
`mount.inspect`, `network.status`, and `log.query`; and fixed-argv
`service.status` and `repo.status`. The host binds each resource to one allowed
worker family plus entry, byte, result, and command-time budgets. The model
supplies only typed operation parameters. TrueCore refuses cross-worker resource
reuse, absolute and parent-traversal paths, symlink traversal, unknown or changed
resources, ungranted workers, model-supplied commands, and exceeded budgets.
TrueMachine returns locations and measurements with `answer: null`; it does not
recommend mutation or decide safety. Mount UUID remains explicitly unresolved
because the current mount resource does not independently establish it.

It validates the `truemachine.fusion@2` shape, timeline, wall-time consistency,
scheduling arithmetic, per-source collection windows, coordinates/status, and
data hashes. It returns source data intact, marks failed collectors PARTIAL, and
issues a deterministic result hash with a limited stated verification scope.
Semantic correctness and actual live-world freshness are not established by byte
hashing. The expected run/sequence prevents accidental substitution, not
unbounded clock-based freshness claims.

`truecore.model_host` now exposes only this API over bounded JSONL. It does not
load a model. This is not OS isolation
against an untrusted process with independent filesystem/network privileges.
No local model is currently loaded or connected, and existing human/development
API routes remain separate. They have not been secretly rerouted or removed.

## Help reconciliation

The combined TrueMem topic now uses DocuFilm admission, structured EvidenceNeed,
no raw question/top_k, and diagnostic-only deeper-wider. The operator manual's
missing TrueCore truth-document reference is explicitly corrected, not replaced
with a fabricated file. The new boundary's help comes directly from its fixed
operation table, so it advertises only operations implemented at that boundary.

## Workflow and retry

External acceptance executes real TrueMachine TemporalEngine/FusionStore with
deterministic fixture collectors, verifies WAL, host-binds the resulting artifact,
calls TrueCore, verifies output custody and receipt, and stops with the correct
status. Fault coverage includes missing bindings, invalid requests, denied grants,
wrong run/sequence, corrupt evidence, inconsistent timeline/time, failed collector,
and corrected-binding retry. Retry is safe here because the boundary is read-only;
no retry rule is extrapolated to future actions.

## Media control ownership

Native TrueVision capture writes cell state; TrueFrameGen renders derived frames.
Its parsed options include duration, capture/target FPS, motion mode, smoothing,
temporal radius, recursion and region controls. Option existence is not quality
qualification. Read the renderer branches before directing them.
TrueAudio includes file/machine state logging and state-derived WAV replay.
TrueSpeech detects speech-like segments and aligns supplied lyrics; it is not
an unrestricted transcription engine. TrueVisionIntake owns document/glyph state.
The external media catalog records exact source paths, hashes and Python argument
declarations; Rust option literals are labelled as a narrower static extraction.

Media execution is intentionally not exposed by the current read-only model
boundary. Each future worker requires its own input/output, permission, side-effect,
failure, retry and receipt qualification before registration. That is remaining
integration work, not something the model should learn as completed.

## Registered repository-worker bridge

`worker.invoke` accepts only a host-granted repository worker identity, one
host-bound TrueMachine repository-map resource identity, and a bounded integer
result limit. `TrueCore/truecore/registered_worker_bridge.py` rejects workers
outside the registered read-only repository-graph family, any worker with write
authority, changed map manifests, model-supplied paths/modules/commands, and
results that do not validate as `truecore.worker_result@1`.

Fifteen repository workers are registered. Eight return witnessed/static
investigation candidates. Seven deliberately return `NOT_IMPLEMENTED` with the
missing graph authorities required for stronger conclusions. Their existence as
callable workers does not imply that the missing control-flow, data-flow,
test-target, documentation-claim, security-role, route-policy, privileged-sink,
or canonical-object relationships exist.
