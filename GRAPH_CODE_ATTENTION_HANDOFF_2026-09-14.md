# TrueSystems graph and code attention handoff

**Date:** 2026-09-14 (America/New_York)  
**Repository:** `/home/lamercey/TrueSystems-Alignment`  
**Branch inspected:** `alignment/truecore-boundary`  
**HEAD inspected:** `99ed0cf6a94a4ab584cf89eae6cfb3a88b1c0365`  
**Inspection mode:** read-only graph and exact-source review  
**Runtime/code changes made during inspection:** none  
**Dataset changes made during inspection:** none  
**Service changes made during inspection:** none

## Purpose

This file is the detailed continuation record for the repository-graph and code
attention audit. It records what the current graph proves, what exact source
inspection confirmed, which risks are dormant versus active, what the graph
cannot yet prove, and the ordered work required next.

This is a handoff, not capability authority. Under `AGENTS.md`, executable code
and passing tests for the exact path remain authoritative. A finding labeled
`STATIC_CANDIDATE` is not a vulnerability claim. A missing graph relationship
must remain explicit; it must not be filled with inference.

## Current safety state

No active network exposure was found for the examined legacy surfaces:

- no listener was found on ports `3220`, `8765`, `5000`, or `3219`;
- `truesystems-control-api.service` is inactive and not installed;
- no active `truesystems_api`, `truemem.ui_server`, or `truecore.app` process was
  found by the bounded process check.

Therefore the highest-severity findings below are **dormant source defects or
qualification blockers**, not evidence of a currently exposed service. Do not
start the affected paths until their boundaries are corrected and tested.

The worktree was clean before this handoff file was added. This handoff file is
the only intended repository change from the audit.

## Evidence inspected

### Verified repository map

Map directory:

`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/output/repository-map-20260914T104858Z`

Important map facts:

- schema: `truesystems_repository_map@1`
- snapshot ID:
  `8abbaed9f319789033a7dd9634adc8cb4f2333e8a42df59f19c88135446c9606`
- persistent symbols: `false`
- N-N-N meaning: `ownership-source_order-dependency`
- ownership radius: `2`
- source-order radius: `6`
- dependency radius: `3`
- channels collapsed: `false`
- control-flow authority: `NOT_IMPLEMENTED`
- data-flow authority: `EXACT_NAME_ACCESS_EVIDENCE_ONLY`

The build command is preserved in that directory's `RUN.txt`. Verification is
preserved in `verification.json`.

Map scale established by the completed run:

- 4,961 files
- 4,109 parsed source files
- 114,501 code objects
- 623,810 structural relationships
- 21,620,151 exact occurrences
- 45,983 uniquely resolved dependency relationships
- 76,766 ambiguous dependency relationships
- 163,191 unresolved dependency relationships

Runtime/project dependency resolution from the exact map:

| Scope | Unique | Ambiguous | Unresolved |
|---|---:|---:|---:|
| Runtime source | 5,678 | 7,297 | 17,007 |
| Project source | 255 | 324 | 1,558 |

These are relationship-resolution counts, not defect counts. External-library
calls, dynamic dispatch, aliases, wrappers, and unsupported languages can all
produce unresolved or ambiguous relationships.

### Registered graph-worker run

Worker results:

`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/output/repository-graph-workers-protected-20260914T110000Z`

Fifteen registered workers ran through the protected TrueCore/TrueMachine
worker boundary. The family returned:

- external-entrypoint candidates: 662 total
- filesystem-writer candidates: 1,033 total
- process-execution candidates: 343 total
- direct TrueMem references: 111 witnessed static locations
- agent-registration candidates: 304 total
- detached-subgraph candidates: 3,684 total, truncated at 2,000
- no-incoming-dependency candidates: 17,069 total, truncated
- duplicate-implementation candidates: 10,445 total, truncated
- seven workers correctly returning `NOT_IMPLEMENTED` because required graph
  authority does not exist yet

The registered worker result envelope and exact stderr captures remain in that
directory. They must be retained when the map is superseded so results remain
reproducible.

## Confirmed findings requiring attention

### P0 — graph views apply limits before scope selection

**State:** confirmed implementation defect in investigation views  
**Immediate danger:** no direct runtime danger; high risk of incomplete or
misleading audit results

`TrueMachine/src/truemachine/repository_views.py::_bounded` consumes the first
`limit` rows from the generated stream. Candidate generators attach a
`source_scope`, but the public `run_view` interface has no scope argument and no
scope filter before `_bounded`.

Consequences already visible in the results:

- research and test archaeology consume much of the 2,000-row result limit;
- live runtime/project findings can appear late and be excluded;
- `returned` and `truncated` describe the unscoped candidate universe;
- a truncated result cannot be called complete for runtime source;
- security workers can miss the exact candidates they were created to expose.

Required repair:

```text
requested view + authorized scope
  -> enumerate exact candidates
  -> classify source scope
  -> filter by scope before limiting
  -> deterministic sort
  -> apply result limit
  -> return unfiltered total, filtered total, returned count, truncation
```

The default for security qualification should be an explicitly declared scope,
not an implicit whole-repository mixture. Research material may remain
queryable, but it must not silently crowd runtime results out.

Acceptance requirements:

1. A fixture with more than `limit` research matches followed by one runtime
   match must still return the runtime match when runtime scope is requested.
2. Scope filtering must occur before truncation.
3. Identical inputs must return byte-identical ordering and receipts.
4. Counts must distinguish all matches, in-scope matches, and returned matches.
5. Unknown or unauthorized scopes must fail closed.
6. Rerun all fifteen registered workers after the repair.

### P0 — authoritative TrueMem interfaces still advertise raw questions

**State:** confirmed code/interface conflict  
**Immediate danger:** dormant, because no TrueMem UI listener was active  
**Correctness impact:** high

`TrueMem/src/truemem/operator_contract.py` still advertises:

- `query`: `--question` and `--top-k`;
- `batch`: a plain question file and `--top-k`;
- `speech`: question-shaped count-walk speech.

`TrueMem/src/truemem/ui_server.py` calls itself `TrueMemReadOnlyUI`, but exposes
POST `/api/ui/batch/run`. That endpoint:

- accepts caller-selected `questions_path`;
- accepts `top_k`;
- spawns `python -m truemem.cli batch`;
- uses `timeout=None`;
- has no request-body size ceiling;
- returns the command and progress log.

`TrueMem/src/truemem/engine/querying.py::direct_question_batch_baseline` creates
an output directory and writes a batch summary. Therefore the UI is not
read-only in behavior.

This conflicts with the governing evidence boundary:

```text
human request
  -> operator derives explicit evidence obligations
  -> TrueMem receives a structured EvidenceNeed or bounded location request
  -> TrueMem returns locations, relationships, coordinates, citations, and receipts
  -> operator inspects evidence and forms the supported answer
```

TrueMem must not receive an answer-shaped benchmark question as a retrieval
command. It must not decide the factual answer. Co-occurrence, same paragraph,
or same block must not become complete relationship evidence without witnessed
subject ownership.

Required disposition:

- identify whether these routes are historical compatibility code or intended
  current runtime;
- keep them disabled until that classification is made;
- remove them from current generated help if they are not authoritative;
- replace active query entrypoints with the structured evidence/location
  contract;
- do not silently wrap the old question path and rename it EvidenceNeed.

Acceptance requirements:

1. A raw `question` field is rejected at the retrieval boundary.
2. Caller-supplied `top_k` cannot substitute for direct anchor occurrence and
   relationship traversal where the contract forbids it.
3. Output contains locations/relationships and `answer: null`.
4. Exact subject ownership, polarity, quantity, and qualifiers remain separate.
5. No read-only surface can create output directories or spawn batch work.
6. Request bodies and subprocess durations have deterministic bounds.

### P0 — legacy control API routes around TrueCore

**State:** confirmed architectural bypass in dormant code  
**Immediate danger:** not active; service absent and no listener found

`control-api/src/truesystems_api/server.py::OPERATIONS` routes directly to
TrueMachine, TrueMem, LocalMemoryChat, and ChatChain callables. The HTTP layer
does not pass requests through the qualified TrueCore operator boundary.

Caller-controlled values include:

- TrueMachine `state_dir`;
- TrueMem `runtime_root` and `dataset_id`;
- LocalMemoryChat `runtime_root`;
- ChatChain database path.

Those are host/resource bindings, not ordinary model-supplied arguments. The
server is loopback-restricted, which is useful, but loopback is not authority.
The body reader also accepts the advertised `Content-Length` without a maximum.

The TrueMem query route in this API correctly rejects `question` and `top_k`;
that narrower behavior should not be confused with overall boundary safety.
Direct component routing and caller-supplied host roots remain the problem.

Required disposition:

- do not enable the old service in its current form;
- retire it or convert it into a thin TrueCore client;
- bind roots, datasets, databases, grants, budgets, and executable identities on
  the host side;
- expose only registered bounded operation IDs and caller-authorized fields;
- return self-describing correction packets for missing/invalid arguments;
- require explicit approval gates for destructive or externally consequential
  operations.

### P0 — TrueCore shun state can claim enforcement that failed

**State:** confirmed correctness defect  
**Immediate danger:** dormant; no active TrueCore service was found

`TrueCore/truecore/control/shun.py` invokes Windows `netsh` firewall commands.
On the current Linux host those operations cannot provide the claimed
enforcement.

More importantly, state transitions are unsafe independently of platform:

- `shun_ip` stores the IP and returns `ok: true` even when firewall creation
  returns false;
- `unshun_ip` removes the in-memory record before firewall removal is verified;
- `purge_all_shun_rules` clears all in-memory state even when rule removal
  failures were counted.

Required state machine:

```text
REQUESTED
  -> APPLYING
  -> APPLIED
  -> VERIFIED

or

REQUESTED/APPLYING
  -> FAILED
  -> ROLLBACK_REQUIRED or CLEAN
```

TrueCore must never return `SHUNNED` unless the operating-system backend proves
the rule is active. Failed removal must retain enough authoritative state for
retry and investigation.

Acceptance requirements must use isolated firewall fixtures unless the human
separately authorizes live firewall modification.

### P1 — importing `truecore.app` starts runtime activity

**State:** confirmed lifecycle/side-effect defect

`TrueCore/truecore/app.py` ends with module-level `app = create_app()`.
`create_app()` starts the Reaper and control bus and executes `db.create_all()`.
Therefore importing this module can start background activity and write state.

Required separation:

```text
import definitions
  -> no background threads
  -> no database creation
  -> no runtime mutation

explicit create/build
  -> construct dependencies

explicit start
  -> start reaper/control bus/listeners
  -> issue lifecycle receipt
```

This is required both for safe inspection and for tests that claim to exercise
only construction or schema behavior.

### P1 — important non-Python runtime surfaces are structurally opaque

**State:** confirmed mapper limitation, not a defect claim about those files

The map reports `CODE_STRUCTURE_NOT_IMPLEMENTED` for important files including:

- `TrueComputer/src/main.rs`;
- `TrueCore/frontdoor/src/main.rs`;
- TrueVision native Rust capture/runtime binaries;
- selected TrueVision UI assets;
- Clearbox QML, JavaScript, CSS, and HTML surfaces.

All 68 syntax-rejected Python files observed in the earlier audit were under
`research_reference_not_runtime`; they are preserved archaeology, not current
runtime failures.

Rust mapping is the first parser priority because TrueComputer and the TrueCore
front door are high-authority surfaces. Whole-system security claims are not
permitted while those paths are opaque.

### P1 — control flow, value flow, tests, policy, and documentation authority are missing

**State:** explicitly and correctly `NOT_IMPLEMENTED`

The current graph proves ownership, source order, exact name access, and static
dependency relationships with explicit resolution states. It does not prove:

- runtime control flow;
- caller argument to privileged sink value flow;
- permission/approval dominance over a sink;
- test-to-code coverage;
- security-role ownership;
- expected-route policy compliance;
- documentation-claim to implementation relationships.

Accordingly, these registered workers correctly refuse to answer:

- TrueCore bypass candidates;
- security-configuration writers;
- canonical-evidence writers;
- untested privileged sinks;
- unresolved privileged reachability;
- documentation claims without code;
- code without documentation.

Do not replace these `NOT_IMPLEMENTED` results with name matching. Add the
missing relationship authority, then allow the same workers to produce stronger
grades through their existing output contract.

### P1 — registered worker subprocess inherits ambient `PYTHONPATH`

**State:** static investigation candidate; not a proven exploit

`TrueCore/truecore/registered_worker_bridge.py` builds two intended import roots
but appends any inherited `PYTHONPATH`. That expands child import resolution
beyond the declared TrueCore/TrueMachine boundary.

The bridge already provides useful controls:

- fixed runner and catalog;
- manifest/resource hashing before and after execution;
- bounded `limit`;
- subprocess timeout;
- result-schema and worker-identity validation.

The production qualification should construct a minimal environment rather
than inheriting import/executable configuration. Test import shadowing from a
host-controlled path and require deterministic rejection or isolation.

The general agent runner remains a development runner, not a production
sandbox. It rejects manifests requiring sandboxing, but accepted work otherwise
runs with host process authority. Never expose it directly to an untrusted model
or network caller.

## Secondary findings

### Direct TrueMem references

The graph found 41 runtime/project direct TrueMem references. Most are internal
TrueMem imports. The control API references are the boundary concern described
above.

TrueVision Intake directly references TrueMem from DocuFilm, code-glyph,
structural-binding, and tabular-intake paths. These may be intended intake
integration. The existing graph cannot call them bypasses because expected-route
policy and control/data flow are missing. Review them against the component
ownership contract before changing them.

### Persistent-symbol-era drift

Some TrueVision Intake/DocuFilm-to-TrueMem code still carries persistent
`symbol` fields and symbol lookup concepts. This conflicts with the newer
symbol-free repository-map work, but the repository's current `AGENTS.md` still
describes TrueMem as owning dataset symbols. Resolve the governing architecture
before editing code or documentation. Do not perform a partial vocabulary
replacement.

Temporary numeric GPU execution IDs, if used, must remain adapter-local,
generation-bound, and absent from persistent evidence identity.

### Duplicate implementations

Most returned duplicate groups are research/test archaeology or small utility
functions. The more meaningful runtime maintenance candidate is repeated
`ArtifactState` logic in TrueMem evidence modules; receipt/state definitions can
diverge even when their starting source was identical.

Other repeated helpers (`utc_now`, hash helpers, JSON writers) are lower
priority. Consolidate only after callers and failure semantics are covered by
tests. Similar names alone do not prove duplicate authority.

### Mapper false positive already explained

`LocalMemoryChat/local_memory_chat/__init__.py` dynamically extends its package
path to the `src` implementation. The static mapper cannot establish that
dynamic package connection and may classify the shim as detached. This is a
mapper limitation, not evidence that LocalMemoryChat is orphaned.

### Misleading name that does not mutate source

`normalize_anchor()` currently returns its supplied value unchanged. The name
is inconsistent with the no-normalization law, but exact source inspection did
not find spelling correction or source rewriting in that function. Do not
report normalization as occurring merely from the function name.

## Required work order

The next operator should use this order so later findings are not built on an
incomplete graph view:

1. Add scope as a validated argument to repository views and filter before
   limiting.
2. Add external acceptance fixtures proving scope-before-limit behavior,
   deterministic ordering, counts, and fail-closed scope handling.
3. Rerun the complete repository map only if code affecting map semantics has
   changed; otherwise rerun all fifteen workers against the existing verified
   snapshot.
4. Reconcile TrueMem's raw-question/UI paths against the current EvidenceNeed
   and location-only contract. Keep dormant paths disabled during review.
5. Keep the legacy control API disabled; design any replacement exclusively as
   a TrueCore bounded-operation client with host-owned resource binding.
6. Correct and externally test the TrueCore shun state machine using isolated
   Linux backend fixtures.
7. Separate TrueCore construction/import from explicit startup and prove a
   side-effect-free import.
8. Add Rust structural mapping, beginning with TrueComputer and TrueCore
   frontdoor. Preserve unsupported-language states until verified.
9. Add control-flow and value-flow authority sufficient to track caller-bound
   inputs into process/filesystem/security sinks.
10. Add permission, approval, expected-route, security-role, test, and
    documentation relationships as separate graph channels.
11. Harden the registered-worker subprocess environment and qualify the
    development runner versus any future sandboxed runner.
12. Review TrueVision Intake-to-TrueMem ownership and persistent-symbol-era
    drift only after the governing identity contract is reconciled.
13. Address duplicated receipt/state definitions after higher-authority
    boundaries are stable.

## External test placement required

Under the global test agreement, all new user-authored tests and their output
belong outside this source repository:

```text
/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/
/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/output/
```

The external test directory must retain a README naming this canonical
repository path and describing test execution. New outputs must be timestamped
in UTC and must not overwrite the existing repository map or worker run.

Repository-native tests may be executed in place, but logs and generated
artifacts should be redirected externally where supported.

## First repair acceptance matrix

| Area | Required positive proof | Required negative proof |
|---|---|---|
| View scoping | requested runtime findings survive research overflow | research rows cannot consume runtime limit |
| TrueMem boundary | structured need returns locations/relationships | raw question cannot enter retrieval |
| Read-only UI | GET reads bounded existing evidence | no POST, subprocess, or output creation |
| TrueCore routing | host binds resources and grants | caller cannot supply roots, grants, executables, or budgets |
| Shun state | OS rule is applied and independently verified | failed backend cannot return `SHUNNED` |
| TrueCore lifecycle | explicit start produces receipt | import alone creates no DB/thread/service |
| Worker environment | imports resolve only from declared roots | ambient path cannot shadow a dependency |
| Rust graphing | exact spans and relationships round-trip | unsupported syntax remains unpromoted |
| Data/control flow | exact request value reaches exact sink with witnessed path | textual proximity cannot become reachability |

## Commands used for the final read-only verification

The final audit used bounded reads only, including:

```text
git status --short --branch
git log -1 --format=...
sed / nl over the exact files named above
ss -ltnp filtered to ports 3220, 8765, 5000, and 3219
systemctl --user is-active/status truesystems-control-api.service
pgrep filtered to the named TrueSystems services
streaming JSONL summaries over code_objects and resolved dependencies
```

No service was started, no process was killed, no firewall was changed, no
dataset was opened for mutation, and no generated map artifact was altered.

## Stop conditions for the next operator

Stop rather than infer if any of the following occurs:

- the repository HEAD differs and the changed files affect map semantics;
- the existing map's source hashes no longer match the source under review;
- a requested security conclusion requires a `NOT_IMPLEMENTED` relationship;
- a repair would activate the dormant control API or TrueMem UI;
- a test would alter live firewall, canonical evidence, protected code, or user
  data without explicit authorization;
- an apparent bypass is based only on a name, import, or nearby source text;
- a compatibility path's authoritative/current status cannot be established.

## Resume point

Resume with the **scope-before-limit repair in TrueMachine repository views and
its external acceptance tests**. That correction is first because every later
graph-agent investigation depends on complete, scope-correct candidate packets.
After it passes, rerun all registered graph workers and compare their runtime
results against the preserved `20260914T110000Z` baseline before investigating
new source candidates.
