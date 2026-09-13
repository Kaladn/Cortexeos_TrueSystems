# Context-Cloud Adjustments and Traversal Trial

## Purpose

This document records the corrected text-only structure for individual anchors, sentence clouds, paragraph clouds, and dataset-wide address fields. It also demonstrates boil-up and boil-down traversal using *The Basement*.

This is an observational addressing and relationship system. A `6-1-6` cloud is a graph view over preserved source addresses, not a mandatory compute shape, semantic weight, or probability of truth.

## 1. Preserved source hierarchy

Every text occurrence remains traceable through this hierarchy:

```text
dataset
└── document
    └── block / paragraph
        └── sentence
            └── item
                └── individual anchor occurrence
```

The minimum address is:

```text
dataset_id
document_id
block_id
paragraph_ordinal
sentence_id
sentence_ordinal_document
sentence_ordinal_block
item_ordinal_sentence
anchor_ordinal_sentence
exact_source_span
```

The address identifies an occurrence, not merely a normalized word. Two appearances of `sword` are two anchor occurrences with separate addresses. A normalized anchor identity may connect them, but it must never replace either occurrence or its provenance.

## 2. Corrected cloud boundaries

### Sentence cloud

- Center: one sentence.
- Neighborhood: up to six prior and six following sentences.
- Hard boundary: owning paragraph/block.
- The cloud contracts naturally at both block edges.
- It never borrows a sentence from another paragraph.

### Paragraph cloud

- Center: one complete paragraph/block.
- Neighborhood: up to six prior and six following paragraphs.
- Hard boundary: owning document.
- It must cross paragraph/block borders while walking through the document.
- It contracts only at the beginning and end of the document.

### Dataset field

- Connects admitted documents as one addressable relationship field.
- Cross-document relationships do not erase document borders.
- Every relationship endpoint retains dataset, document, block, sentence, item, anchor, and source-span provenance.
- Dataset relations are graph edges between owned addresses, not evidence that separate documents were originally one continuous text.

## 3. Boil-up traversal

Boil up begins with a precise occurrence and progressively widens context:

```text
anchor occurrence
→ owning sentence
→ sentence cloud
→ owning paragraph
→ paragraph cloud
→ document
→ dataset relationship field
```

### Trial: `sword`

The first `sword` occurrence in the extracted body used for this trial has this local address:

```text
document_id: the_basement
block_id: P0063
sentence_id: S00458
sentence_ordinal_block: 9
anchor_ordinal_sentence: 19
anchor_text: sword
```

Exact sentence evidence:

> She crept the rest of the way to the open doors, wishing she had thought to bring the ancient sword that grandpa had given her.

Its sentence cloud is `6-1-2`, because only two sentences remain in that paragraph after the center. The sentence cloud therefore ends at `P0063`; it does not pull sentences from `P0064` to manufacture a full right side.

Boiling upward to the paragraph level changes the view. `P0063` receives a complete `6-1-6` paragraph cloud:

```text
P0057 P0058 P0059 P0060 P0061 P0062
                         ↓
                       P0063
                         ↓
P0064 P0065 P0066 P0067 P0068 P0069
```

This wider view connects Ashley's search, the footprints, the open bulkhead, her realization that the ancient sword is needed, and the later retrieval and inspection of the sword. The individual occurrence remains unchanged; only the inspected contextual scale expands.

## 4. Boil-down traversal

Boil down begins with a broad admitted field and follows addresses toward exact evidence:

```text
dataset relationship field
→ selected document
→ paragraph cloud
→ selected paragraph
→ sentence cloud
→ selected sentence
→ exact anchor occurrence and source span
```

### Trial: sword-introduction scene

1. Select paragraph cloud centered on `P0063`.
2. Observe the cross-block progression from search and environmental evidence into weapon retrieval.
3. Select the center paragraph `P0063`.
4. Select sentence `S00458` from its contained sentence cloud.
5. Resolve `sword` at anchor ordinal `19`.
6. Return the exact sentence and its complete provenance address as evidence.

The broad graph locates the relevant scene, but the final support comes from the exact occurrence. A paragraph-level relationship is not permitted to substitute for the underlying sentence or anchor evidence.

## 5. What the trial changed

The earlier prototype already allowed paragraph clouds to cross block boundaries inside the document. The required adjustment is to make the complete hierarchy and traversal law explicit:

| Level | Center | Traversal boundary | Function |
|---|---|---|---|
| Anchor | Exact text occurrence | Sentence/source span | Precise evidence address |
| Sentence cloud | Sentence | Paragraph/block | Proposition and local transition context |
| Paragraph cloud | Paragraph/block | Document | Scene, argument, or procedural context |
| Dataset field | Provenance-owned address | Admitted dataset | Cross-document recurrence and relationship discovery |

The same stored evidence supports both traversal directions. The system does not need duplicate text for boil up and boil down; it needs bidirectional indexes over stable addresses.

## 6. Required indexes

```text
anchor identity → occurrence addresses
occurrence address → sentence
sentence → owning block
sentence → contained sentence cloud
block → document-wide paragraph cloud
document → dataset ownership
relationship edge → both endpoint addresses and signed offset
```

Reverse indexes provide downward traversal from every parent to its children. Forward ownership links provide upward traversal from every child to its parents.

## 7. Boundaries retained for the next implementation

- Text only for this stage.
- Punctuation is preserved as source structure but contributes no anchor counts.
- No silent alias merging, stemming, singular/plural merging, or inferred entity resolution.
- No arbitrary semantic weights.
- Signed offsets remain observations.
- `6-1-6` is one inspectable graph projection and can later be compared with adaptive geometries.
- Document provenance survives every dataset-level connection.

## Conclusion

The adjustment produces one provenance-preserving address field with multiple entry points. Retrieval may begin with an individual anchor, sentence cloud, paragraph cloud, document, or dataset relationship. Boil up discovers broader structure; boil down resolves that structure back to exact evidence.
