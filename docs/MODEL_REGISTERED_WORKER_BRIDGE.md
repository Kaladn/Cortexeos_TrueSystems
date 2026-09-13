# Model-to-registered-worker bridge

Status: implemented and externally qualified for the first read-only
repository-graph worker family.

## Boundary

```text
human request
  -> operator LLM constructs a bounded worker request
  -> truecore.operator_request@1
  -> host-owned operation grant
  -> host-owned worker grant
  -> host-owned resource binding and manifest hash
  -> registered TrueCore agent runner
  -> fixed TrueMachine repository view
  -> truecore.worker_result@1
  -> operator LLM inspects locations and relationships
  -> supported response to the human
```

The implementation is `TrueCore/truecore/registered_worker_bridge.py`. The
model-facing operation is `worker.invoke`. The model supplies exactly:

```json
{
  "worker_id": "repo_process_execution",
  "resource_id": "truesystems-map",
  "parameters": {"limit": 25}
}
```

The model cannot supply a filesystem path, Python module, command, manifest,
grant, or approval. The host binds the resource identity to an absolute
TrueMachine repository-map directory and the exact SHA-256 of its manifest.
The bridge checks that binding before and after execution.

Only a host-granted manifest whose source callable belongs to
`truecore.agents.repository_graph_workers`, has no writes or approval path, and
uses `truecore.worker_result@1` may enter this first bridge generation. The
existing TrueCore runner still validates the catalog, manifest, runtime and
source hashes. The bridge does not become an alternate executor.

## Authority

TrueMachine returns locations, static relationships, result grades and missing
graph prerequisites. It does not answer the human's question. TrueCore grants,
binds, runs and validates the worker. The operator LLM chooses a granted method,
inspects the packet, follows exact source locations when necessary, and decides
what the evidence supports.

`STATIC_CANDIDATE` remains an investigation candidate. `WITNESSED_STATIC`
proves only the exact static relationship stated by the worker. A nested
`NOT_IMPLEMENTED` result remains unavailable; the bridge may not rewrite it as
an empty search result or a security conclusion.

## Current qualification

The frozen full-map run used snapshot
`2273d92c39552e70fb4601f8fce6021fc2b73406905a128f4652b0c199f9092e`
with manifest SHA-256
`8bc6ea54998fa7c9dfe1f4623393775180282afe7ae22d0312d8117e6ff78d20`.
Through the JSONL model host it returned bounded process-execution and direct
TrueMem-reference locations. The TrueCore-bypass worker remained
`NOT_IMPLEMENTED` because route-policy, security-role, and control/data-flow
relationships are absent.

No model weights participated in qualification. A local or API model can use
the same JSONL request later without receiving another operational interface.
