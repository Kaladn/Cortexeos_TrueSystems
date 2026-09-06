# Codex–TrueSystems operator and handoff contract

Status: production architecture contract.

## Role law

```text
human or questionnaire
  -> operator LLM
  -> bounded TrueSystems work order
  -> deterministic evidence and operation packet
  -> operator LLM
  -> human response
```

The operator LLM owns interpretation, request decomposition, operation
selection, evidence inspection, reasoning, and communication. TrueSystems owns
admitted datasets, dataset-local symbols, occurrences, signed 6-1-6
relationships, source coordinates, deterministic operations, and receipts.

TrueSystems is not required to interpret an arbitrary conversational request or
compose the final textual answer. The operator must not impersonate
TrueSystems, manufacture its evidence, or silently repair its failures.

## Work-order law

The operator preserves the original request byte-for-byte and rearranges its
intent into a bounded work order. Rearrangement may expose:

- complete subject or object identities;
- one evidence obligation per requested property, value, relation, population,
  outcome, date, quantity, unit, comparison, or polarity;
- the deterministic operation requested after the evidence is gathered;
- the required return shape.

The work order must distinguish two query sources:

1. `DIRECT_REARRANGEMENT`: exact material from the original request, reordered
   or separated into independent evidence obligations;
2. `OPERATOR_EXPANSION`: an operator-supplied alternate expression intended to
   locate the same evidence obligation.

An expansion never becomes dataset truth. It must retain its author, reason,
and relationship to the original obligation. Benchmark answers, expected
documents, expected paths, and expected anchors are forbidden work-order
inputs.

Every work order retains at least:

```text
schema
work_order_id
original_request
original_request_sha256
dataset_id
subjects
evidence_obligations
bounded_queries
operation
requested_result
ambiguities
operator_identity
benchmark_knowledge_used
canonical_record_sha256
```

The exact original request and every query string remain unchanged.

## TrueSystems execution law

TrueSystems resolves each bounded request through the selected dataset's own
lexicon, occurrences, signed relationships, structures, binaries, and source
coordinates. It returns evidence locations and may execute only an existing
declared deterministic capability.

TrueSystems must not rewrite the human request, invent an evidence obligation
or operator expansion, use benchmark judgments to select evidence, convert a
retrieval candidate into proof without source-bound support, or compose the
final human response.

## Evidence handoff law

The handoff packet preserves, when available:

```text
work_order_id
dataset_id
obligation_id
bounded_query_id
evidence_status
exact admitted strings
dataset-local symbols
relationship measurements and paths
document and parent-object identity
block, line, sentence, object, and occurrence coordinates
citation identity
source hash
deterministic operation result and receipt
missing or ambiguous evidence
device receipt
```

Permitted evidence states are `COMPLETE_EVIDENCE`, `PARTIAL_EVIDENCE`,
`AMBIGUOUS_EVIDENCE`, `NO_EVIDENCE`, and `OPERATION_FAILED`.

Candidate locations alone are not a factual answer. The operator inspects the
returned source field, determines whether the evidence obligations are
satisfied, and communicates only what that packet supports.

### Executable EvidenceNeed boundary

The public TrueMem retrieval call accepts only `truemem_evidence_need@1` and
must reject raw questions or claims before reading retrieval artifacts. Every
need contains `subject`, `relation`, non-empty `qualifiers`, `quantity`, and
`requested_proof_form`. Each field carries explicit admitted-anchor
alternatives. The retrieval packet enumerates exact subject occurrences and
their signed 6-1-6 clouds, intersects required fields for the requested proof
form, and returns evidence locations without TopK or answer generation.

An answer-shaped benchmark string may be retained outside retrieval as the
operator's original request, but it cannot occupy the EvidenceNeed argument.

The quantity field is always present. When the request contains no quantity,
it must be encoded as `{"field":"quantity","anchors":[],"required":false}`;
retrieval must not manufacture a numeric constraint.

## Benchmark boundary

A benchmark judgment is opened only after the complete work-order and
prediction artifacts have been closed and hashed. It may evaluate retrieval or
the operator's evidence decision. It may never construct a work order or alter
an already returned packet.

Direct human-request-to-TrueSystems runs remain valid diagnostic baselines, but
they are not measurements of the complete operator architecture and must be
labelled `DIRECT_QUERY_BASELINE_NOT_OPERATOR_LOOP`.
