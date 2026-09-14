# TrueSystems day reconciliation — 2026-09-13

Status: evidence-backed progress report, not capability authority
Authority: executable code and passing tests for each named path
Alignment branch: `alignment/truecore-boundary`

## Executive judgment

Today drifted severely in scope but not catastrophically in verified system
state. Work moved through model education, evidence retrieval, TrueVision,
storage concerns, documentation recovery, repository mapping, worker creation,
the model bridge, and TruePlug. That made the day difficult to follow and left
several threads unfinished.

The containment strategy worked: the proven Alignment changes are committed in
small generations, generated tests and large maps are external, the Delving
Core is a separate clean repository, model training was not promoted, and the
PluginRunner is staged only as non-runtime archaeology. No verified evidence in
this reconciliation shows loss of canonical TrueSystems source or a new
production authority bypass.

## Severity scale

- **S0 — critical:** verified data loss, authority bypass, or corrupted canonical
  generation.
- **S1 — high:** architecture or safety risk that blocks promotion.
- **S2 — medium:** incomplete integration or evidence that can mislead status.
- **S3 — low:** documentation, packaging, or efficiency debt with a bounded
  workaround.

## Where the work drifted

| Drift | Severity | Effect | Current disposition |
| --- | --- | --- | --- |
| Conventional 3.322B-model education began before all TrueSystems operation contracts were aligned. | S1 schedule/architecture; no verified Alignment corruption | Consumed attention and produced a model experiment that could not establish the intended deterministic system learning. | Training is parked and must not become system authority. Its artifacts remain experimental evidence. |
| The evidence task repeatedly slid between benchmark answering, retrieval scoring, and location finding. | S1 conceptual | A retrieval system could have been rewarded for benchmark-shaped answers rather than witnessed relationships. | Corrected in Delving: raw claims/questions/answers/Top-K are absent from requests; the system returns locations and measurements only. |
| Symbol, string, anchor, and GPU execution identity were repeatedly treated as one decision. | S2 | Risked replacing persistent identity and storage while testing only transport performance. | Current law separates exact persistent anchors/addresses from disposable execution IDs. No Alignment-wide storage migration is authorized. |
| TrueVision live capture, blur, logging transport, and disk layout became mixed with model/evidence work. | S1 operational; S2 project management | Raised destructive-storage risk and obscured which capture behaviors were actually qualified. | TrueVision remains an independent backlog. No claim here promotes live capture or disk reconfiguration. |
| Full repository mapping looked like a detour until it became the prerequisite for code-derived workers. | S3 beneficial detour | Produced a very large diagnostic map and exposed storage inefficiency. | Retained as a verified source-grounded baseline; compact transport remains future work. |
| Security-worker names initially risked sounding stronger than available graph authority. | S1 if promoted; contained | Static names/proximity could have been mislabeled as vulnerabilities or bypasses. | Eight views return witnessed/static candidates; seven return explicit `NOT_IMPLEMENTED`. |
| TruePlug discussion risked treating an old same-process runner as a ready sandbox or production plugin authority. | S1 if executed; presently contained | Untrusted plugin code could share process state, paths, secrets, or host effects. | Runner is byte-preserved under `research_reference_not_runtime`; it has no runtime reference or registration. Refactor is explicitly future detached work. |
| Documentation and plan creation outran the final commit. | S2 | Current truth exists but is not yet one immutable Git checkpoint. | Governing TODO, tool catalog, reconciliation, receipt update, and TruePlug import require a clean commit sequence. |

## Completed and verified today

### Alignment repository

1. **Phone-document custody:** seven unique Markdown files representing ten
   qualifying phone records were byte-verified, deduplicated, and committed as
   non-authoritative historical evidence (`810fea2`).
2. **TrueCog audit:** the code/document audit classified 38 claims and reproduced
   five discrepancies externally. It established that TrueCog is an owner-facing
   assembled role, not a discovered standalone implementation.
3. **Full repository map:** 4,407 files, 109,336 code objects, 322,684 structural
   relationships, 274,603 resolved dependency relationships, and 921,311 exact
   name accesses were mapped with exact source custody. The first failed run was
   preserved; the repaired run passed source, byte-span, endpoint, and receipt
   verification.
4. **TrueMachine mapping authority:** the repository mapper and bounded views
   were integrated and committed (`f182dfd`, `3953e6a`).
5. **TrueCore worker system:** `truecore.worker_result@1`, manifest-derived skill
   indexing, the repository-map worker, and fifteen graph workers were committed
   (`0ddd516`, `3953e6a`).
6. **Model-to-worker bridge:** the read-only model-shaped request path through
   TrueCore to host-bound TrueMachine maps was implemented and committed
   (`d6a030d`). It rejects model paths, modules, commands, ungranted workers, and
   changed map manifests.
7. **Local navigation catalog and governing TODO:** both were produced and their
   external checks pass. They remain uncommitted at this checkpoint.
8. **TruePlug custody:** 480 current working-state runner files, four distinct
   historical HTML tools, the build specification, and the tail record are
   staged with full hashes. External acceptance proves no TrueCore, TrueMachine,
   or control-API reference. The original dirty CompuCog tree remains untouched.

### Separate Delving Core

1. Thirty method contracts were frozen; five are implemented as a contained
   C++20 host calculator: exact occurrence locate, signed 6-1-6 projection,
   recenter/continue, ownership path, and witness descent.
2. Wrong-subject relationship takeover is rejected in the MDA5/RIG-I fixture.
3. The five methods serialize deterministic reasoning-direction, location, and
   receipt packets with cross-process replay and cryptographic commitments.
4. The fresh 30-case SciFact experiment used confirmation needs rather than raw
   questions or claims and produced locations/relationships only. It found qrel
   overlap in exact-subject locations for 14/30, produced 14 operator conclusions,
   and refused 16. Same-sentence overlap was 0/30, so this is diagnostic evidence,
   not a retrieval-quality victory.
5. Negative TrueCore authorization passed. The five methods remain unregistered
   and unrunnable because typed value-source/receipt argument binding is absent.

## Not done

| Missing work | Severity | Required next proof |
| --- | --- | --- |
| Commit the staged TruePlug custody import and uncommitted governing documents without mixing unrelated changes. | S2 | Clean commit sequence, post-commit test rerun, hashes, and status receipt. |
| Implement Day 1 bounded read-only TrueMachine primitives and TrueCore workers. | S1 for local-model usefulness | Host-bound schemas, result/time budgets, missing/changed-resource tests, code-derived help. |
| Repair the 38 TrueCog documentation/code differences. | S1 for claims; S2 for runtime | Fix one independently tested cluster at a time; do not rewrite code merely to satisfy prose. |
| Compact the 15.69 GB repository map. | S2 operational | Exact location, relationship, channel, and receipt parity against the verbose baseline. |
| Add real control flow, data flow, test-target, documentation-claim, route-policy, security-role, privileged-sink, and canonical-object relationships. | S1 for security conclusions | Parser/runtime-backed independent channels; rerun the seven `NOT_IMPLEMENTED` workers. |
| Complete Delving argument binding and TrueCore admission. | S1 authority gate | Typed value-source/receipt envelope, negative binding tests, code-derived help, then a separately authorized adapter. |
| Implement the remaining 25 Delving methods. | S2 | One bounded method at a time, each with public locations/measurements only and independent tests. |
| Refactor TruePlug into a real detached development center. | S1 security | Separate repository/process/workspace, fake services, complete hashes, named mandatory gates, immutable submission packet. |
| Connect and qualify a real TrueVision + TrueAudio + Linux Fusion workflow. | S2 capability | Exact modality contracts, partial/missing behavior, timing, receipts, and no inferred semantic cognition. |
| Resume or replace model education. | S2 research | Only after current system contracts are aligned; evaluate against witnessed operations and sealed holdouts. |

## Needs tuning

1. **Repository-map encoding:** semantics are useful; verbose JSONL is not.
2. **Call resolution:** 42,836 unique, 72,614 ambiguous, and 159,153 unresolved
   calls must remain distinct while better language/runtime witnesses are added.
3. **Evidence focus:** exact subject custody works in fixtures, but real SciFact
   same-sentence confirmation remained 0/30.
4. **Worker result coverage:** the common envelope is proven for the repository
   worker family, not every TrueSystems callable.
5. **Receipt semantics:** execution, publication, nested integrity, and observed
   postcondition must not collapse into one success field.
6. **TrueCog naming:** current code proves temporal observation and custody, not
   broad cognition.
7. **PluginRunner:** preserve behavior worth keeping, but replace shared-process
   imports, weak promotion scoring, partial change detection, and implicit host
   access rather than polishing them.

## Immediate ordered continuation

1. Commit and post-commit verify today’s documentary and TruePlug custody state.
2. Complete Day 1 read-only local navigation operations.
3. Correct the highest-risk TrueCog verifier/schema/documentation mismatches.
4. Add compact repository-map transport with exact parity.
5. Build control-flow/data-flow authority before promoting security judgments.
6. Complete Delving argument binding before any TrueCore registration.
7. Refactor TruePlug separately; never execute the imported runner against the
   live system.

The day produced real foundations. The remaining danger is not that nothing
worked; it is that several proven slices could be mistaken for one completed
system. They are not yet one completed system.
