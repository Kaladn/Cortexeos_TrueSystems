# SYL five-channel training addition

## Decision

The five-channel design is a current extension to the deterministic evidence
representation. It is not a replacement for TrueMem's admitted anchor stream,
6-1-6 signed relationship graph, eight-field candidate vector, citations, or
the frozen supplied-candidate steering boundary.

The first trainable addition is a scorer that receives only candidates already
supplied by a frozen deterministic release. For each supplied candidate it may
compare five independently preserved evidence channels:

1. **Source object** — exact admitted source/block/object identity, coordinates,
   occurrence support, and source provenance.
2. **Stable anchor** — exact anchor identity and observed count/support at the
   candidate location.
3. **Anchor sequence** — signed `-6..-1,+1..+6` lanes, ordered path evidence,
   distance stability, direction, and sequence coordinates.
4. **Derived symbol fragment** — a versioned deterministic fragment derived
   only from admitted anchors and coordinates, retaining its derivation receipt.
5. **Grouped symbol pattern** — a versioned deterministic grouping of observed
   fragments/paths, retaining every member identity and grouping receipt.

No channel is semantics by itself. The canonical builder now derives channel
four as exact contiguous two- and three-anchor subsequences of the admitted
stream. Channel five contains only identical fragments observed at least
twice. Neither derivation assigns meaning. Both retain members, occurrence
coordinates, support, and receipts.

## Canonical candidate packet

```json
{
  "schema": "truesystems_syl_candidate_evidence@1",
  "candidate_bridge_id": "existing-frozen-id",
  "candidate_set_hash": "frozen-hash",
  "channels": {
    "source_object": {"status": "observed", "evidence": []},
    "stable_anchor": {"status": "observed", "evidence": []},
    "anchor_sequence": {"status": "observed", "signed_lanes": {}, "paths": []},
    "derived_symbol_fragment": {"status": "observed", "fragments": []},
    "grouped_symbol_pattern": {"status": "observed", "patterns": []}
  },
  "existing_relationship_vector": {
    "Local": null,
    "Back": null,
    "Cloud": null,
    "Forward": null,
    "Support": null,
    "Lift": null,
    "DistanceStability": null,
    "Direction": null
  },
  "provenance": {},
  "forbidden_outputs": [
    "identifier", "hash", "relationship", "operation", "evidence", "authority"
  ]
}
```

`null` and `unavailable` are meaningful. Missing evidence cannot be imputed
from language, generic Hugging Face data, model output, or nearby candidates.

## Model boundary

The model receives a phrase plus a finite frozen candidate set and its verified
packets. It may return only the index of one supplied candidate or an explicit
non-target status. Channel values remain separate at the handoff and in all
receipts. The training objective may learn a comparison over the channels, but
the released evidence must never be replaced by one unexplained scalar.

TrueMem remains evidence authority. The model cannot create anchors, fragments,
patterns, paths, meanings, bridge IDs, visual identities, operations, or
authority. Generic external data remains `NOT_LOCAL_TRUTH` and cannot populate
any local channel without a separately verified bridge.

## First experiment gate

The bounded steering experiment must not silently consume this new design.
Before its first optimizer update:

1. freeze this packet schema and exact field semantics;
2. implement deterministic builders for channels one through three from current
   admitted artifacts;
3. leave channels four and five explicitly unavailable in experiment one;
4. build identical packets with one and 24 workers and require byte identity;
5. prove every evidence item resolves to its frozen source coordinate/hash;
6. freeze the scoring adapter, tokenizer, seed, device, optimizer, stopping rule,
   maximum updates, and checkpoint-selection rule;
7. keep evaluation reservations sealed until the checkpoint and all choices are
   frozen; and
8. train outside every source repository, then revoke the single authorization.

The deterministic construction is implemented by
`TrueCore/truecore/training/syl_evidence.py`. It admits each exact frozen bridge
phrase through DocuFilm, assigns dataset-local TrueMem symbols, derives all five
channels, and runs non-learned lexicographic ablations. Its first fixed release
did not beat the unchanged resolver: the strongest channel combination reached
5/14 versus the 6/14 resolver baseline. Identical visual phrases bound to
different frozen targets remain structurally ambiguous. No further training is
authorized by this result.

## Later experimental matrix

After an accepted five-channel builder exists, compare fixed frozen releases:

- channels 1-3 baseline;
- baseline plus channel 4;
- baseline plus channel 5;
- all five channels;
- deterministic resolver baseline with no learned scorer.

Report local and visual domains separately, preserve unseen-paraphrase and
refusal reservations, and require invented/invalid selections and authority
violations to remain zero. No training loss may be presented as generalization.
