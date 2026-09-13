# TrueMachine contract

## Time

`pulse_index` and locked `cadence_ns` are timeline truth. This follows the
TrueVision rule that frame index and FPS are the clock and the TrueAudio rule
that frame index and sample windows determine time. One `Clock.sample()` call
adds wall-clock provenance to a pulse; wall time is not replay timeline truth.

- `utc`: fixed-width UTC `YYYY-MM-DDTHH:MM:SS.NNNNNNNNNZ`
- `utc_date`: UTC `YYYY-MM-DD`
- `unix_time_ns`: signed integer nanoseconds since the Unix epoch
- `monotonic_ns`: Linux monotonic-clock nanoseconds used for ordering
- `elapsed_ns`: monotonic nanoseconds since this engine run began
- `clock_offset_ns`: observed wall-clock difference from the run's monotonic
  projection; this exposes clock adjustment rather than hiding it
- `boot_id`: Linux kernel boot identity
- `run_id`: identity of one engine invocation
- `sequence`: contiguous pulse order within the run
- `timeline_ns`: exactly `(sequence - 1) * cadence_ns`
- `cadence_ns`: immutable cadence for the engine run

`utc` and `utc_date` are rendered from the same `unix_time_ns`; they are never
sampled independently. Wall-clock changes do not affect monotonic ordering.

## Fusion Packs

Each pulse contains the timestamp plus all collector observations from that
sampling boundary. Collectors report either `ok` with data or `error` with an
explicit error. Missing evidence is never replaced with invented values.

The durable order is:

1. serialize one canonical Fusion Pack;
2. append and `fsync` its envelope to `fusion.wal.jsonl`;
3. atomically publish `packs/<run_id>/<sequence>.fusion.json`;
4. atomically update `current.fusion.json`.

The WAL envelope carries the SHA-256 of the exact canonical pack bytes.
Verification recalculates every hash and checks run sequence continuity.

Every observation also carries its source-owned schema, stable content hash,
and source coordinates. TrueVision, TrueAudio, TrueMem, and TrueMem state artifacts
remain owned by those systems; TrueMachine admits their hashes and coordinates
without rewriting their facts. Canonical JSON uses sorted keys and compact
separators so identical admitted state produces identical hashes.

## Boundaries

Plugin Runner and TrueVision may later submit observations through the same
engine intake. Neither is simulated here. TrueVision source truth must remain
native state artifacts, never raw pixels, images, or video.

The system order is locked:

`TrueVision + TrueAudio + Linux state -> TrueMachine/CompuCog -> TrueCore`

TrueMachine is the cognition and Fusion Pack authority. TrueCore is a
downstream security consumer. TrueCore cannot own or rewrite capture,
timestamps, admitted state, fusion, or cognition.

## Repository-state observation

TrueMachine owns repository-state observation because a repository is mutable
machine state. A repository map freezes the exact observed generation and may
derive source-grounded structure without modifying the observed repository.

The current repository-map contract is:

```text
exact Git working-tree generation
-> file paths, bytes, modes where exposed, and SHA-256 identities
-> exact text locations
-> Python AST-owned code objects
-> ownership, source-order, calls, imports, and exact name accesses
-> location-only N-N-N packets and receipts
```

The N-N-N axes are `ownership-source_order-dependency`. Control flow is
`NOT_IMPLEMENTED`; data flow is `EXACT_NAME_ACCESS_EVIDENCE_ONLY`. Those states
must not be upgraded by documentation, callers, or presentation. Syntax-damaged
and unsupported-language files remain exact source with explicit parser status.
Ambiguous and unresolved relationships remain ambiguous and unresolved.

TrueMachine locates and measures repository state. It does not decide whether
a path is safe, vulnerable, authorized, or malicious. TrueCore remains the
downstream policy and authority boundary.

TrueCore exposes this capability through the registered
`truemachine_repository_map` worker. The worker must preserve TrueMachine's
location-only result and leave TrueCore as `truecore.worker_result@1`. This is
the first implementation governed by
`docs/TRUECORE_WORKER_RESULT_AND_SKILL_INDEX_CONTRACT.md`; later TrueMachine
workers must use the same result envelope and manifest-derived skill index.

The first named repository-view generation is implemented in
`src/truemachine/repository_views.py`. It exposes the fifteen work-order methods
as either bounded static investigations or explicit missing-authority results.
Every view returns its classifier rule, independent channel availability,
unresolved prerequisites, truncation state, locations/relationships, a receipt,
and `answer: null`. The view engine does not perform security adjudication.
