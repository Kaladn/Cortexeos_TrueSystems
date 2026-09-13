# TrueCore worker result and skill index contract

This is the system-wide starting contract for every newly registered TrueCore
worker and for every future worker family derived from a human work order.

## One execution doorway

Workers are invoked through the TrueCore runner and a validated agent manifest.
A worker may delegate to a component-owned callable, but it does not absorb that
component's authority. TrueMachine still owns repository observation; TrueCore
owns registration, permission checking, invocation, and the common result gate.

## One processable result

Every worker execution leaving the TrueCore runner uses:

```text
truecore.worker_result@1
```

The executable contract is
`TrueCore/truecore/live_agents/worker_result.py`. It preserves separate fields
for status, native result, locations, relationships, evidence, claims,
artifacts, unresolved facts, errors, receipts, and continuation. Supported
claims require explicit evidence bindings. A successful process exit does not
create evidence or a supported claim.

Legacy workers are wrapped at the runner boundary. Their native output is
preserved under `result.native_output`; it is not reinterpreted as locations,
evidence, claims, or receipts. New workers should emit the common envelope
directly.

## One skill index

The executable index builder is
`TrueCore/truecore/live_agents/skill_index.py`. It reads only validated agent
manifests and publishes `truecore.skill_index@1`. The tracked current index is:

```text
TrueCore/truecore/live_agents/AGENTS/catalog/skill_index.json
```

Index fields come directly from manifests: identity, version, runtime,
entrypoint and hash, required parameters, declared read/write boundaries,
approval state, mutation class, risk tier, callability, and result schema.
Catalog descriptions do not prove execution behavior.

## Work-order continuation point

When a human supplies a larger work order:

1. preserve the input verbatim and hash it;
2. derive bounded worker candidates without changing the original;
3. implement each worker against a real component-owned callable;
4. register one validated manifest per worker;
5. generate code-derived usage through the existing help path;
6. publish it in the skill index;
7. qualify input binding, permission, execution, common output, failure,
   ambiguity, and continuation externally;
8. let downstream workers consume only validated `truecore.worker_result@1`
   packets.

The first component adapter governed by this contract is
`truemachine_repository_map`. It can request TrueMachine build, query, and
verification operations. Its query operation returns locations and
relationships without answers or security conclusions.

The first larger worker family is recorded in
`docs/work_orders/TRUECOG_REPOSITORY_GRAPH_WORKER_GENERATION_1.md`. Its manifests
are generated from
`TrueCore/truecore/live_agents/AGENTS/catalog/repository_graph_worker_source.csv`.
The generated runtime catalog and system skill index provide the reproducible
registration outputs.
