# TrueSystems Governing TODO — 2026-09-13

Status: current work order, not capability authority
Implementation authority: code plus passing external tests
Repository: `/home/lamercey/TrueSystems-Alignment`
Starting commit: `d6a030d786b39a0ed61afb350e587f948ece09a5`

## Purpose

Treat TrueSystems as one machine with specialized authorities. Before creating
or changing a subsystem, identify the existing owner, witnessed implementation,
tests, contracts, authority, and exact missing piece. A document describes state
or intent; it does not create capability.

```text
human or model
-> TrueCore request and authority
-> registered capability or worker
-> owning TrueSystems component
-> witnessed result and receipt
-> operator interpretation
```

## Current proven checkpoint

- TrueCore exposes six read-only model operations: `help.list`, `help.query`,
  `sensory.inspect`, `source.classify`, `media.describe`, and `worker.invoke`.
- Fifteen repository workers are registered and model-bridge eligible when the
  host grants them and binds a verified TrueMachine repository map.
- Eight repository views return witnessed/static investigation candidates.
- Seven repository views return `NOT_IMPLEMENTED` and name their missing graph
  authorities.
- TrueMachine owns Linux observation and the source-grounded repository map.
- Repository-map N-N-N means ownership, source order, and dependency. It does
  not mean control flow or data flow.
- Repository-map workers return locations and relationships, not answers or
  vulnerability judgments.
- `truecore.worker_result@1` is established for the registered worker family;
  it is not yet universal across every TrueSystems tool.
- TrueComputer has four bounded desktop actions but is not yet connected to the
  TrueCore model boundary or a cryptographic human-approval object.
- General local housekeeping operations are not yet implemented in TrueMachine.
- TruePlug's source ancestor is the detached ClearboxPluginRunner. It is a
  standalone development host but currently shares one Python process with its
  plugins and is not sandboxed.
- The current ClearboxPluginRunner working state, four distinct historical
  Forest HTML tools, and the TruePlug build input are preserved under
  `research_reference_not_runtime/TruePlug/`. That tree is staged, byte-verified,
  non-runtime archaeology; it is not the future TruePlug implementation.
- The separate TrueSystems Delving Core has five host-qualified native location
  methods and a deterministic public packet boundary. Twenty-five cataloged
  methods remain specifications. TrueCore has zero runnable Delving capabilities;
  typed value-source/receipt binding is the next blocked gate.

## Governing boundaries

### TrueCore

Owns capability registration, grants, approvals, model-facing requests,
production admission, runners, and common result validation. A model never
supplies raw commands, module names, manifests, grants, approvals, or arbitrary
filesystem paths.

### TrueMachine

Owns witnessed machine state, bounded local machine operations, repository
structure, and operation receipts. It does not decide intent or factual meaning.

### TrueComputer

Owns bounded desktop actions with exact target preconditions and observable
postconditions. Its `--execute` switch is not human approval.

### TrueMem and delving

Own evidence locations, occurrences, relations, coordinates, and provenance.
The operator converts questions into evidence needs; the locator does not answer
benchmark questions. Experimental delving results remain distinct from features
integrated into this repository's current model boundary.

### TrueVision, TrueAudio, and TrueSpeech

Own their respective witnessed state and candidate outputs. Their raw CLIs are
not model tools. Each operation must be independently registered and qualified.

### TruePlug

Owns detached plugin creation, development, mounting, fixture execution,
inspection, testing, packaging, and qualification-for-submission. It does not
grant production authority, self-register plugins, or execute production machine
operations. TrueCore alone admits a candidate into production.

Current TruePlug security grade:

```text
DETACHED_FROM_MAIN_HOST
SHARED_PROCESS_WITH_PLUGIN
NOT_SANDBOXED
UNTRUSTED_PLUGIN_EXECUTION_NOT_AUTHORIZED
```

### Canonical evidence

Canonical evidence and derived projections are distinct. Generic housekeeping
workers may not alter admitted datasets, frozen manifests, immutable receipts,
security policy, or TrueCore authority configuration. Those require dedicated
admission or supersession workflows.

## Worker result law

New workers use `truecore.worker_result@1` unless a formally tested successor is
approved. Native results may be carried inside the envelope without being
reinterpreted into stronger evidence.

Every mutating operation receipt must identify:

```text
principal
worker_id
operation
resource_class
resolved source and destination
pre-state and post-state hashes where applicable
grant_id
approval_id where required
start and completion timestamps
execution status
verification status
rollback or recovery information
```

## Approval law

Destructive and privileged operations require explicit TrueCore approval. An
approval binds one principal, operation, resolved target set, exact argument set,
dry-run state, expiration, and single-use nonce. Any change invalidates it.

No approval authorizes adjacent work. Arbitrary shell text is not a housekeeping
operation.

## Day-by-day gated lineup

Days are ordered engineering gates, not calendar promises. Work stops at a failed
gate and preserves the failure evidence.

### Day 1 — Synchronize truth and qualify read-only navigation

Needs:

- Commit the corrected local tool catalog and this governing TODO.
- Preserve the historical work-order receipt unchanged.
- Mark repository-worker generation 1 complete in a new status receipt.
- Freeze schemas for `fs.list`, `fs.find`, `fs.read_metadata`, `fs.hash`,
  `fs.disk_usage`, `fs.duplicate_scan`, `process.list`, `service.status`,
  `package.inventory`, `device.inventory`, `mount.inspect`, `network.status`,
  `log.query`, and `repo.status`.
- Implement the smallest read-only TrueMachine primitives.
- Register their TrueCore workers and generate code-derived help.

Exit gate:

- Every operation is bounded by a host resource, time/result budget, and strict
  schema; attempts to supply paths or commands through the model fail closed.
- External tests verify success, missing prerequisites, invalid arguments,
  changed resources, truncation, and deterministic receipts.

### Day 2 — Common receipts and reversible filesystem work

Needs:

- Freeze the common operation receipt.
- Implement `fs.mkdir`, `fs.write_new`, `fs.copy`, `fs.move`, `fs.rename`,
  `archive.create`, and `archive.extract_staging`.
- Default to create-new and collision refusal.
- Preserve pre/post hashes and recovery information.

Exit gate:

- All success and partial-failure paths are verified with isolated fixtures.
- Archive extraction rejects traversal, links, special files, and collisions
  outside its declared staging contract.

### Day 3 — Approval runtime and destructive fixture qualification

Needs:

- Implement the operation-bound TrueCore approval object.
- Implement `fs.delete` first against external disposable fixtures only.
- Test missing, wrong, expired, replayed, changed-target, symlink, directory,
  protected-resource, and successful approvals.
- Connect one existing TrueComputer action through the same grant/approval
  vocabulary without claiming application success.

Exit gate:

- No destructive action begins without a matching single-use approval.
- Execution and postcondition receipts remain distinct.
- No personal, canonical, or live system data is used for destructive tests.

### Day 4 — Control-flow graph authority

Needs:

- Select one parser-supported language and a bounded repository fixture.
- Add basic blocks, branch edges, loop edges, return edges, and exception edges
  using a qualified parser/compiler authority.
- Preserve control-flow edges separately from source order and calls.

Exit gate:

- Exact source locations and parser state back every edge.
- Unsupported or damaged source returns an explicit unavailable state.
- No heuristic line-order edge is promoted to control flow.

### Day 5 — Data flow, tests, documentation, and security roles

Needs:

- Add bounded def-use and argument-binding relationships.
- Add test-target relationships based on witnessed test collection/execution.
- Add documentation-claim records without treating prose as implementation.
- Define expected TrueCore routes, privileged sinks, canonical evidence objects,
  and security configuration objects through explicit registries.
- Re-run the seven `NOT_IMPLEMENTED` workers; promote only the views whose exact
  prerequisites now exist.

Exit gate:

- Each relationship channel remains independent.
- Candidate, witnessed static, and witnessed runtime states remain distinct.
- No worker infers vulnerability, reachability, or absence from naming alone.

### Day 6 — TruePlug custody and reproducible baseline

Needs:

- Preserve the completed, byte-verified import of the current working state and
  the separately identified committed base without modifying or deleting the
  dirty CompuCog worktree.
- Inventory its 501 tracked files, imports, plugin families, routes, mock host,
  fixtures, change detector, promotion checks, and tests.
- Reproduce discovery, mount, manifest, health, fixture, and promotion behavior
  in an external test environment.
- Classify each mechanism as `RETAIN`, `REFIT`, `REPLACE`,
  `RESEARCH_REFERENCE`, or `REJECT`.

Exit gate:

- The baseline is replayable and its limitations are explicit.
- No source state is silently chosen or combined.
- No untrusted plugin is executed.

Current state:

- Source custody and the no-runtime-reference test pass.
- Behavioral reproduction, mechanism classification, and trusted-fixture
  execution have not started.

### TruePlug refactor law

The imported `ClearboxPluginRunner` is frozen archaeology. Do not refactor it in
place and do not import it from TrueSystems code. Build the replacement as a
standalone detached development repository with no production TrueSystems
runtime dependency.

The refactor must:

- derive a minimal runner contract from witnessed runner behavior before coding;
- retain only separately qualified discovery, manifest, fixture, inspection,
  development UI, packaging, and submission behaviors;
- remove same-process plugin import and global `sys.path` mutation;
- run one plugin per bounded process and disposable workspace;
- provide fake filesystem, network, database, host API, application, and
  TrueCore/TrueMachine fixtures rather than canonical system access;
- replace MD5/Python-only change checks with complete SHA-256 content manifests;
- replace aggregate `passed >= 6` promotion with named mandatory gates;
- generate help only from actual callable schemas and test every instruction;
- emit an immutable candidate and qualification packet for separate TrueCore
  review, never self-register or self-promote;
- preserve the ability to unplug the entire development center without changing
  any TrueSystems component.

Legacy plugin families, WinUtil material, Forest bridges, GPU hooks, social/UI
experiments, and Wolf components are not automatically retained. Each is
`RESEARCH_REFERENCE` until its exact operation, effects, dependencies, and
tests justify `RETAIN`, `REFIT`, `REPLACE`, or `REJECT`.

### Day 7 — TruePlug containment

Needs:

- Establish one process per plugin.
- Add disposable per-plugin filesystem roots, restricted environment, bounded
  network policy, CPU/RAM/time/output limits, captured logs, and termination.
- Replace Python-only MD5 change detection with a complete SHA-256 content
  manifest covering code, manifests, templates, configuration, and resources.
- Provide behavioral fixtures for denied and partial TrueSystems operations.

Exit gate:

- A deliberately failing trusted test plugin cannot modify sibling workspaces,
  inherit undeclared secrets, exceed resource limits, or kill the supervisor.
- Failure preserves logs and receipts and destroys disposable state.

### Day 8 — TruePlug factory and mandatory promotion

Needs:

- Add bounded workspace creation, plugin-shape selection, manifest/package
  skeletons, route/schema skeletons, tests, and immutable candidate packaging.
- Replace aggregate promotion scoring with named mandatory gates.
- Record vendor documentation, surface witness, invocation witness, output
  witness, postcondition witness, replay, filesystem effects, network effects,
  and unresolved facts as separate dimensions.
- Generate a TrueCore submission packet; do not self-register.

Exit gate:

- One mandatory failure always produces `NOT_PROMOTABLE`.
- A complete candidate can become `TRUECORE_SUBMISSION_ELIGIBLE`, never
  self-declared production-qualified.

### Day 9 — First third-party adapter qualification

Needs:

- Choose one reversible, locally available, low-risk application surface.
- Build its adapter entirely in TruePlug.
- Exercise success, denial, missing prerequisite, partial failure, version drift,
  retry, and postcondition behavior.
- Submit the immutable candidate to TrueCore's admission review.

Exit gate:

- Production execution occurs only after TrueCore admission and only through the
  owning TrueSystems operation authority.
- Removing the adapter leaves the rest of TrueSystems functional.

### Day 10 — Human-facing consumption, not new authority

Needs:

- Expose the qualified navigation catalog inexpensively to the human and model.
- Let Kali Ka consume common TrueSystems results independent of the selected LLM.
- Let Smokey indicate only exact system-established locations.
- Keep both surfaces outside permission, evidence, and execution authority.

Exit gate:

- Changing the underlying model does not change system identity or grants.
- No exact target means no confident pointer indication.

## Independent TrueVision backlog

TrueVision's existing TODO remains independently governed by
`TrueVision/docs/TRUEVISION_TODO_COMBINED_STATUS.md` and `TrueVision/TODO.md`.
It is not silently pulled into this ten-day integration sequence. Only the
specific TrueVision contract needed by an admitted operation or TruePlug fixture
enters this work order.

## Stop conditions

Stop and preserve evidence when:

```text
authority owner is unresolved
canonical and derived state cannot be separated
target identity is ambiguous
required approval does not match
source or manifest hash changes during operation
an operation escapes its resource boundary
an external test contradicts the claimed capability
a missing graph relationship would require inference
TruePlug containment cannot prevent host effects
```

## Completion law

```text
inspect existing machinery
-> classify the work
-> implement the smallest system-consistent change
-> test externally
-> preserve receipts and failures
-> update current-state documentation
```

Passing prose, manifests, aggregate scores, and fluent model output do not qualify
a capability.
