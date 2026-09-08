# Aligned development generation — bounded qualification

This worktree is `/home/lamercey/TrueSystems-Alignment`, branched from the frozen
combined generation `294a0da2324043ce4b5a02bc8b98e39d8a321054`.
It is the development authority for changes in this alignment task, not a
whole-system production promotion or a persistent-storage migration.

## Sensory plane: resolved mechanism, distinct name

The owner's TrueCog sensory-plane role maps to the existing documented system
order `TrueVision + TrueAudio + Linux state -> TrueMachine/CompuCog -> TrueCore`.
Evidence: `TrueMachine/README.md` explicitly identifies TrueMachine as the Linux
CompuCog cognition layer; `TrueMachine/docs/CONTRACT.md` fixes that ordering.
`TemporalEngine.pulse`, `Observation`, `FusionPack` and `FusionStore.commit`
implement collection, per-source errors, timestamps, hashes, WAL and publication.

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
schema, request_id, operation and arguments. There are two connected operations:
`help.list` and `sensory.inspect`. Unknown operations fail closed.

The host provides the path and expected byte hash; the model provides an opaque
artifact reference and expected run/sequence from witnessed/request information.
The adapter reads already-admitted artifacts. It does not capture, start agents,
write a substrate, modify a dataset, invoke the legacy API or bypass HID controls.
Existing permission machinery is untouched. Grants authorize only these narrow
reads, not live mutation or a general-purpose runner.

It validates the Fusion Pack shape, timeline, wall-time consistency, per-source
coordinates/status and data hashes. It returns source data intact, marks failed
collectors PARTIAL, and issues a deterministic result hash with a limited stated
verification scope. Semantic correctness and actual live-world freshness are not
established by byte hashing. The expected run/sequence prevents accidental
substitution, not unbounded clock-based freshness claims.

Only this API is to be exposed to a later model host. This is not OS isolation
against an untrusted process with independent filesystem/network privileges.
No local model is currently loaded or connected, and existing human/development
API routes remain separate. They have not been secretly rerouted or removed.

## Help reconciliation

The combined TrueMem topic now uses DocuFilm admission, structured EvidenceNeed,
no raw question/top_k, and diagnostic-only deeper-wider. The operator manual's
missing TrueCore truth-document reference is explicitly corrected, not replaced
with a fabricated file. The new boundary's help comes directly from its fixed
operation table, so it advertises only its two actual operations.

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

Media execution is intentionally not exposed by the initial two-operation model
boundary. Each future worker requires its own input/output, permission, side-effect,
failure, retry and receipt qualification before registration. That is remaining
integration work, not something the model should learn as completed.
