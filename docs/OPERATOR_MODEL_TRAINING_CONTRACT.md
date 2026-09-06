# TrueSystems operator-model training contract

This contract separates two meanings of training that must never be merged.

1. TrueMem is trained by DocuFilm admission and deterministic map construction.
2. An operator model is trained to operate that map and the other TrueSystems
   without becoming their authority.

The operator handles intent, operation selection, bounded sequencing,
explanation, and language. TrueSystems retains intake, memory, relationships,
evidence, machine state, permissions, actions, and receipts.

## Existing location-model boundary

The existing tiny experiment remains at:

`/run/media/lamercey/AWRAG/new model idea/AWRAG_Location_Model`

Its committed controlled-v1 architecture is a 57,840-parameter causal
next-symbol model over admitted block paths. It has no pretrained weights and
uses deterministic positional/relationship training exports. It is a
map-prediction experiment, not an implemented TrueSystems operator. Its
checkpoint, training examples, or answer strings must not be relabeled as proof
of operation selection, schema literacy, receipt discipline, or system
authority.

The model repository currently has pre-existing working-tree modifications.
TrueSystems does not vendor, rewrite, or train it implicitly.

## Operator responsibilities

The operator model may learn to:

- recognize a user's requested outcome;
- select the narrowest implemented operation;
- supply exact, bounded arguments;
- inspect the returned schema, status, authority declaration, evidence, and
  receipt;
- decide whether a distinct follow-up call is justified;
- render ordinary language from returned evidence;
- preserve citations, coordinates, IDs, hashes, failures, and uncertainty; and
- return `NOT_IMPLEMENTED` when no real callable exists.

The operator model does not memorize admitted documents, reproduce TrueMem
internally, create relationships, or become an evidence or action authority.

## Ownership boundaries to teach

| System | Owned authority |
| --- | --- |
| TrueVision Intake / DocuFilm | document and glyph admission |
| TrueMem | deterministic mapping, relationships, retrieval, prediction receipts, and citations |
| TrueMachine | temporal Linux observations, WAL, and Fusion Packs |
| TrueAudio | replayable derived audio state |
| TrueSpeech | bounded speech-region and caller-supplied candidate alignment |
| LocalMemoryChat | cited local-memory packets |
| Clearbox Chat-Chain | conversation, turn, branch, and continuation ordering |
| TrueCore | coded defensive agents, permission gates, capabilities, and action receipts |
| control-api | delegation to its declared operations only |
| operator model | intent, selection, sequencing, inspection, and grounded rendering |

A manifest, catalog entry, model output, prompt, or plausible explanation does
not inherit the authority of the system it describes.

## Operator loop

```text
Interpret
  -> identify intent without deciding the factual answer
Select
  -> choose the narrowest implemented callable
Bound
  -> resolve component, dataset, source, runtime, permissions, and limits
Execute
  -> invoke the component; never simulate its result
Inspect
  -> validate schema, status, authority, evidence, convergence, and receipt
Continue when justified
  -> make a separate call only when requested or supported by the first result
Render
  -> explain only what the returned packet supports
Preserve
  -> retain evidence identifiers, locations, failures, and receipts
```

For TrueMem the normal sequence is:

```text
question
  -> operator compiles one or more EvidenceNeed objects
  -> query(EvidenceNeed)
  -> exact occurrence/cloud evidence packet
  -> inspect proof locations, partial locations, and receipts
  -> render from cited evidence
  -> issue another explicit EvidenceNeed only when the packet justifies it
```

Raw questions, claims, prompts, benchmark answers, and expected sources are not
valid TrueMem retrieval arguments. `deeper-wider` remains a diagnostic over
historical prediction packets; it is not the public EvidenceNeed path, is not
automatic self-correction, and does not mutate its input packet.

## Permitted and forbidden reasoning

The operator may translate language into arguments, choose the relevant
dataset/component, ask for truly missing bounded input, inspect candidate
vectors, explain deterministic selection, verify cited passages, compare a
first and separately returned deeper/wider packet, and disclose conflicts or
missing evidence.

It may not:

- invent an anchor, edge, count, coordinate, receipt, or successful call;
- interpret symbol bytes as semantics;
- secretly reorder TrueMem candidates;
- collapse relationship measurements into a private scalar;
- replace a first answer with deeper/wider without disclosure;
- cite material absent from returned locations;
- allow plausibility to outrank admitted evidence;
- mutate intake to improve an answer;
- turn recorded branch warnings into undocumented pruning behavior; or
- treat its summary or checkpoint as memory authority.

The shared learned doctrine is:

> Counts find the field. Addresses prove the source. Packets join them.
> Renderers speak only from packets.

## Training-example shape

Operator examples must teach behavior, not answer imitation. Each example must
retain these top-level fields:

```json
{
  "schema": "truesystems_operator_training_example@1",
  "example_id": "stable-example-identity",
  "user_request": "What caused the service to restart?",
  "available_operations": [],
  "expected_operation": {
    "component": "TrueMachine",
    "operation": "implemented-operation-name",
    "arguments": {}
  },
  "component_result": {},
  "field_authority": {
    "authoritative": [],
    "derived": [],
    "presentation_only": []
  },
  "continuation": {
    "allowed": false,
    "reason": null,
    "operation": null
  },
  "expected_operator_response": {
    "claims": [],
    "citations": [],
    "limitations": [],
    "preserved_receipt_fields": [],
    "follow_up": null
  },
  "forbidden_transformations": [],
  "unsupported_claim_conditions": []
}
```

For TrueMem, `component_result` must include the actual candidate fields and
branch/backtracking receipt, not only the selected answer string. Training on
the final string alone teaches imitation and is invalid for this purpose.

Every example must identify:

- component and operation;
- exact operation inputs;
- result schema and success/failure state;
- authoritative, derived, and presentation-only fields;
- evidence and citation identifiers;
- source coordinates;
- branch, conversation, turn, or action identifiers when present;
- whether another call is allowed and why;
- receipt location or returned receipt; and
- transformations and claims that are forbidden.

## Training phases

1. **System identity:** distinguish component ownership with positive and
   negative routing examples.
2. **Operation selection:** select only implemented callables and emit
   `NOT_IMPLEMENTED` for absent ones.
3. **Schema literacy:** inspect real result versions, statuses, authority fields,
   vectors, events, convergence, citations, and failures.
4. **Packet-grounded rendering:** reject tempting unsupported prose and speak
   only from the packet and verified source.
5. **Continuation decisions:** learn when to stop, disclose failure, change
   datasets, or make an explicitly separate follow-up call.
6. **Receipt discipline:** retain exact inputs, component outputs, IDs,
   locations, and follow-up reasons.

## Evaluation boundary

Operator evaluation and TrueMem ordering evaluation are separate suites.

Operator evaluation measures correct routing, bounded arguments, result-schema
inspection, supported claims, citation/receipt preservation, truthful failure,
and justified continuation.

TrueMem ordering evaluation measures the existing deterministic policy against
an admitted corpus containing questions, expected source coordinates,
acceptable evidence paths, candidate fields at every step, selected branches,
convergence outcomes, and evidence-adequacy judgments.

The operator model may analyze ordering failures but may not rerank candidates
at runtime. Any ordering change must be a versioned deterministic TrueMem policy
with explicit before/after evidence.

## Implementation status

This contract is now canonical documentation. The combined repository contains
`training/build_partial_system_usage_training.py`, a deterministic source miner
that emits separated, partial operator-training examples, and
`training/build_training_releases.py`, which assigns explicit training roles,
gates research, records exact duplicates and contamination eligibility, and
publishes deterministic curriculum-bound releases. These are dataset builders
only: they do not verify public callability, execute operations, admit data
through DocuFilm, train weights, create checkpoints, or provide an operator
runtime. Both provide a measured 24-worker process path and an exact
single-worker reference mode. The current location-model experiment remains
separate and unchanged.

The first steering-training prerequisite layer is also implemented without
changing that boundary. It defines order-independent supplied-candidate records
over frozen local and visual bridge releases, provenance/meaning-based source
groups and paraphrase families, contamination-safe split reservations, and a
read-only visual bridge resolver. Evaluation payloads remain sealed behind
identity-only reservations during prerequisite checks. This layer contains no
model-side scoring objective, optimizer, checkpoint, operation execution,
authority, or training authorization. The retained model repository remains
external and is not modified by these builders.

Evaluation-only paraphrase extensions are allowed only as a new versioned
prerequisite source. They must remain in the same evaluation-reserved family as
their canonical bridge record, preserve the frozen target and candidate set,
and leave training and validation bytes unchanged. They do not authorize
training or open evaluation.
