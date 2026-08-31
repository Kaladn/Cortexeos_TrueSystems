# Anchor Structure Sheet Contract

The anchor structure sheet is a temporary query-scoped description of how a
question must be traversed. It is available to every admitted TrueMem dataset.
It is not training data, an answer, or a dataset-specific ranking rule.

## Inputs

- The exact question string and its exact complete-word/structural anchors.
- Explicit ruling anchor groups supplied by the sitting operator model.
- Exact question-anchor coordinates for every group.
- A bounded operation and its exact question-anchor coordinates.
- The evidence fields that each group must supply.

TrueMem verifies these inputs. It does not infer names, silently join separated
words, lowercase source identity, or invent missing anchors.

## Selection law

An exact group matches only a contiguous occurrence in an admitted block. A
`parent_title` group matches only inside the block's native parent/title region.
When ruling groups are supplied, a selected evidence chain must cover every
group. A chain that does not cover them is ineligible, regardless of generic
anchor pressure. The native signed relationships and native rank measurements
remain visible in the result receipt.

If no eligible chain exists, the selector returns
`REQUIRED_RULING_PATH_NOT_FOUND`. It does not fall back to an unrelated result.

## Authority boundary

- Stored counts, symbols, postings, and relationships are never modified.
- The sheet contains no answer.
- The sheet creates no local fact, operation, identity, or model authority.
- Deterministic operator skills may run only on cited values returned by the
  selected evidence.
- The overlay expires with the query.

## Capability execution

A capability cannot execute directly from prose or a citation label. Each
operand must bind to an admitted evidence record and retain:

- citation ID and block ordinal;
- file and line coordinates;
- verified block SHA-1 and SHA-256;
- exact identity UTF-8 byte span;
- exact value UTF-8 byte span or spans;
- deterministic value type and parsing receipt.

TrueMem derives the typed operand from the verified source span. A caller may
not submit a typed number or date as authority. Every required evidence field
declared by the sheet must be satisfied exactly once. Missing, duplicated,
undeclared, stale, or byte-inexact evidence fails closed before calculation.

When one block covers every ruling group, selection returns that one block. A
multi-block pair is constructed only when no single block covers the complete
ruling field. This prevents an unrelated second block from being added merely
to satisfy a fixed result cardinality.

Every capability attempt returns `truemem_capability_authority_receipt@1` with
either `EXECUTED` or `REJECTED`, a stable failure code, and whether an operation
actually ran. Rejection is an auditable result; it is not replaced by a guess.

The device boundary is explicit. Posting lookup, signed relationship matching,
ruling-group qualification, candidate construction, and ranking remain XPU
tensor work and fail if tensors leave XPU. CPU work is limited to source-file
loading, coordinate/receipt serialization, exact UTF-8 byte and hash checks,
and bounded scalar/date/count/equality/set operations. This boundary is not a
fallback path.

The native implementation is:

- `truemem.engine.query_ruling`
- `truemem.engine.xpu_relationship_index`
- `truemem.engine.operator_skills`
- `truemem.engine.evidence_operands`

Benchmark and application adapters may call this implementation. They may not
carry private copies of its relationship or ruling laws.
