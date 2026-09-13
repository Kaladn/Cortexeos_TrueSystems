# TrueCore-only read-worker host

This completes the bounded read-only alignment host. It is a real JSONL transport
and worker dispatcher, not a trained model, sandbox or deployment service.
All operators, human or AI, receive the same result boundaries. Model education
remains paused. The frozen combined generation remains unchanged.

## Host-owned configuration

The trusted embedding host creates a private configuration file with exactly:

```json
{
  "schema": "truecore.model_host@1",
  "grants": ["help.list", "help.query", "sensory.inspect", "source.classify", "media.describe"],
  "artifacts": {},
  "worker_grants": [],
  "resources": {},
  "max_calls": 64,
  "max_request_bytes": 65536
}
```

Bind each admitted artifact ID out-of-band to an absolute `path` and its exact
byte `sha256` in `artifacts`. Those fields do not belong in model requests.
Keep the configuration, process arguments and worker code outside model control.
Only bind sources the requesting operator is allowed to read. No host-selected
grant enables live action: there is no action runner in this interface.

Run with this worktree's TrueCore on PYTHONPATH:

```text
python -B -m truecore.model_host --host-config /absolute/host-owned/config.json
```

This launches no TrueCore app, HTTP server, capture, model or agent thread.
The producer of JSONL may later be a model, but this release does not start
inference or resume any saved checkpoint. Use one serialized stream per session.

## Model turn

```json
{"schema":"truecore.operator_request@1","request_id":"r1","operation":"help.list","arguments":{}}
```

The returned help contains exact argument requirements, result grades, permission,
effects and retry rules from `operator_contracts.py`. Six fixed operation types
are accepted. `worker.invoke` can reach only a host-granted registered read-only
worker and a host-bound resource. No model-supplied module path, URL, shell,
filesystem path, manifest, approval or grant is executable. A model-supplied
worker identity is only a selection among separate host-owned worker grants.

The host validates JSON framing, duplicates/nonfinite values, input size, call
budget and request identity. A repeated ID with the identical request replays
the recorded response. Different content under the same ID is rejected. Corrected
requests require a new ID. Cached results are session results, not fresh reads;
use a new request ID when a new inspection is required. New host admission is
necessary when immutable source content changes.

## Connected component work

| Operation | Actual code used | Limitation |
| --- | --- | --- |
| help.list | TrueCore fixed operation/contracts registry | Describes only this boundary |
| help.query | combined `truesystems_api.help.answer_help` | Authored lexical help; citations are not semantic proof |
| sensory.inspect | TrueCore validator of TrueMachine Fusion Pack | Preserves source errors/ownership; no semantic perception or live freshness claim |
| source.classify | `truevision_intake.source_typing.classify_source` | Existing source typing; no source admission or code execution |
| media.describe | `truevision_runtime.state_language.build_state_language` | Describes declarations; does not prove or execute media capability |
| worker.invoke | registered TrueCore runner and fixed eligible worker manifest | Returns `truecore.worker_result@1`; does not create an operator answer |

The source classifier classifies filenames/content formats; its internal format
handling must not be confused with rewriting exact source anchors. The media
descriptor's stage/behavior inference is kept under DECLARATION_NOT_EXECUTION_PROOF.
It is not promoted into a worker permission or an artistic judgment.

Imports are fixed in TrueCore and checked to come from this worktree. The host
does not dispatch via the old control-api runtime. The separate direct development
API is not exposed to this JSONL producer. A hostile independently privileged
process still requires OS isolation; this application transport is not a sandbox.

## Effects, receipts and disabled work

Workers read host-bound regular files, check hashes and budgets, and return JSON.
The transport writes responses only to stdout. Fixture files/reports are external
test artifacts. Receipt hashes cover results and stated scope; they are neither
authorization signatures nor guarantees of observed real-world truth.

Capture, rendering, playback, transcription, desktop/security actions, dataset
mutation and training are unconnected and rejected. The first worker bridge is
limited to the read-only repository-graph family described in
`docs/MODEL_REGISTERED_WORKER_BRIDGE.md`. The 94 media file surfaces
remain inventory records, not 94 registered workers. To add one later, require
its own contract, authorization, isolated acceptance, failure/retry tests and
registration. Do not expose all catalog entries through dynamic dispatch.

## Acceptance

External `test_boundary.py` exercises real TrueMachine engine/storage with
fixture collectors. `test_model_host.py` exercises existing component readers,
real subprocess transport, cross-process replay, permission denials, malformed
input, source limits and absence of alternate tools. No neural model participates
in these protocol/worker tests. Passing transport tests does not imply model skill.
