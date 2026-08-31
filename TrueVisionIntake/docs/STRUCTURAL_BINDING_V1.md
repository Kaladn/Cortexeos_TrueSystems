# TrueVision Structural Binding v1

## Authority and insertion point

TrueVision Intake / DocuFilm is the only document and glyph intake authority.
Structural Binding v1 executes in that admission path after exact source text is
available and before TrueMem allocates the dataset's active six-byte symbol
range.

The pre-v1 command path in `TrueMem/src/truemem/engine/pipeline.py` reads text
and constructs anchors directly.  It labels its receipt as DocuFilm intake but
does not call `truevision_intake.docufilm_truemem`.  Structural Binding v1 must
close that handoff; it must not create another TrueMem language intake.

## Preserved authority

- Exact source bytes, source hashes, blocks, sentences, anchors, punctuation
  boundaries, glyph state, and native coordinates remain unchanged.
- Existing anchor observations and signed `-6..-1,+1..+6` relationship counts
  remain unchanged.
- Punctuation participates in exact span reconstruction and boundary structure
  only. It contributes no structural ranking, relationship pressure, or vote.
- No LLM, embedding, statistical NER, statistical dependency parser, remote
  service, or model-generated annotation is permitted.
- Semantic subtypes require explicit source cues. Otherwise the compiler emits
  a general or ambiguous structure.

## Dataset-local symbol law

Every accepted structural parent has a deterministic structure key. The key is
included in the same frozen dataset allocation input as ordinary anchors and
therefore receives a symbol from the existing
`workspace_monotonic_integer_6b` authority. Structure symbols are never reused
across datasets or exported as meaning.

Structure keys do not become ordinary anchor occurrences and do not change
existing anchor or 6-1-6 counts. They are stored in the lexicon with zero direct
anchor observations and are referenced by the structural graph.

## Logical records

### Structure

```text
structure key and dataset-local symbol
parent/source-object key
block and sentence coordinates
anchor start and count
UTF-8 byte start and length
kind and status
exact source hash and provenance
```

### Child

```text
parent structure symbol
child symbol
child ordinal
child role
```

### Explicit relation

```text
subject structure symbol
exact relation-phrase structure symbol
object structure symbol
source occurrence and direction
status and provenance
```

The relation phrase is an exact source-resolvable parent structure. A later
relation class may supplement it but may never replace the source phrase.

## Initial deterministic structures

The first compiler is intentionally bounded:

- exact named structures, including internal glue words;
- quoted structures;
- parenthetical structures;
- dates;
- quantities and units;
- explicit alias forms;
- source-explicit relation phrases; and
- source parent/child containment.

Specific types such as person, city, film, event, or organization are emitted
only when an explicit cue in the same source construction proves the subtype.

## Query symmetry

Questions use the identical compiler as a temporary overlay. Temporary
structures receive no permanent dataset symbols and cannot modify admitted
counts, relationships, or source. A caller may select among verified temporary
structures but cannot invent or join spans.

## Physical storage decision boundary

The logical records above are authoritative before physical file topology.
Storage selection must measure size and access. The preferred first candidate
is one sectioned structural graph artifact plus a manifest, because source text,
anchors, blocks, and citations already exist elsewhere and must not be copied.

## TrueMem consumer boundary

TrueMem may load, verify, project, traverse, bind, and calculate over the
compiled substrate. It must not reinterpret source text. Traversal Layer v1 is
versioned above the frozen Authority Layer v1.

## M4.1 occurrence and local-cloud law

A structural form, an exact occurrence, and its admitted parent object are
different identities. Every stored relation therefore preserves the exact
subject, relation-phrase, and object occurrence IDs. Equal structural form does
not prove equal referent.

The first context cloud is the current parent object. A sentence-initial
reference subject such as `It` may carry the native parent identity only within
that same admitted object. This bounded carry retains the exact reference
surface and relation phrase in the receipt; it does not perform general pronoun
resolution or corpus-wide inference.

Native parent identity regions come from the source object's first-line native
identity. A mechanically qualified title may additionally expose its exact base
component (for example, the component before a comma or parenthetical). Body
mentions may cross objects only through an exact complete-structure binding to
one such native identity component. Zero matches remain unbound; multiple
matches remain ambiguous.

Traversal uses exact occurrence IDs as its frontier:

```text
exact occurrence
-> exact relation occurrence
-> exact object occurrence
-> verified parent-reference binding
-> target parent object's local occurrence cloud
```

The forbidden operation is `shared form -> every corpus posting`. Gathered
occurrences and their citations are handed off as an evidence workspace. This
layer does not form a textual answer.
