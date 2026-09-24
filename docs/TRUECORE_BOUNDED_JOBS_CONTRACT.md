# TrueCore finite admitted jobs

The model-facing operation is `job.invoke` through `OperatorBoundary` and the
existing JSONL `ModelHost`. The only caller argument is `job_id`. Host
configuration supplies the exact plan path/hash, matching admission digest and
external output root. No model request supplies a patch, command, root, grant,
approval, executable, module or output destination.

This is a local application boundary, not an OS sandbox or the final secured
mutation/protection service. The operator authors implementation changes and
tests; TrueCore never invents them. The operator may bootstrap missing workers,
qualify them externally, and then submit admitted jobs to those workers. A
source-file patch verifies exact bytes, not semantics; acceptance is a separate
registered step.

`truecore.bounded_job_plan@1` binds the preserved request digest, job identity,
implementation files and finite ordered steps. Steps may declare `depends_on`
using only earlier step IDs. If omitted, all preceding steps are dependencies.
An incomplete dependency prevents dispatch. Explicit independent steps may
continue. A failed/refused worker stops subsequent dispatch. Unsupported worker
identities stay `NOT_IMPLEMENTED`; no nearby operation is substituted.

The registered family is generated from
`TrueCore/truecore/live_agents/AGENTS/catalog/bounded_job_worker_source.csv`:

- `job_patch_files`: preserve all pre-state, check all exact target preconditions,
  apply only the admitted UTF-8 bytes, then check post-state. No deletion or
  automatic overwrite recovery. Parent escapes, symlink targets, changed files,
  unsupported target modes and budget overruns are refused. Multi-file changes
  are not an atomic filesystem transaction; partial changes preserve pre-state
  and stop for inspection.
- `job_acceptance_run`: execute one hash-bound external Python script with
  pinned source inputs, a timeout and bounded combined output. The script is
  trusted host code; this is not a sandbox. Its receipt proves only what the
  script executed. It is not proof that a different user operation traversed
  its authorized production path or produced the requested effect.
- `job_history_readiness`: report missing historical evidence prerequisites.
  Readiness is not analysis or causal authority.
- `job_history_order`: delegate admitted TrueMem block projection to TrueMem;
  preserve message speaker and explicit conversation-local order. Quotation
  ownership, interpretation, implementation outcomes and causal responsibility
  remain unavailable unless separately witnessed and qualified.
- `job_graph_review`: invoke all fifteen registered graph workers and publish
  one canonical bundle. A preserved map stays labeled historical. Current-file
  mismatches, missing sources, lack of new-file discovery and unsupported graph
  authority remain explicit.

Workers use the existing validated manifest/runner/result gate and leave it as
`truecore.worker_result@1`. The finite job returns one private
`truecore.bounded_job_receipt@1` inside that envelope. It includes actual worker
results and explicit unexecuted steps. Independent inspection rechecks result
hashes and referenced artifact hashes. Normal model output contains only the
job identity, receipt commitment and compact step status/reason fields.

The output directory reserves one job identity before dispatch. A terminal
receipt can be inspected/replayed without executing the steps again. An
interrupted directory without a terminal receipt is refused for automatic
reexecution. The private progress record and pre-state are recovery evidence;
they do not establish which interrupted operation completed. Fully automated
crash reconciliation and protection against a hostile same-user process remain
unqualified. Content hashes are not signatures.

Normal completed jobs retain one terminal receipt, required domain artifacts,
external test output and required pre-state. A bounded process failure may add
an incident log. Progress is removed only after terminal publication. No service
is enabled, no live media is captured, and no historical receipt is deleted by
registering or describing this family.

The self-describing correction implemented for `job.invoke` accepts only the
declared `job_id` field. Unknown job identities are authorization failures. This
does not implement the system-wide correction/protection placeholders for all
other operations.

External acceptance resides in
`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/`:
`test_truecore_bounded_jobs.py`, `test_history_projection.py`,
`test_av_receipt_jobs.py`, and `run_truecore_receipt_acceptance.py`.
