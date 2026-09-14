# Receipt consolidation and retained operational abilities

This contract describes the native receipt changes qualified on September 14,
2026. It does not add a service, a scheduler, an authorization source, or the
seven missing repository graph authorities. The operator implements and reviews;
native owners still produce the underlying state and proof.

## Preserved boundaries

Logged TrueAudio/TrueVision source state, capture timing, replay inputs, native
validation, generation inputs, calibration, manifests and teacher-purge policy
remain outside this housekeeping change. TrueMem intake receipts and freshness
readers, TrueMachine WAL/Fusion records, TrueComputer action/reuse records and
Forge records retain their existing ownership. A compact outer receipt is not
a replacement for any of these records.

No new periodic logger or cleanup is installed by this code. Budget scans and
cleanup are explicit maintenance calls, never inserted into media processing.
Files are private atomic publications; a content digest binds bytes but is not
an authentication signature against someone who can rewrite both bytes and hash.

## Native interface changes

| Producer | New contract | Reader/caller obligation |
| --- | --- | --- |
| WorkerDiagnosticRecorder | `truecore.worker_diagnostic_result@2`; retains packet, Forge metadata and inline receipt; replaces `receipt_path` with a structured `receipt_ref`. No extra receipt file. | Use `resolve_receipt(reference)` on the recorder's host-owned Forge root to obtain and verify the native packet. The reference checks ID, sequence and packet digest. Registry advertises Forge-only writes. |
| StorageBudgetGuard | Routine success updates one current state. Calls within one second coalesce counters in memory; `health_receipt_path` is null and `health_receipt_publication` is `buffered` when not published. | Call `flush_health()` at the maintenance job's end. The returned decision still describes the current scan. Do not label buffered counts durable. A process crash can lose routine counters since the last flush. One guard owns a given maintenance scope; these counters are not a cross-process accounting ledger. |
| TrueMem dataset overview | Summary and run receipt use version 2. `run_receipt.json` contains the full `no_mutation_receipt` object. | Read the nested proof. The output map no longer advertises `no_mutation_receipt.json`. Dataset artifact hashes and source trails remain. |
| TrueMem resonance adapter | Result and run receipt use version 2. One run receipt embeds `source_receipt`, `no_mutation_receipt` and source files after execution. | Read nested proofs from `outputs.run_receipt`. Optional symbol/binary-readiness artifacts retain their own contracts. Source and output roots must not overlap. |
| CentralWriter | One atomic report file retains the original report fields at top level and embeds writer-owned `_publication` metadata (`truecore.writer_publication@2`) with receipt and report hash. | Existing facts-field readers still work. Use `read_publication(path)` for verified report/provenance. Result replaces the sidecar path with `receipt_ref` naming the `_publication.receipt` member. Neither file existence nor a facts report establishes enforcement authority. |
| InternalSelfLogger | Independent observation file per unchanged state/60-second interval, with an overwritten small current pointer. Repeated identical checks update count and last observation time; any material content change starts another record. | Read through `read_observation`; the default 60-second maximum age makes stale or future-dated observations `unknown_stale`. The system-trust sentinel uses this read. Work jobs do not own the independent observation proof. |
| PerformanceLogger | Standalone calls publish their own atomic receipt. An explicit `with logger.batch():` groups at most 256 samples for one algorithm/run into one terminal receipt. | Buffered calls return a null path and `receipt_publication=buffered`. After context exit, `last_publication` resolves the actual file. The batch retains counts, sums, maxima, fixed latency bins and optional-field missing counts. Exceptions publish a partial batch; no per-sample disk writes occur. |
| RollingRetentionManager | `truecore.retention_window_result@2` has one `job_receipt_path` and the native transaction result. | Supply exact `eligible_details`; no entries means no deletions. The old broad deletion helper is removed. Read health/window/verification inside transaction `context`, alongside actual outcomes. |

No compatibility sidecar is emitted merely to keep a retired path alive.
Previously published files are not removed or rewritten by migration.

## Finite metrics example

```python
logger = PerformanceLogger(host_owned_performance_root)
with logger.batch():
    logger.write_receipt(algorithm_id="profile", run_id=host_job_id,
                         input_size=10, duration_ms=measured_ms)
terminal = logger.last_publication
```

Latency bins have upper edges 1, 10, 100, 1000 and 10000 milliseconds, plus an
overflow bin. They are reporting bins, not claims about an acceptable media
deadline. Maxima retain isolated stalls. Memory-peak sums are sums of samples,
not total machine allocation. Absent GPU/energy values are counted as missing;
they do not become zero observations. Routine buffered metrics can be lost on
process death; they never supply native media proof or recovery authority.

## Exact retention admission and failure behavior

`admit_detail` is a host-side assertion that a selected object is closed,
inactive, unreferenced operational detail. It binds path, source job identity,
canonical recorded time, size, SHA-256, device/inode and modification identity.
It is not an automatic classifier of arbitrary JSON, binary or AV files.
Source/evidence ownership must already be known by the admitting owner.

`execute_details` accepts only that explicit set under declared managed roots,
outside protected roots and its own receipt root. It rejects parent traversal,
symlink paths, multi-link/nonregular files, conflicting transaction IDs and
invalid object state. Preserve/active markers and changed identities prevent
deletion. The rolling wrapper filters declared recorded time to its exact
half-open window; the caller owns selection of the permitted retention window.
Anomaly windows and failed Fusion verification preserve files.

Default execution budgets are 256 files, 32 MiB of admitted bytes and two
seconds; callers may select up to 30 seconds. The deadline is checked between
files, so filesystem I/O is not hard real-time. A single bounded file operation
can exceed it. Budget scans stop after 10,000 entries or 250 ms and report an
incomplete scan instead of calling a partial count healthy. Separate receipt
capacity defaults to 16 MiB, with 4 KiB reserved for a current pressure result.
That is an admission threshold for this maintenance callable, not an OS quota
on other writers. Existing incidents and recovery proof are not automatically
discarded when capacity is tight.

A durable pending record precedes irreversible work. The parent directory is
opened without following symlinks; the named target is captured under a private
quarantine name and its identity rechecked before unlink. A replaced target is
preserved rather than treated as the admitted object. Completed deletions and
an inflight operation are recorded separately. Publication failure retains
recovery state. Replaying an interrupted identity reports
`interrupted_outcome_unverified` and does not repeat deletion. A partial
quarantine may require operator reconciliation; there is no automatic crash
rollback or authorization to overwrite a concurrent writer's files. Managed
detail must remain owner-closed/immutable during maintenance; this is not an OS
sandbox against a hostile process with the same filesystem authority.

Terminal transaction existence does not mean every requested object was
deleted. Inspect status, skipped objects, unprocessed count and inflight state.
Protected, changed, timed-out or failed objects yield truthful partial outcomes.

## Qualification and limits

External acceptance and measurements are under:
`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/`.
Use `tests/run_receipt_component_regression.py OUTPUT_DIRECTORY`,
`tests/run_truecore_receipt_acceptance.py`, and
`tests/run_receipt_completion_graph.py NEW_OUTPUT_DIRECTORY`.
The external README records the repository and commands.

The component runner explicitly records four retired native test contracts and
their external replacements: sidecar-path existence, unadmitted budget deletion,
and two broad rolling-window deletion behaviors. It does not silently skip
failing current behavior or modify upstream tests. Replacement tests exercise
resolvable Forge proof and stricter eligibility/window/source protections.

The graph review covers an explicit current Python source set and invokes all
15 graph workers. Its scope cannot establish whole-repository absence, complete
reachability, permission dominance, Rust behavior, or test-coverage authority.
Recorded synthetic bookkeeping measurements are not live capture/generation
throughput qualification. No live logged AV or historical receipts are cleanup
targets in the acceptance run.
