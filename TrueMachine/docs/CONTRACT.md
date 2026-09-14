# TrueMachine contract

## Time

`sequence` and locked `cadence_ns` are timeline truth. This follows the
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
- `scheduling.scheduled_monotonic_ns`: intended monotonic start for this pulse
- `scheduling.pulse_started_monotonic_ns`: observed monotonic start
- `scheduling.scheduling_lateness_ns`: nonnegative observed start minus intended start
- `scheduling.cadence_boundaries_missed_before_start`: whole cadence boundaries
  crossed by that lateness; this exposes catch-up pressure and does not claim a
  dropped or recovered observation
- `collection_started_monotonic_ns` / `collection_ended_monotonic_ns`: the
  witnessed serial collection window for each source
- `collection_duration_ns`: exactly collection end minus collection start

`utc` and `utc_date` are rendered from the same `unix_time_ns`; they are never
sampled independently. Wall-clock changes do not affect monotonic ordering.

## Fusion Packs

Each `truemachine.fusion@2` pulse contains the pack timestamp, scheduling
quality, and all collector observations attributed to that pulse. Collectors
report either `ok` with data or `error` with an explicit error. Both states keep
their monotonic collection window. Missing evidence is never replaced with
invented values.

The durable order is:

1. acquire the state directory's advisory exclusive writer lock;
2. serialize one canonical Fusion Pack;
3. append and `fsync` its envelope to `fusion.wal.jsonl`;
4. atomically publish `packs/<run_id>/<sequence>.fusion.json`;
5. atomically update `current.fusion.json`;
6. release the writer lock.

The WAL envelope carries the SHA-256 of the exact canonical pack bytes.
`FusionStore.verify()` recalculates that envelope hash, binds envelope run and
sequence to the embedded pack, recalculates each observation-data hash, checks
run sequence continuity, checks every immutable per-run pack against its WAL
entry, and checks `current.fusion.json` against the final WAL entry. It detects
but does not repair WAL-ahead publication failure. TrueCore independently checks
the structure and hashes of a separately host-bound Fusion Pack.

Every observation also carries its source-owned schema, stable content hash,
and source coordinates. TrueVision, TrueAudio, and TrueMem state artifacts
remain owned by those systems; TrueMachine admits their hashes and coordinates
without rewriting their facts. Canonical JSON uses sorted keys and compact
separators so identical admitted state produces identical hashes.

## Boundaries

Plugin Runner and TrueVision may later submit observations through the same
engine intake. Neither is simulated here. TrueVision source truth must remain
native state artifacts, never raw pixels, images, or video.

The system order is locked:

`TrueVision + TrueAudio + Linux state -> TrueMachine -> TrueCore`

This is a qualified pull boundary: an external host binds a completed Fusion
Pack for TrueCore inspection. TrueMachine does not invoke TrueCore. TrueMachine
owns observation and Fusion Pack custody. TrueCore is a downstream security
consumer and cannot own or rewrite capture, timestamps, admitted state, or
fusion. Broader CompuCog/TrueCog cognition remains a design target rather than a
claim established by this package.

Linux network observation contains interface state and counters only. Machine
load is a separate `linux.load` observation sourced from `getloadavg(3)`. The
collectors are sampled serially after the pack time sample; their individual
start/end windows prove that order. Their presence in one pack is shared
attribution, not a claim of simultaneous measurement. A cadence overrun remains
visible as scheduling lateness and whole nominal boundaries missed before the
pulse starts; the engine's current immediate catch-up behavior is not hidden.

Memory, process, and network collectors use their `@2` schemas. They return a
`collection_status` plus explicit `unresolved` records when required memory
fields, process-status files, or interface fields cannot be read or parsed.
Individual failures are no longer silently discarded. A top-level collector
failure still becomes an error Observation at the engine boundary.

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

Every returned location also carries a deterministic path-derived source scope
(`RUNTIME_SOURCE`, `TRAINING_OR_EXPERIMENT`, `TEST`, `SCRIPT`, `DOCUMENTATION`,
`PROJECT_SOURCE`, or `RESEARCH_REFERENCE_NOT_RUNTIME`). This scope is not
reachability proof. An
unqualified string `.replace()` call is not classified as a filesystem write,
and an internal helper merely containing the characters `truemem` is not a
direct TrueMem reference.

`src/truemachine/repository_integrity.py` creates deterministic snapshots of a
clean Git repository plus explicitly selected external derived-view trees. It
stores content-addressed SHA-256 blobs, a canonical manifest, exact file modes,
and a snapshot identity. Verification re-hashes the manifest, every referenced
blob, repository bytes, and derived-view bytes. A UTF-8 change is reported at
line/column and exact changed-glyph coordinates; binary changes use byte
coordinates. Added and missing paths remain distinct.

An integrity failure requires safe/secure mode. The incident builder preserves
the observed suspect bytes in quarantine and materializes a separate read-only
trusted tree from the snapshot. It never overwrites the suspect source. Actor
identity remains `UNRESOLVED_NO_OS_AUDIT_WITNESS` unless a separately qualified
OS audit event names the writer; file ownership and modification time are not
offender proof. Read-only verification is registered as `integrity.verify` and
can enter only through a host-bound TrueCore integrity-snapshot resource.
That worker enforces host-owned entry, per-file byte, total-byte, and elapsed-time
budgets. Snapshot creation and safe-mode response are administrative CLI/API
operations and are not callable by the model.

## Bounded filesystem observation

`src/truemachine/navigation.py` implements six read-only observations beneath a
caller-bound absolute root: directory listing, substring name finding, metadata,
SHA-256, recursive disk usage, and duplicate-content grouping. Requests use only
relative paths. The implementation reports symlinks in a direct listing but
never follows them as targets or during recursion. Parent traversal, absolute
request paths, special hash targets, exceeded entry/byte budgets, and target
escape are refused.

Every packet carries the root device/inode identity, observed relative
locations, measurements, explicit unresolved entries, truncation state, a
deterministic receipt, and `answer: null`. TrueCore owns grants and resource
binding; TrueMachine only observes the bounded state. These operations neither
write files nor decide which duplicate, file, or directory should be changed.

## Bounded Linux and command observation

`src/truemachine/system_observation.py` adds six read-only observations over
separate host-bound roots. `process.list` reads bounded procfs status records;
`network.status` reads bounded sysfs interface records; `package.inventory`
reads pacman local-database records; `device.inventory` reads sysfs block-device
records; `mount.inspect` reads one procfs `mountinfo` file; and `log.query`
returns matching physical UTF-8 lines from one bounded regular file. They do not
signal processes, change interfaces, invoke a package manager, mount storage, or
rotate logs.

The process and network collectors preserve unreadable or malformed entries as
explicit unresolved records. Host entry, file-byte, total-byte, and result
limits apply. `mount.inspect` currently reports the kernel major/minor identity,
source, filesystem, and mount location, but reports UUID as unresolved because
no independent device-identity resource is bound. Same-record proximity does
not authorize a UUID inference.

`src/truemachine/command_observation.py` contains the only command-backed
operations in this generation: `service.status` and `repo.status`. Their argv is
fixed in code. The model cannot supply a command or executable. TrueCore binds
and hashes the exact `systemctl` or Git executable, binds the unit-status worker
or repository root to that resource, and rechecks identities before and after
execution. Calls have fixed output and wall-time budgets. Git status disables
optional locks, system/global configuration, and filesystem-monitor execution.
These observations return locations and measurements with `answer: null`; they
do not start services, alter repositories, or adjudicate machine safety.

Every `machine.invoke` resource names exactly which registered worker may use
it. A root admitted for one observation cannot be reused by a different worker
merely because both operations accept a directory.
