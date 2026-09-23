# TrueSystems provenance versus conventional and current evaluation harnesses

**Date:** 2026-09-15  
**Repository:** `/home/lamercey/TrueSystems-Alignment`  
**Status:** read-only architecture and adversarial comparison; no runtime code changed by this report

## Executive conclusion

TrueSystems is not yet a replacement for a general agent-evaluation harness. It
is a different authority layer.

Most current harnesses answer one of these questions:

- Did the model produce the expected answer?
- Did the retriever return relevant documents?
- Did the agent complete the task in a sandbox?
- Did the tool trajectory look acceptable?
- Did the run become slower, more expensive, or less reliable?

TrueSystems asks a prior question:

> **What exact admitted state, source bytes, relationship path, permission
> decision, and execution receipt justify treating this result as an observed
> result at all?**

That makes TrueSystems complementary to the best existing harnesses, not a
drop-in competitor. The strongest combined design is:

```text
market harness breadth and task environments
    -> TrueVision/TrueMem admission and exact source identity
    -> TrueCore host-bound capability and permission gate
    -> task/tool/model execution
    -> TrueMachine observations and receipts
    -> provenance-aware grader
    -> separate task score and provenance-integrity score
```

The important change is that provenance moves from a citation or trace attached
after the answer to an **executable qualification boundary**. A fluent answer,
a successful browser task, or a passing test cannot promote an unadmitted or
tampered source into evidence.

## What is currently proven in TrueSystems

### Source and dataset custody

`TrueMachine/src/truemachine/repository_integrity.py` implements
`truemachine.repository_integrity_snapshot@1` and content-addressed SHA-256
blobs. Snapshot creation requires a clean Git worktree, rejects symlinks and
invalid roots, records the repository commit and external-view roots, and
declares `persistent_symbols: false` and `normalization_performed: false`.

Verification compares the trusted manifest and blobs with the live roots. It
returns `SAFE_MODE_REQUIRED` for additions, removals, content changes, or mode
changes and pinpoints text changes by UTF-8 line/column or binary changes by
byte range. It does not claim to identify an offender without an OS audit
witness and does not overwrite the suspect source. `create_incident` preserves
the observed copy in quarantine and materializes a read-only trusted safe tree.

This is stronger than ordinary trace metadata, but it is not a cryptographic
signature system. A party able to rewrite both source and the local manifest
can defeat a local hash check; an external vault, signed manifest, or separate
trust anchor is still required for hostile-host claims.

### Host-bound operations

`TrueCore/truecore/machine_navigation_bridge.py` binds a worker to a host-owned
resource, allowed worker family, manifest hash, and budgets. The model cannot
provide a path, executable, Python module, grant, or authority root. The
`integrity.verify` operation is read-only and receives its snapshot binding
from the host.

`TrueCore/truecore/live_agents/manifest.py` validates entrypoint hashes,
allowed reads/writes, approval requirements, runtime language, risk tier, and
the common `truecore.worker_result@1` schema. Registered workers are not
allowed to become prompt-only pseudo-tools.

`TrueCore/truecore/live_agents/worker_result.py` requires explicit locations,
relationships, evidence, claims, unresolved states, errors, receipts, and a
continuation decision. A `SUPPORTED` claim must bind to returned evidence. The
schema permits `NOT_IMPLEMENTED` and `UNRESOLVED`; it does not force a weak
graph to manufacture a security conclusion.

### Graph and evidence limits

The repository map is source-grounded and currently exposes ownership,
source-order, dependency/call, and exact name-access relationships. The map
and `TrueMachine` repository views deliberately return locations and
relationships, not answers. Several views return `NOT_IMPLEMENTED` until the
required control-flow, data-flow, test-target, documentation-claim,
security-role, privileged-sink, or canonical-object authority exists.

This is a strength against false certainty, but it means the system cannot yet
prove reachability, causation, permission dominance, or taint flow merely from
the current graph.

## Adversarial comparison

The table compares capabilities, not marketing names. “Traditional” means the
usual benchmark/RAG/evaluator pattern; “current public harnesses” means the
representative systems documented below as of 2026-09-15.

| Harness family | What it is good at | Its usual authority assumption | Adversarial failure against provenance | What TrueSystems adds |
|---|---|---|---|---|
| Traditional QA / exact-match evals | Stable answer scoring, cheap regression tests | Gold answer is correct and the prompt/sample is intact | A wrong gold label, incomplete qrel, or unsupported answer can score as success | Preserve source and dataset revision; classify gold defect, incomplete evidence, or valid NEI separately |
| BEIR-style retrieval benchmarks | Cross-dataset retrieval comparison, zero-shot IR metrics | Corpus, query, qrels, and relevance judgments are accepted inputs | A benchmark can reward retrieval of the wrong subject or incomplete qrels; rank metrics do not prove relation ownership | Return exact locations and relationship witnesses; audit the benchmark object itself |
| RAG metrics such as Ragas | Context precision/recall, faithfulness, answer relevance, tool-call metrics | Retrieved context and reference fields are sufficient evaluation material | LLM-as-judge and reference-free scores can bless co-occurrence, fluent unsupported claims, or a bad reference | Require source hashes, owner custody, evidence bindings, and deterministic claim states before scoring |
| OpenAI Evals-style suites | Reusable eval templates, model/solver separation, recorders, custom graders | The eval definition and recorder are trusted; output is the main scored object | Prompt injection in content, mutable eval assets, grader leakage, or a model-graded reference can be hidden behind a passing score | Host-bound source and worker identities, fail-closed artifacts, explicit unresolved/unsupported states |
| Inspect AI | Task/dataset/solver/scorer composition, agent tools, sandboxed execution | Sandbox and task package define the trusted experiment; scorer defines truth | Excellent trajectory coverage can still score a task while source identity, benchmark revision, or evidence custody is not independently authenticated | Add immutable admission and per-step evidence/permission receipts without replacing Inspect’s sandbox/scorer model |
| BrowserGym / WorkArena / WebArena family | Realistic web-agent interaction and task completion | Browser state and task success checker are the practical truth | Screenshots and final state can hide wrong-account actions, stale pages, injected content, or an unrecorded external mutation | Bind browser/tool resource, source state, operation receipt, and postcondition to a witnessed run identity |
| OSWorld / OSWorld-V2 | Long-horizon desktop workflows and multimodal interaction | Pinned image/task release plus final environment state | A task can pass while intermediate actions, external I/O, or altered assets are not independently attributable | Preserve exact image/task hashes, TrueCore permission decisions, action receipts, and before/after state hashes |
| SWE-bench-style coding harnesses | Real repository issues, patches, tests, reproducible software tasks | Repository checkout, issue, patch, and test result define correctness | A patch can pass visible tests while changing an untested path; a checkout or dependency can drift | Snapshot repository and external views, map exact source spans, preserve test-target authority, and mark absent control/data-flow as unresolved |
| LangSmith/Langfuse/Phoenix-style observability/eval | Production traces, experiments, datasets, feedback, latency and cost comparisons | Collector/backend and attached metadata are trusted enough for operations | A trace is evidence of logging, not proof that the logged source or tool result was authentic; collectors can be misconfigured or replayed | Make receipts content-addressed and bind them to admitted source, worker manifest, run/sequence, and host resource |
| OpenTelemetry-style tracing | Cross-process trace/span correlation and context propagation | Trace context correlates events; it does not define truth | Forged or untrusted trace headers, missing spans, and baggage leakage can create a persuasive but false causal story | Treat trace IDs as correlation only; require source and operation receipts for authority |

### What “latest” means here

There is no single best market harness. The current public direction is a
stack: Inspect-style agent evaluation, BrowserGym/OSWorld-style realistic
environments, SWE-bench-style repository tasks, Ragas/BEIR-style retrieval
metrics, and LangSmith/OpenTelemetry-style trace analysis. They optimize for
different observable outcomes. TrueSystems should not reimplement all of them;
it should provide the provenance contract they currently lack.

## The adversarial cases the combined harness must add

These are not generic “try a harder prompt” tests. Each test must have a
pre-state, exact mutation or substitution, expected refusal/qualification, and
receipt.

### 1. One-byte or one-glyph source mutation

Change one source byte after admission. The harness must stop before the worker
or model uses the changed source, report the exact line/column or byte range,
quarantine the observed copy, and expose the trusted safe tree. A fluent answer
from the changed text is a failure, even if its task score is correct.

### 2. Manifest and resource substitution

Keep the source unchanged but swap the manifest, repository map, worker
entrypoint, dataset ID, or external-view root. TrueCore must reject the resource
before execution with a changed-resource or manifest-tamper receipt.

### 3. Relationship-owner collision

Place the requested predicate/object near two subjects, with the correct
relationship owned by the other subject. Same document, paragraph, block, or
retrieval rank must not establish ownership. The result must return the
competing locations/relationships and remain unsupported until custody is
continuous.

### 4. Wrong polarity, quantity, or direction

Use a source that says “does not,” “decreases,” “before,” or “one” where the
claim asks for the opposite. Retrieval may succeed, but support must be
`CONTRADICTED`, `AMBIGUOUS`, or `PARTIALLY_SUPPORTED`, not `SUPPORTED`.

### 5. Benchmark defect

Give the harness a gold document that cites a different subject or does not
establish the claim, while another admitted document does. Report two scores:
raw benchmark agreement and evidence adjudication. Never modify the original
label to make the system pass.

### 6. Model-supplied authority injection

Ask the model to provide an absolute path, executable, module, manifest, grant,
or wider scope. The request must be rejected or reduced to host-bound values;
the model must not be able to turn a read-only worker into a writer.

### 7. Stale and replayed receipt

Replay a valid receipt against a different run, sequence, source root, worker
hash, or dataset revision. The verifier must reject it before treating the old
result as current evidence.

### 8. Partial and interrupted work

Kill a worker after input admission but before a terminal receipt. The harness
must preserve the partial record, refuse automatic completion, and expose an
explicit retry or human-review state.

### 9. Missing graph authority

Ask “does untrusted input reach this privileged sink?” against the current graph.
The correct output is `NOT_IMPLEMENTED` with the missing control/data-flow and
privileged-sink relationships—not a suspiciousness score presented as a fact.

### 10. Trace forgery and external-context injection

Supply forged traceparent/baggage values or an untrusted external event. Trace
correlation may be retained as telemetry, but it cannot create source
authority, permission, actor identity, or causal proof.

## Where TrueSystems is weaker today

This comparison is not a victory lap. The following are real gaps:

1. **Control/data-flow is incomplete.** The graph’s current N-N-N is
   ownership–source-order–dependency, not execution reachability or def-use.
2. **Actor attribution is unresolved without OS audit evidence.** File owner,
   mtime, and UID are not an offender identity.
3. **Legacy routes exist outside the qualified boundary.** The dormant
   `control-api` has direct component routes and retains legacy question/top-k
   shapes; it must not be treated as equivalent to the TrueCore path.
4. **Local hashes are integrity checks, not signatures.** The vault/trust root
   must be separated before claiming hostile-host security.
5. **Receipt metadata can be durable without being authoritative.** The receipt
   consolidation contract explicitly distinguishes facts, publication, and
   enforcement authority.
6. **Native Rust/non-Python surfaces are not all mapped.** Static Python
   coverage cannot imply the behavior of unmapped native code.
7. **The benchmark-audit layer is not yet a universal market adapter.** The
   schema and classifications exist as design direction, but qrel/claim
   adjudication still needs an independently qualified implementation.

These gaps are why TrueSystems should initially be a provenance sidecar and
gate, not the only evaluator or security oracle.

## Combined architecture: the provenance-first harness

### Run envelope

Every benchmark or agent run should receive a host-created envelope:

```json
{
  "schema": "truesystems.provenance_run@1",
  "run_id": "host-issued",
  "source_revisions": [
    {"kind": "repository", "commit": "...", "snapshot_id": "..."},
    {"kind": "dataset", "revision": "...", "sha256": "..."}
  ],
  "harness": {"name": "inspect|browsergym|osworld|swebench|custom", "version": "..."},
  "capability_binding": {"worker_id": "...", "manifest_sha256": "..."},
  "authority": {"root_binding": "host-owned", "model_paths_supplied": false}
}
```

The model or agent can propose bounded intent. The host supplies roots, grants,
worker identities, dataset revisions, and resource bindings.

### Step and evidence envelope

Each step records:

- request and argument binding hash;
- source/asset revision and exact selected locations;
- relationship edges and ownership custody;
- permission decision and approval state;
- tool/worker entrypoint hash;
- observed result and postcondition;
- receipt digest and continuation state;
- unresolved requirements and missing authority.

The output to the model can remain short. The authoritative packet stays
outside the prompt and is referenced by immutable IDs and hashes.

### Two scoreboards

Never collapse these into one number:

**Task scoreboard**

- answer/task success;
- retrieval precision/recall;
- tool-call correctness;
- test pass or environment postcondition;
- latency and cost.

**Provenance scoreboard**

- source admission verified;
- dataset/benchmark revision pinned;
- relationship ownership continuous;
- all claims bound to exact evidence;
- permission and worker manifest verified;
- no replay/stale receipt;
- unsupported or missing authority correctly refused;
- mutation detected and quarantined;
- actor attribution honestly unresolved when no OS witness exists.

A run that completes the task but fails provenance is **task-successful and
provenance-invalid**. A run that refuses a bad benchmark claim is **task-score
negative and evidence-correct**. This is the accounting needed to expose
garbage benchmarks instead of training the system to imitate them.

## How this changes the future of provenance

### From citation to custody

Traditional provenance answers “which document was cited?” The combined model
answers:

```text
which exact bytes were admitted
-> in which revision and run
-> through which authorized capability
-> along which owned relationship path
-> with which observed postcondition
-> producing which claim and receipt
```

Provenance becomes a condition for authority, not an ornamental field on a
completed answer.

### From answer grading to benchmark grading

The harness can score the benchmark itself: wrong subject, wrong polarity,
unwitnessed relation, incomplete qrels, valid NEI, corpus limitation, local
mapping error, or genuine retrieval/answer failure. Benchmark creators can
receive a compact correction packet with source hashes, coordinates, and
reproduction steps rather than an accusation based on one model score.

### From observability to replayable proof

OpenTelemetry and commercial tracing make distributed events correlate. The
TrueSystems layer would add source custody and authority checks so a trace can
be replayed against the same admitted revision and either reproduce the result
or explain exactly why the old receipt is stale.

### From model trust to boundary trust

The model no longer needs to be trusted as the holder of paths, grants, source
identity, or completion status. It can remain capable and even adversarially
curious; TrueCore decides which bounded operation may run, and the grader
decides which claims the evidence supports.

### From “secure” to measurable failure modes

The combined harness can publish not only a pass rate but a failure taxonomy:

```text
retrieval miss
demand/decomposition miss
relationship-owner collision
polarity/direction miss
benchmark defect
source unavailable
permission denial
stale/replayed receipt
missing graph authority
actual answer failure
```

That makes future model and system improvement scientific instead of aesthetic.

## Recommended adoption order

1. Keep current TrueSystems read-only and preserve the existing owner boundary.
2. Define a small `provenance_run@1` envelope around one external harness first
   (Inspect is the cleanest initial agent adapter; SWE-bench is the strongest
   code-task adapter).
3. Add mutation, wrong-owner, stale-receipt, model-path-injection, and
   missing-authority tests before broad benchmark coverage.
4. Store the harness release, task asset hashes, source snapshot, worker
   manifest, and receipts together. Do not rely on a dashboard export alone.
5. Produce separate task and provenance scoreboards.
6. Add BrowserGym/OSWorld adapters only after action receipts and postconditions
   are qualified for the relevant desktop/browser resource.
7. Add control/data-flow and native-surface graph authority before promoting
   security reachability claims.
8. Add external signing or an independent vault before claiming protection from
   an attacker who can rewrite the local repository and manifest.

## Bottom line

Traditional and current harnesses are excellent at making agents comparable.
TrueSystems is strongest at making the comparison deserving of belief.

The future combination is not “TrueSystems replaces Inspect, SWE-bench,
OSWorld, Ragas, or LangSmith.” It is:

> **Those systems provide the hard environments and broad task coverage;
> TrueSystems supplies source custody, relationship custody, capability
> authority, fail-closed integrity, and evidence-grade receipts.**

That is a materially different future for provenance: the system will be able
to say not only *what happened* and *what score it received*, but *which exact
state was allowed to count, what was proven, what was not proven, and why the
result remains replayable or must be rejected*.

## External primary references

- [Inspect AI documentation](https://inspect.aisi.org.uk/) and [task/scorer model](https://inspect.aisi.org.uk/tasks.html)
- [OpenAI Evals run guide](https://github.com/openai/evals/blob/main/docs/run-evals.md), [solver separation](https://github.com/openai/evals/blob/main/evals/solvers/README.md), and [eval templates](https://github.com/openai/evals/blob/main/docs/eval-templates.md)
- [BrowserGym repository and benchmark ecosystem](https://github.com/ServiceNow/BrowserGym)
- [OSWorld repository](https://github.com/xlang-ai/OSWorld) and [OSWorld-V2 release manifests](https://github.com/xlang-ai/OSWorld-V2/blob/main/benchmark_releases/README.md)
- [SWE-bench organization](https://github.com/swe-bench)
- [BEIR retrieval benchmark](https://github.com/beir-cellar/beir)
- [Ragas metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/)
- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
