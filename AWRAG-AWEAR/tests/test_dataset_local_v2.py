from collections import Counter

from awrag.engine.dataset_local_v2 import (
    ANCHOR_RECORD,
    FORMAT_SCHEMA,
    LEGACY_FORMATS,
    RELATION_RECORD,
    SYMBOL_BYTES,
    allocate_dataset_local_symbols,
    encode_counts,
    validate_resolution,
)


def fixture():
    anchors = Counter({"alpha": 2, "beta": 1, "gamma": 1})
    relations = Counter({("alpha", "beta", 1): 1, ("beta", "alpha", -1): 1})
    postings = [("alpha", 0, 0), ("beta", 0, 1)]
    return anchors, relations, postings


def test_authoritative_format_is_dataset_local_u32_and_legacy_is_explicit():
    assert SYMBOL_BYTES == 4
    assert FORMAT_SCHEMA == "awear_dataset_local_u32@1"
    assert "awrag_dataset_6b@1" in LEGACY_FORMATS


def test_allocation_and_binary_output_are_deterministic():
    anchors, relations, postings = fixture()
    first = allocate_dataset_local_symbols(anchors)
    second = allocate_dataset_local_symbols(Counter(dict(reversed(list(anchors.items())))))
    assert first == second
    assert first["mapping"] == {"alpha": 1, "beta": 2, "gamma": 3}
    assert encode_counts(first["mapping"], anchors, relations, postings) == encode_counts(second["mapping"], anchors, relations, postings)


def test_every_emitted_symbol_resolves_and_record_widths_are_four_byte():
    anchors, relations, postings = fixture()
    allocation = allocate_dataset_local_symbols(anchors)
    artifacts = encode_counts(allocation["mapping"], anchors, relations, postings)
    result = validate_resolution(allocation["lexicon"], artifacts)
    assert result["status"] == "PASS"
    assert result["unresolved_symbols"] == []
    assert ANCHOR_RECORD.size == 12
    assert RELATION_RECORD.size == 14
    assert len(artifacts["anchor_counts.awbin"]) == len(anchors) * ANCHOR_RECORD.size


def test_dataset_local_values_are_not_claimed_cross_dataset_compatible():
    anchors, _, _ = fixture()
    lexicon = allocate_dataset_local_symbols(anchors)["lexicon"]
    assert lexicon["symbol_scope"] == "dataset_local"
    assert lexicon["legacy_symbol_compatibility"] == "NONE_VALUES_MUST_NOT_BE_COMPARED"
