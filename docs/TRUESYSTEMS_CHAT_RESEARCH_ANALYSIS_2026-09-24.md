# TrueSystems research and integration record — 2026-09-24

## Scope and evidence discipline

This record synthesizes the work and decisions in the current conversation,
including the investigations reported earlier in it and the source inspection
performed on 2026-09-24. It is a **research and decision record**, not a claim
that the full TrueSystems integration has been implemented. It does not
reconstruct other Codex conversations or the admitted historical archive.

The labels used below matter:

- **Operator law** is an explicit direction given in this conversation. It
  defines the intended boundary but does not prove that code obeys it.
- **Code observation** identifies a particular implementation path. It proves
  only what that inspected path does.
- **Runtime observation** identifies an effect actually observed in this
  session. A source file, registered manifest, or receipt alone is not one.
- **Reported prior finding** comes from an earlier investigation summarized in
  this conversation. It is retained for continuity where this report did not
  independently repeat the entire audit.
- **Unverified** means the available evidence does not establish the claim.

The assembled checkout is `TrueSystems-Alignment`. Separate checkouts of
`SecureCore`, `CompuCog`, and the operator-model gateway were also inspected.
Their common names do not establish that their runtimes are joined. The
working tree was already extensively dirty when this record was prepared;
this document does not adopt or certify those other changes.

## 1. What the operator established

### Names and authority

1. **SecureCore** is the canonical name for the authority system. `TrueCore`
   remains a legacy source-path name, not another authority.
2. **AnchorWorks** is the canonical name for the relationship and evidence
   system. `TrueMem`, `AWEAR`, and `AWRAG` are legacy or lineage names, not
   independent current systems by virtue of their names.
3. **CompuCog** is the canonical name for machine cognition, observation,
   temporal and causal state, machine I/O observation, lineage, and
   security-relevant findings. `TrueMachine` is a legacy source-path name.
4. TrueVision, TrueAudio, and the other bounded components retain their
   actual code-backed responsibilities. An old `TrueIO` label does not create
   an independent live I/O subsystem.
5. Every TrueSystems operation must enter **SecureCore** for identity,
   admission, authorization, agent initiation where applicable, dispatch, and
   completion governance. A working direct component call does not authorize
   itself.
6. **CompuCog does not replace SecureCore** and is not a universal router for
   every payload. It observes and reports findings; SecureCore remains the
   authority decision maker. Any required pre-action, concurrent, or
   post-action observation is operation-specific.
7. The repository development lock is to remain **disabled** until the owner
   explicitly says to lock the repository. Only the owner may authorize an
   enable or disable transition. Its current marker is `locked: no`; this
   record does not change it.

These rules are now stated in the working-tree root [`AGENTS.md`](../AGENTS.md).
That instruction change is not evidence of a completed runtime connection.

### Operating method

The requested order is: resolve governing `AGENTS.md` instructions, establish
current capability and the existing production caller, determine authority,
then plan and operate. Crossing into a new concern requires resolving its
instructions before crossing. Neither documentation nor a callable grants
runtime authority. The instruction-resolution map must cite actual
caller/callee edges and preserve unresolved states.

The operator rejected invented question runners, helper ingress, surrogate
questions, pairwise resurrection, generic RAG substitutions, and new
workflows chosen for model convenience. The canonical AnchorWorks evidence
interface is typed `EvidenceNeed` with source coordinates and signed relation
evidence. Additional historical methods may be kept as bounded, conditional
deeper methods only after exact source-level reconciliation; they are not
automatically inserted into every query.

The operator also rejected standing synthetic test files as architectural
authority. Proof of a production operation must use real admitted data, the
authorized route, the actual requested effect, and external receipts. Runtime
integrity and admission checks remain production machinery. Historical copied
test-named files remain source-lineage evidence when their original names are
part of immutable manifests. `job_acceptance_run` was classified in the
conversation as an optional admitted-script executor, not proof that another
production operation succeeded.

## 2. How this investigation changed direction

| Phase | Decision or finding | Remaining limit |
| --- | --- | --- |
| Pipeline reset | Read governing instructions and trace source authority through admission, intake, AnchorWorks, SecureCore, retrieval, evidence, and output from code. | The requested complete function-by-function verification and code map were not finished in this chat. |
| Instruction architecture | Root law is short and global; decision-bearing local `AGENTS.md` files govern concerns; operation resolution crosses directory boundaries. | A prior inventory reported 143 files across the examined material. This report does not re-audit that count or certify that all duplicates were removed. |
| Test-layer decision | Standing test infrastructure is to be removed; production verification uses real authorized operations. | The present working tree contains many test-file deletions, but their complete dependency cleanup and operational consequences have not been certified here. |
| Naming reconciliation | SecureCore, AnchorWorks, and CompuCog are the three canonical names for their respective concerns. | Legacy module names remain in code and evidence; renaming alone cannot repair authority edges. |
| AnchorWorks reconciliation | Today's typed evidence route remains canonical; legacy answer-shaped and ranking paths are candidate evidence, not automatic replacements. | The file-level duplicate/deeper-method catalog was not completed in this record. |
| I/O ownership | The operator directed a code-based TrueIO-versus-CompuCog investigation. | No independent current TrueIO authority is established by the evidence retained here. Removal or migration of every stale mention is unverified. |
| Desktop action | TrueComputer was classified by the prior inspection as a bounded Linux desktop actuator, not general computer-use authority. | Its CLI is not proven to be dispatched by SecureCore or observed by CompuCog. |
| Role correction | SecureCore is sole operational authority; CompuCog supplies cognition, observation, lineage, and security findings. | The old linear `SecureCore → CompuCog → every component` diagram was rejected. |
| Whole-system scope correction | The work is the marriage of **all TrueSystems**, not only SecureCore and CompuCog. | No full-system production route was observed complete. |

The conversation also exposed process failures: an earlier claim that a report
had been opened when it did not exist, a move toward a new question runner,
standing test files reappearing under an old global instruction, and repeated
interpretation of partial code paths as final architecture. These are reasons
for direct state verification and explicit `UNVERIFIED` labels. This record
does not attribute every current worktree modification to those events or
claim that any particular production behavior was broken by them.

## 3. Current SecureCore entry and identity problem

Four inspected surfaces have different jobs and are not proven to be one
admitted front door:

| Surface | What code establishes | What it does not establish |
| --- | --- | --- |
| [Rust frontdoor](../TrueCore/frontdoor/src/main.rs) and the separate `SecureCore/frontdoor/src/main.rs` | Proxies `/api/*` to a backend and exposes health. | The proxy itself does not authorize a component operation. |
| [Flask app](../TrueCore/truecore/app.py) and separate `SecureCore/securecore/app.py` | Constructs SecureCore substrates, agents, JWT-protected control routes, and local control machinery. | Its inspected HTTP routes do not form a demonstrated dispatch route to every TrueSystems component. |
| [Model host](../TrueCore/truecore/model_host.py) → [operator boundary](../TrueCore/truecore/operator_boundary.py) | The host supplies grants and resource bindings outside the model request; the boundary checks its finite operation set and returns a result hash. | A current host config, deployed caller identity, and full component admission were not observed. The listed operations are narrower than the full system. |
| Separate `SecureCore/securecore/package_api/contracts.py` → `service.py` | Validates a finite route name and a caller string; implemented branches include memory and chat ledger calls. | Membership of a caller string in an allowlist is not authenticated caller identity. Some recognized routes return `ok` with an unimplemented warning. |

The separate operator-model gateway's
`src/truesystems_operator_model_gateway/securecore_loop.py` supplies a caller
string to the package API. Its Codex mode itself records that native Codex
tools are not proven to be SecureCore-only. An operator-facing loop therefore
cannot be promoted to the universal authority boundary on this evidence.

The 2026-09-24 machine snapshot showed LocalMemoryChat listening at
`127.0.0.1:1236`, with no listening SecureCore service at the inspected
ports and no matching SecureCore/CompuCog process. That is a **snapshot**, not
proof that an on-demand host or a differently deployed SecureCore path never
operates. No authorized end-to-end component operation was run for this report.

## 4. Whole-system marriage: current paths and missing edges

The matrix separates the component's present callable from the missing
system-level relationship. It is not an instruction to route every payload
through CompuCog or to replace the component with a new wrapper.

| Concern | Existing code-backed capability or path | Current integration finding / required edge |
| --- | --- | --- |
| SecureCore | [operator boundary](../TrueCore/truecore/operator_boundary.py), registered worker bridge, Flask controls, separate package API | Establish which caller identity, host grant, resource admission, dispatch, and completion path governs each operation. The surfaces above are not yet proven joined. |
| CompuCog | Assembled [TrueMachine package](../TrueMachine/src/truemachine/) stores temporal observations and Fusion Packs; separate CompuCog checkout has sensor/event and API generations. | Define required observation per operation, bind real sensor/input and result-finding handoffs, and preserve SecureCore's final decision. The separate CompuCog API's reported `NOOP` order execution must not count as machine action. |
| DocuFilm / TrueVision Intake | [document-state reader](../TrueVisionIntake/truevision_intake/document_state/state_reader.py) and [TrueMem handoff](../TrueVisionIntake/truevision_intake/docufilm_truemem.py) | Source admission, bytes/hash, glyph/block coordinates, and handoff need an authorized SecureCore caller before system use. |
| AnchorWorks | [typed `EvidenceNeed` retrieval](../TrueMem/src/truemem/engine/evidence_retrieval.py); direct CLI and [control API](../control-api/src/truesystems_api/runtime.py) paths | Bind typed evidence and provenance through SecureCore; direct calls are bypasses. Do not replace with LocalMemoryChat raw-question output or legacy ranked answers. |
| TrueVision | [studio server](../TrueVision/scripts/truevision_studio_server.py), AV-tool calls, [template renderer](../TrueVision/truevision_runtime/rendering/template_renderer.py), and native capture | Admit the selected existing operation via SecureCore; distinguish prepared preview from actual render and generated video from captured evidence. |
| TrueAudio | Existing scripts call logging/replayable/replay functions under [`trueaudio_runtime`](../TrueAudio/trueaudio_runtime/) | Admit exact source and operation through SecureCore; preserve source identity and audio-state receipts. Direct scripts are component calls. |
| TrueSpeech | [speech segmentation](../TrueSpeech/truespeech_runtime/speech.py) and lyric-candidate alignment | Bind the chosen call to SecureCore and TrueAudio state identity. Segment detection is not a transcript. |
| TrueComputer | [Rust CLI](../TrueComputer/src/main.rs) validates and executes a small Hyprland/`wtype` action set with pre/post state and receipts | SecureCore must authorize and invoke the bounded action; CompuCog may observe and report. Neither the direct CLI nor its own receipt is an authority grant. |
| LocalMemoryChat | Local cited-memory package and gateway; separate SecureCore package `memory.query` calls the gateway | Prove authenticated caller binding and preserve memory as memory, not AnchorWorks source evidence. The running gateway is not proof of SecureCore admission. |
| Clearbox Chat-Chain | [HTTP handler](../clearbox-chat-chain/src/clearbox_chat_chain/server.py) calls conversation storage/core directly | Conversation creation, turns, and continuation need SecureCore admission while retaining durable order and IDs. |
| Control API and UIs | [HTTP route table](../control-api/src/truesystems_api/server.py) delegates directly to component runtime functions | Transport must enter SecureCore before dispatch. Existing direct routes remain bypasses until an authorized replacement works and is observed. |
| Experimental sibling projects | Anchor Index, Reasoning Space, chatbot/model experiments, and other separate checkouts were discussed as candidate or staged work | Do not promote by name, catalog, or filesystem presence. Determine exact ownership, admission, and authority individually before adding to production. |

`TrueIO` is not added as a separate row of authority. The operator directed that
real machine I/O responsibilities be derived from code and assigned to their
actual owners. The prior inspection did not prove a separate live TrueIO
runtime; a complete stale-reference removal is **unverified**.

## 5. AnchorWorks technical risks below the authority edge

The canonical route is
[`query_evidence_need_mapping`](../TrueMem/src/truemem/engine/evidence_retrieval.py)
with typed evidence fields. The earlier code investigation identified three
specific risks that must be settled before an evidence packet is called
trustworthy:

1. `COMPLETE_EVIDENCE` is currently selected when `proof_locations` is
   nonempty in `evidence_retrieval.py`. The prior trace found that anchor
   coexistence within a block could satisfy that condition without proving
   the requested **signed relationship**. Either the status must describe
   its narrower proof or the signed witness must be required.
2. [Intake pipeline](../TrueMem/src/truemem/engine/pipeline.py) permits any
   positive relationship window, while the investigated retrieval geometry
   assumed ±6. The admitted geometry must be explicit and read back exactly;
   otherwise intake and retrieval can disagree.
3. The same pipeline computes a `file_digest` from the path string in its
   inspected default branch. Source-byte integrity must carry through
   admission and retrieval; path identity or mtime/count readiness is not
   equivalent to a source-byte hash.

These findings are **diagnoses**, not fixes made by this report. The same
investigation found legacy answer-shaped and XPU ranking machinery, including
[`xpu_relationship_index.py`](../TrueMem/src/truemem/engine/xpu_relationship_index.py).
Its presence does not prove the typed normal route uses it. Each current
dependency on legacy answer-shaped code still requires caller/callee
classification as required, replaceable, or removable. A complementary
deeper method needs a named trigger, bounded input/output, unchanged
provenance, and no silent effect on the canonical result.

## 6. Instruction, test, and lock findings

The prior instruction inventory reported one root, 36 concern files, 54
generic inventories, 40 test-tree instructions, seven mostly scope-only
files, and five staged/reference files: 143 total. The operator's retention
rule is functional: a governing file should change what an agent may, must,
or must not do. Folder tours and duplicated test-tree rules do not become
law merely because they are named `AGENTS.md`. The current
`AGENTS_RESOLUTION_MAP.json` is **untracked working-tree material** and covers
a finite code-traced subset; it cannot establish a complete system map or
runtime admission by itself.

The conversation identified a real instruction conflict: the old root wording
encouraged universal `TrueMachine` traversal even though local instructions
said it was not a general router. The working-tree root now states the
corrected SecureCore/CompuCog roles. A separate old global instruction had
required external acceptance-test files after meaningful changes; the
working-tree `/home/lamercey/.codex/AGENTS.md` now calls for operational
verification and forbids standing synthetic tests. That external file is
outside this commit. The current tree shows many test-file deletions and
related manifest/creator edits. This report does not certify the complete
test-removal dependency map, prove imports still resolve, or stage those
deletions.

The legacy `test_command` field was reported to be structurally required in
older agent registration while production execution used `command`. The
operator rejected renaming it into `proof_command` or inventing a replacement
test layer. Current uncommitted manifest and creator work must be evaluated
for its actual effect on registration and authority before being called
complete. Historical copied source files whose test-like names are fixed in
lineage manifests must be assessed as evidence rather than erased by a
filename rule.

The earlier lock investigation located a repository development-lock path
through SecureCore's CLI with hashing and ordinary write-bit control
delegated to TrueMachine. The current checkout has an untracked
`REPOSITORY_LOCK.json` reading `locked: no`. No lock transition was requested
for this document. This mechanism was deliberately described as a
development interlock, not protection against the filesystem owner or
privileged code. The operator explicitly reported that an earlier lock had
blocked Codex work and had to be disabled; the present report does not
contradict that history or claim to have reproduced it.

## 7. What is done, what is not, and what failed

**Established as operator law:** canonical names, SecureCore's sole authority,
CompuCog's cognition/observation role, instruction-first resolution,
operation-aware routing, source/provenance preservation, no standing test
layer, and owner-controlled lock state.

**Code paths identified:** the finite model-host boundary, the separate Flask
and package surfaces, direct control-API/component ingress, AnchorWorks typed
retrieval, DocuFilm handoff, media and desktop component callables, and
CompuCog's split generations. The prior TrueComputer investigation reported
fixed `hyprctl`/`wtype` actions, exact active-window preconditions, request
hashing, and redacted receipts; it did not observe SecureCore dispatch.

**Not completed:** a proven common SecureCore front door for humans and bots;
authenticated package caller binding; a full operation-by-operation admission
catalog; all component connections; operation-specific CompuCog observation
handoffs; complete AnchorWorks source-byte/signed-proof/geometry repair;
closure of bypasses; a verified all-functions inventory; full 143-file
instruction reconciliation; complete test-removal dependency proof; and
real end-to-end operational receipts across the system.

**Not established as broken:** the conversation contains concerns about
regressions, stale routes, and previous agent mistakes, but this report did
not run the historical reconstruction through admitted evidence or show that
a specific production capability was destroyed by the present work. The
large pre-existing dirty worktree must not be mistaken for a verified set of
successful or failed integrations.

## 8. Required order for the full-system marriage

1. **Resolve SecureCore's actual production admission boundary.** Prove the
   human/bot caller identity and host grants, select the existing appropriate
   transport for each, and make the permit/deny, dispatch, and completion
   chain inspectable. The Rust proxy, JWT route, model host, and package
   service cannot be called one boundary merely because they share a name.
2. **Register exact existing component operations.** For each row in section
   4, bind its typed input, resource identity, allowed effect, native result,
   receipt, and SecureCore decision. Do not invent a generic runner or make a
   caller-supplied route/command into authority.
3. **Bind CompuCog by observation contract.** Prove each required input,
   recorded state, finding, and handoff to SecureCore. Keep `NOOP`, missing
   sensors, and unverified observations visible.
4. **Reconcile evidence integrity.** Preserve admitted source-byte identity,
   exact coordinates, signed origin/center/lane relationships, and the
   admitted window geometry. Do not turn a memory answer, block co-presence,
   pair total, or ranked legacy answer into signed proof.
5. **Move consumer entrances behind SecureCore.** Resolve the control API,
   UIs, direct servers, CLIs, and operator gateway one operation at a time.
   Do not hide a bypass by deleting or relabeling it before its authorized
   replacement operates.
6. **Prove real operations.** Use admitted data and the actual authorized
   production path for representative evidence retrieval, document intake,
   music-to-video work, audio/speech work, chat continuation, desktop action,
   and machine observation. Check the requested effect and preserve native
   receipts outside the source repository. No standing synthetic test suite
   or renamed acceptance harness is to be created.
7. **Only then report completion.** Separate `CLEANED`, `COMPLIANT`, and
   `STILL_BLOCKED`. Verify the intended repository diff, then commit and push
   only work whose required operation has succeeded and been directly
   verified. No instruction rewrite or deletion may make an authority gap
   appear resolved.

The previously saved
[`TRUESYSTEMS_HISTORICAL_RECONSTRUCTION_SYSTEM_USE_ONLY.md`](TRUESYSTEMS_HISTORICAL_RECONSTRUCTION_SYSTEM_USE_ONLY.md)
is a **later** system-use diagnosis. It is not an instruction to bypass the
missing front door with shell, direct source reading, or a new retrieval
path. Its prerequisite is an observed authorized SecureCore route for the
historical material and current-state inspection.

## 9. Status at publication

- Repository development marker observed: `locked: no`; unchanged.
- This document is the sole file intended for the present commit.
- No runtime code, instruction map, test deletion, or lock transition is
  included in this documentation commit.
- No SecureCore-authorized end-to-end operation was performed for this
  documentation change. Source and instruction inspection verifies the
  scope of the record, not the system marriage.
- The full-system integration remains **STILL_BLOCKED / UNVERIFIED** at the
  shared caller-identity and admission edge, with the per-component gaps
  listed above.
