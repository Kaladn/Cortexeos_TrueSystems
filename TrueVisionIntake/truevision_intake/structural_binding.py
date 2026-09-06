"""Deterministic exact-span structural compilation for DocuFilm intake.

This module does not interpret source with a model.  It records only structures
that can be reconstructed from exact bytes and bounded source-form rules.
"""

from __future__ import annotations

import hashlib
import json
import re
from array import array
from bisect import bisect_left, bisect_right
from typing import Any


SCHEMA = "truevision_structural_binding@2"
COMPILER = "truevision_deterministic_text_structure_compiler@2"

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
DATE_RE = re.compile(
    rf"\b(?:[0-3]?\d\s+(?:{MONTHS})\s+\d{{4}}|(?:{MONTHS})\s+[0-3]?\d(?:,\s*\d{{4}})?|\d{{4}})\b"
)
QUANTITY_RE = re.compile(
    r"(?<![\w.])[+-]?(?:\d+(?:,\d{3})*|\d*\.\d+)(?:\s*(?:%|percent|percentage|days?|weeks?|months?|years?|hours?|minutes?|seconds?|words?|miles?|kilometers?|kg|g|lb|MB|GB|TB))?\b",
    re.IGNORECASE,
)
ALIAS_RE = re.compile(
    r"\b(?:also known as|also called|known as|formerly called|other name(?:d)?|alias(?:ed)? as)\b",
    re.IGNORECASE,
)
EXPLICIT_TYPE_CUES = {
    "actor": "PERSON_ROLE",
    "actress": "PERSON_ROLE",
    "author": "PERSON_ROLE",
    "composer": "PERSON_ROLE",
    "player": "PERSON_ROLE",
    "city": "PLACE_CITY",
    "town": "PLACE",
    "country": "PLACE_COUNTRY",
    "film": "WORK_FILM",
    "movie": "WORK_FILM",
    "book": "WORK_BOOK",
    "novel": "WORK_BOOK",
    "war": "NAMED_EVENT",
    "battle": "NAMED_EVENT",
    "company": "ORGANIZATION",
    "organization": "ORGANIZATION",
    "university": "ORGANIZATION",
}
RELATION_WORDS = frozenset({
    "am", "are", "became", "become", "becomes", "been", "being", "born",
    "called", "contained", "contains", "died", "founded", "grew", "had",
    "has", "have", "includes", "is", "known", "located", "married",
    "named", "played", "published", "ran", "served", "starred", "stops",
    "took", "was", "were", "wrote", "written",
})
REFERENCE_SUBJECTS = frozenset({"he", "her", "hers", "him", "his", "it", "its", "she", "their", "theirs", "them", "they"})


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def structure_key(kind: str, exact_text: str, *, identity_anchors: list[str] | None = None) -> str:
    identity = stable_hash({
        "kind": str(kind),
        "identity_anchors": list(identity_anchors) if identity_anchors is not None else None,
        "exact_text": None if identity_anchors is not None else str(exact_text),
    })
    return f"object:structure:{str(kind).casefold()}:{identity}"


def compile_text_structures(
    text: str,
    *,
    source_identity: str,
    block_ordinal: int = 0,
    temporary_query_overlay: bool = False,
) -> dict[str, Any]:
    """Compile deterministic structures without changing the source stream."""

    source = str(text)
    occurrences = _anchor_occurrences(source)
    candidates: list[dict[str, Any]] = []
    candidates.extend(_named_candidates(source, occurrences))
    candidates.extend(_regex_candidates(source, DATE_RE, "DATE"))
    candidates.extend(_regex_candidates(source, QUANTITY_RE, "QUANTITY"))
    candidates.extend(_parenthetical_candidates(source))
    candidates.extend(_quoted_candidates(source))
    title_end = source.find("\n")
    if title_end < 0:
        title_end = len(source)
    if title_end > 0:
        candidates.append({"char_start": 0, "char_end": title_end, "kind": "NATIVE_IDENTITY_REGION", "status": "VERIFIED_STRUCTURE"})
        title_text = source[:title_end]
        qualifier = re.search(r"\s*(?:,|\()[^\n]*$", title_text)
        if qualifier and qualifier.start() > 0:
            candidates.append({
                "char_start": 0,
                "char_end": qualifier.start(),
                "kind": "NAMED_STRUCTURE",
                "status": "VERIFIED_NATIVE_IDENTITY_COMPONENT",
            })
    candidates = _deduplicate_candidates(candidates)
    candidates = _apply_explicit_type_cues(source, candidates)

    parent_object_id = stable_hash({"source_identity": str(source_identity), "block_ordinal": int(block_ordinal), "kind": "PARENT_OBJECT"})
    structures: list[dict[str, Any]] = []
    occurrence_starts = [int(row["char_start"]) for row in occurrences]
    sentence_boundaries = _sentence_boundaries(source)
    byte_offsets = _utf8_prefix_offsets(source)
    for candidate in candidates:
        start = int(candidate["char_start"])
        end = int(candidate["char_end"])
        exact = source[start:end]
        anchor_children = _occurrences_within(occurrences, occurrence_starts, start, end)
        if not anchor_children:
            continue
        kind = str(candidate["kind"])
        identity_anchors = [str(row["anchor"]) for row in anchor_children if not str(row["anchor"]).startswith("boundary:")]
        key = structure_key(kind, exact, identity_anchors=identity_anchors)
        byte_start = int(byte_offsets[start])
        byte_end = int(byte_offsets[end])
        basis = {
            "structure_key": key,
            "source_identity": str(source_identity),
            "block_ordinal": int(block_ordinal),
            "byte_start": byte_start,
            "byte_end": byte_end,
            "kind": kind,
            "semantic_subtype": candidate.get("semantic_subtype"),
            "status": str(candidate.get("status") or "VERIFIED_STRUCTURE"),
        }
        structures.append({
            "schema": f"{SCHEMA}:structure",
            **basis,
            "occurrence_id": stable_hash(basis),
            "exact_text": exact,
            "exact_text_sha256": hashlib.sha256(exact.encode("utf-8")).hexdigest(),
            "char_start": start,
            "char_end": end,
            "sentence_ordinal": _sentence_ordinal_from_boundaries(sentence_boundaries, start),
            "anchor_start": int(anchor_children[0]["position"]),
            "anchor_count": len(anchor_children),
            "children": [
                {
                    "anchor": row["anchor"],
                    "anchor_position": int(row["position"]),
                    "child_ordinal": ordinal,
                    "role": "STRUCTURE_MEMBER",
                }
                for ordinal, row in enumerate(anchor_children)
            ],
            "punctuation_count_bearing": False,
            "temporary_query_overlay": bool(temporary_query_overlay),
            "parent_object_id": parent_object_id,
            "inside_native_identity_region": bool(start >= 0 and end <= title_end),
        })

    relations, relation_structures = _explicit_relations(
        source, structures, occurrences, occurrence_starts, sentence_boundaries,
        byte_offsets,
        source_identity, block_ordinal, temporary_query_overlay, parent_object_id,
    )
    structures.extend(relation_structures)
    structures.sort(key=lambda row: (int(row["byte_start"]), -int(row["byte_end"]), str(row["kind"]), str(row["structure_key"])))
    relations.sort(key=lambda row: (int(row["byte_start"]), str(row["subject_occurrence_id"]), str(row["object_occurrence_id"])))
    body = {
        "schema": SCHEMA,
        "compiler": COMPILER,
        "source_identity": str(source_identity),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "block_ordinal": int(block_ordinal),
        "temporary_query_overlay": bool(temporary_query_overlay),
        "source_text_modified": False,
        "normalization_performed": False,
        "model_used": False,
        "statistical_nlp_used": False,
        "punctuation_count_bearing": False,
        "parent_object_id": parent_object_id,
        "native_identity_byte_start": 0,
        "native_identity_byte_end": int(byte_offsets[title_end]),
        "structures": structures,
        "relations": relations,
    }
    body["compilation_id"] = stable_hash(body)
    return body


def compile_question_structures(question: str) -> dict[str, Any]:
    return compile_text_structures(
        question,
        source_identity="temporary:question:" + hashlib.sha256(question.encode("utf-8")).hexdigest(),
        temporary_query_overlay=True,
    )


def _anchor_occurrences(text: str) -> list[dict[str, Any]]:
    from truemem.engine.anchors import WORD_RE, normalize_anchor, structural_anchor

    rows = []
    for position, match in enumerate(WORD_RE.finditer(text)):
        exact = match.group(0)
        anchor = normalize_anchor(exact) if any(char.isalnum() or char == "_" for char in exact) else structural_anchor(exact)
        rows.append({
            "anchor": anchor,
            "surface": exact,
            "position": position,
            "char_start": match.start(),
            "char_end": match.end(),
        })
    return rows


def _named_candidates(text: str, occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from truemem.engine.anchors import anchor_kind

    out = []
    index = 0
    while index < len(occurrences):
        row = occurrences[index]
        surface = str(row["surface"])
        if anchor_kind(str(row["anchor"])) != "content" or not _capitalized(surface):
            index += 1
            continue
        end_index = index
        last_capital = index
        cursor = index + 1
        while cursor < len(occurrences):
            current = occurrences[cursor]
            current_surface = str(current["surface"])
            kind = anchor_kind(str(current["anchor"]))
            gap = text[int(occurrences[cursor - 1]["char_end"]):int(current["char_start"])]
            if "\n" in gap or len(gap) > 3:
                break
            if kind == "content" and _capitalized(current_surface):
                end_index = cursor
                last_capital = cursor
                cursor += 1
                continue
            if kind in {"glue", "relation"} and cursor + 1 < len(occurrences) and _capitalized(str(occurrences[cursor + 1]["surface"])):
                end_index = cursor
                cursor += 1
                continue
            if current_surface in {",", "-", "–", "—"} and cursor + 1 < len(occurrences) and _capitalized(str(occurrences[cursor + 1]["surface"])):
                end_index = cursor
                cursor += 1
                continue
            break
        end_index = max(end_index, last_capital)
        end_char = int(occurrences[end_index]["char_end"])
        if end_index + 1 < len(occurrences) and str(occurrences[end_index + 1]["surface"]) == "." and len(str(occurrences[end_index]["surface"])) <= 4:
            end_char = int(occurrences[end_index + 1]["char_end"])
        # Preserve an immediately following exact parenthetical qualifier.
        tail = text[end_char:]
        parenthetical = re.match(r"\s*(\([^\n()]{1,96}\))", tail)
        if parenthetical:
            out.append({"char_start": int(row["char_start"]), "char_end": end_char + parenthetical.end(1), "kind": "NAMED_STRUCTURE", "status": "VERIFIED_STRUCTURE"})
        out.append({"char_start": int(row["char_start"]), "char_end": end_char, "kind": "NAMED_STRUCTURE", "status": "VERIFIED_STRUCTURE"})
        # Preserve the complete group and expose its exact coordinated members.
        # This is structural decomposition, not a claim that a connective is
        # unimportant: titles such as "Parks and Recreation" retain the full
        # parent while comparison questions can still bind both named members.
        group_start = int(row["char_start"])
        group_text = text[group_start:end_char]
        for separator in re.finditer(r"\s+(?:and|or)\s+", group_text, re.IGNORECASE):
            member_spans = ((0, separator.start()), (separator.end(), len(group_text)))
            for member_start, member_end in member_spans:
                while member_start < member_end and group_text[member_start].isspace():
                    member_start += 1
                while member_end > member_start and group_text[member_end - 1].isspace():
                    member_end -= 1
                if member_end > member_start:
                    out.append({
                        "char_start": group_start + member_start,
                        "char_end": group_start + member_end,
                        "kind": "NAMED_STRUCTURE",
                        "status": "VERIFIED_COORDINATED_MEMBER",
                    })
        cue = surface.casefold()
        if cue in EXPLICIT_TYPE_CUES and end_index > index:
            out.append({
                "char_start": int(occurrences[index + 1]["char_start"]),
                "char_end": end_char,
                "kind": EXPLICIT_TYPE_CUES[cue],
                "status": "VERIFIED_STRUCTURE",
            })
        index = max(index + 1, end_index + 1)
    return out


def _regex_candidates(text: str, pattern: re.Pattern[str], kind: str) -> list[dict[str, Any]]:
    return [{"char_start": match.start(), "char_end": match.end(), "kind": kind, "status": "VERIFIED_STRUCTURE"} for match in pattern.finditer(text)]


def _parenthetical_candidates(text: str) -> list[dict[str, Any]]:
    return [{"char_start": match.start(), "char_end": match.end(), "kind": "PARENTHETICAL", "status": "VERIFIED_STRUCTURE"} for match in re.finditer(r"\([^\n()]{1,256}\)", text)]


def _quoted_candidates(text: str) -> list[dict[str, Any]]:
    patterns = (r'"[^"\n]{1,256}"', r"“[^”\n]{1,256}”", r"‘[^’\n]{1,256}’")
    out = []
    for pattern in patterns:
        out.extend({"char_start": match.start(), "char_end": match.end(), "kind": "NAMED_STRUCTURE", "status": "VERIFIED_STRUCTURE"} for match in re.finditer(pattern, text))
    return out


def _apply_explicit_type_cues(text: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in candidates:
        if row["kind"] != "NAMED_STRUCTURE":
            continue
        prefix = text[max(0, int(row["char_start"]) - 40):int(row["char_start"])].casefold()
        cue_matches = [typed for cue, typed in EXPLICIT_TYPE_CUES.items() if re.search(rf"\b{re.escape(cue)}\s+(?:of\s+)?$", prefix)]
        if len(set(cue_matches)) == 1:
            row["semantic_subtype"] = cue_matches[0]
        elif len(set(cue_matches)) > 1:
            row["status"] = "AMBIGUOUS_STRUCTURE"
    return candidates


def _occurrences_within(
    occurrences: list[dict[str, Any]],
    occurrence_starts: list[int],
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    """Return the exact ordered occurrence slice bounded by one source span."""

    first = bisect_left(occurrence_starts, int(start))
    last = bisect_left(occurrence_starts, int(end), lo=first)
    return [row for row in occurrences[first:last] if int(row["char_end"]) <= int(end)]


def _explicit_relations(text: str, structures: list[dict[str, Any]], occurrences: list[dict[str, Any]], occurrence_starts: list[int], sentence_boundaries: tuple[list[int], frozenset[int]], byte_offsets: array, source_identity: str, block_ordinal: int, temporary: bool, parent_object_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subject_objects = [row for row in structures if row["kind"] not in {"DATE", "QUANTITY", "PARENTHETICAL", "RELATION_PHRASE", "NATIVE_IDENTITY_REGION"}]
    subject_objects.sort(key=lambda row: (int(row["char_start"]), -int(row["char_end"])))
    relations = []
    relation_structures = []
    seen: set[tuple[str, str]] = set()
    for left, right in zip(subject_objects, subject_objects[1:]):
        if int(left["sentence_ordinal"]) != int(right["sentence_ordinal"]):
            continue
        if int(left["byte_end"]) > int(right["byte_start"]):
            continue
        char_left = int(left["char_end"])
        char_right = int(right["char_start"])
        phrase = text[char_left:char_right]
        words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", phrase, re.UNICODE)
        if not words or len(words) > 16 or not _has_explicit_relation_word(words):
            continue
        exact_phrase = phrase.strip()
        if not exact_phrase:
            continue
        rel_start = char_left + len(phrase) - len(phrase.lstrip())
        rel_end = char_right - len(phrase) + len(phrase.rstrip())
        phrase_children = _occurrences_within(occurrences, occurrence_starts, rel_start, rel_end)
        relation_identity = [str(row["anchor"]) for row in phrase_children if not str(row["anchor"]).startswith("boundary:")]
        rel_key = structure_key("RELATION_PHRASE", exact_phrase, identity_anchors=relation_identity)
        pair = (str(left["occurrence_id"]), str(right["occurrence_id"]))
        if pair in seen:
            continue
        seen.add(pair)
        byte_start = int(byte_offsets[rel_start])
        byte_end = int(byte_offsets[rel_end])
        relation_basis = {
            "structure_key": rel_key,
            "source_identity": str(source_identity),
            "block_ordinal": int(block_ordinal),
            "byte_start": byte_start,
            "byte_end": byte_end,
            "kind": "RELATION_PHRASE",
            "status": "VERIFIED_STRUCTURE",
        }
        relation_occurrence_id = stable_hash(relation_basis)
        relation_structures.append({
            "schema": f"{SCHEMA}:structure",
            **relation_basis,
            "occurrence_id": relation_occurrence_id,
            "exact_text": exact_phrase,
            "exact_text_sha256": hashlib.sha256(exact_phrase.encode("utf-8")).hexdigest(),
            "char_start": rel_start,
            "char_end": rel_end,
            "sentence_ordinal": int(left["sentence_ordinal"]),
            "anchor_start": int(phrase_children[0]["position"]) if phrase_children else -1,
            "anchor_count": len(phrase_children),
            "children": [{"anchor": row["anchor"], "anchor_position": int(row["position"]), "child_ordinal": ordinal, "role": "STRUCTURE_MEMBER"} for ordinal, row in enumerate(phrase_children)],
            "punctuation_count_bearing": False,
            "temporary_query_overlay": bool(temporary),
            "parent_object_id": parent_object_id,
            "inside_native_identity_region": bool(rel_end <= text.find("\n") if "\n" in text else rel_end <= len(text)),
        })
        rel = {
            "schema": f"{SCHEMA}:explicit_relation",
            "subject_structure_key": left["structure_key"],
            "subject_occurrence_id": left["occurrence_id"],
            "relation_structure_key": rel_key,
            "relation_occurrence_id": relation_occurrence_id,
            "object_structure_key": right["structure_key"],
            "object_occurrence_id": right["occurrence_id"],
            "source_identity": str(source_identity),
            "block_ordinal": int(block_ordinal),
            "sentence_ordinal": int(left["sentence_ordinal"]),
            "byte_start": int(left["byte_start"]),
            "byte_end": int(right["byte_end"]),
            "direction": "SOURCE_ORDER_FORWARD",
            "status": "VERIFIED_STRUCTURE",
            "exact_relation_text": exact_phrase,
            "normalized_relation_class": None,
            "temporary_query_overlay": bool(temporary),
            "parent_object_id": parent_object_id,
            "subject_binding_kind": "EXACT_OCCURRENCE",
        }
        rel["relation_id"] = stable_hash(rel)
        relations.append(rel)
    # Exact aliases can bridge the nearest structures on either side.
    for alias in ALIAS_RE.finditer(text):
        before = [row for row in subject_objects if int(row["char_end"]) <= alias.start()]
        after = [row for row in subject_objects if int(row["char_start"]) >= alias.end()]
        if not before or not after:
            continue
        left, right = before[-1], after[0]
        if int(left["sentence_ordinal"]) != int(right["sentence_ordinal"]):
            continue
        # The generic adjacent-structure pass normally records this already.
        # The explicit alias marker is retained on that record rather than
        # replacing its exact surface relation.
        for row in relations:
            if row["subject_occurrence_id"] == left["occurrence_id"] and row["object_occurrence_id"] == right["occurrence_id"]:
                row["explicit_alias"] = True
                row["relation_id"] = stable_hash({key: value for key, value in row.items() if key != "relation_id"})
    relations.extend(_local_context_relations(
        text, structures, occurrences, occurrence_starts, sentence_boundaries,
        byte_offsets, relation_structures, source_identity, block_ordinal, temporary,
        parent_object_id,
    ))
    return relations, relation_structures


def _local_context_relations(
    text: str,
    structures: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    occurrence_starts: list[int],
    sentence_boundaries: tuple[list[int], frozenset[int]],
    byte_offsets: array,
    relation_structures: list[dict[str, Any]],
    source_identity: str,
    block_ordinal: int,
    temporary: bool,
    parent_object_id: str,
) -> list[dict[str, Any]]:
    """Carry an explicit pronominal subject only inside its source parent.

    This is bounded local-cloud compilation.  It does not select a corpus-wide
    referent: a sentence-initial reference subject binds to the admitted native
    identity region of the same parent object.
    """
    native = [row for row in structures if row["kind"] == "NATIVE_IDENTITY_REGION"]
    if not native:
        return []
    parent = native[0]
    by_sentence: dict[int, list[dict[str, Any]]] = {}
    for row in occurrences:
        sentence_ordinal = _sentence_ordinal_from_boundaries(
            sentence_boundaries, int(row["char_start"]),
        )
        by_sentence.setdefault(sentence_ordinal, []).append(row)
    objects = [row for row in structures if row["kind"] not in {"DATE", "QUANTITY", "PARENTHETICAL", "RELATION_PHRASE", "NATIVE_IDENTITY_REGION"}]
    emitted: list[dict[str, Any]] = []
    for sentence_ordinal, anchors in sorted(by_sentence.items()):
        if sentence_ordinal <= int(parent["sentence_ordinal"]) or not anchors:
            continue
        first = anchors[0]
        if str(first["surface"]).casefold() not in REFERENCE_SUBJECTS:
            continue
        targets = [row for row in objects if int(row["sentence_ordinal"]) == sentence_ordinal and int(row["char_start"]) > int(first["char_end"])]
        if not targets:
            continue
        target = targets[0]
        phrase_start = int(first["char_end"])
        phrase_end = int(target["char_start"])
        exact_phrase = text[phrase_start:phrase_end].strip()
        words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", exact_phrase, re.UNICODE)
        if not exact_phrase or not _has_explicit_relation_word(words):
            continue
        rel_start = phrase_start + len(text[phrase_start:phrase_end]) - len(text[phrase_start:phrase_end].lstrip())
        rel_end = phrase_end - len(text[phrase_start:phrase_end]) + len(text[phrase_start:phrase_end].rstrip())
        phrase_children = _occurrences_within(
            occurrences, occurrence_starts, rel_start, rel_end,
        )
        identity = [str(row["anchor"]) for row in phrase_children if not str(row["anchor"]).startswith("boundary:")]
        rel_key = structure_key("RELATION_PHRASE", exact_phrase, identity_anchors=identity)
        byte_start = int(byte_offsets[rel_start])
        byte_end = int(byte_offsets[rel_end])
        basis = {
            "structure_key": rel_key, "source_identity": str(source_identity),
            "block_ordinal": int(block_ordinal), "byte_start": byte_start,
            "byte_end": byte_end, "kind": "RELATION_PHRASE",
            "status": "VERIFIED_LOCAL_CONTEXT_STRUCTURE",
        }
        rel_occurrence_id = stable_hash(basis)
        relation_structures.append({
            "schema": f"{SCHEMA}:structure", **basis,
            "occurrence_id": rel_occurrence_id, "exact_text": exact_phrase,
            "exact_text_sha256": hashlib.sha256(exact_phrase.encode("utf-8")).hexdigest(),
            "char_start": rel_start, "char_end": rel_end,
            "sentence_ordinal": sentence_ordinal,
            "anchor_start": int(phrase_children[0]["position"]) if phrase_children else -1,
            "anchor_count": len(phrase_children),
            "children": [{"anchor": row["anchor"], "anchor_position": int(row["position"]), "child_ordinal": ordinal, "role": "STRUCTURE_MEMBER"} for ordinal, row in enumerate(phrase_children)],
            "punctuation_count_bearing": False, "temporary_query_overlay": bool(temporary),
            "parent_object_id": parent_object_id, "inside_native_identity_region": False,
        })
        relation = {
            "schema": f"{SCHEMA}:explicit_relation",
            "subject_structure_key": parent["structure_key"],
            "subject_occurrence_id": parent["occurrence_id"],
            "relation_structure_key": rel_key,
            "relation_occurrence_id": rel_occurrence_id,
            "object_structure_key": target["structure_key"],
            "object_occurrence_id": target["occurrence_id"],
            "source_identity": str(source_identity), "block_ordinal": int(block_ordinal),
            "sentence_ordinal": sentence_ordinal,
            "byte_start": int(parent["byte_start"]), "byte_end": int(target["byte_end"]),
            "direction": "LOCAL_CONTEXT_FORWARD", "status": "VERIFIED_LOCAL_CONTEXT_RELATION",
            "exact_relation_text": exact_phrase, "normalized_relation_class": None,
            "temporary_query_overlay": bool(temporary), "parent_object_id": parent_object_id,
            "subject_binding_kind": "SAME_PARENT_REFERENCE_SUBJECT",
            "reference_surface": str(first["surface"]),
        }
        relation["relation_id"] = stable_hash(relation)
        emitted.append(relation)
    return emitted


def _has_explicit_relation_word(words: list[str]) -> bool:
    for word in words:
        folded = word.casefold()
        if folded in RELATION_WORDS or (len(folded) > 4 and folded.endswith(("ed", "ing"))):
            return True
    return False


def _deduplicate_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for row in sorted(rows, key=lambda item: (int(item["char_start"]), -int(item["char_end"]), str(item["kind"]))):
        key = (int(row["char_start"]), int(row["char_end"]), str(row["kind"]))
        if key not in seen:
            seen.add(key)
            out.append(dict(row))
    return out


def _sentence_ordinal(text: str, char_position: int) -> int:
    return 1 + len(re.findall(r"[.!?](?:\s+|$)", text[:char_position]))


def _sentence_boundaries(text: str) -> tuple[list[int], frozenset[int]]:
    """Return the earliest prefix coordinate that completes each delimiter."""

    boundaries = []
    prefix_only = set()
    for index, character in enumerate(text):
        if character not in ".!?":
            continue
        following = index + 1
        if following == len(text):
            boundaries.append(following)
        elif text[following].isspace():
            boundaries.append(following)
        else:
            # The legacy prefix regex treats punctuation as an end-of-string
            # delimiter only at the coordinate immediately following it.
            prefix_only.add(following)
    return boundaries, frozenset(prefix_only)


def _sentence_ordinal_from_boundaries(boundaries: tuple[list[int], frozenset[int]], char_position: int) -> int:
    """Match ``_sentence_ordinal`` without repeatedly scanning source prefixes."""

    completed, prefix_only = boundaries
    position = int(char_position)
    return 1 + bisect_right(completed, position) + int(position in prefix_only)


def _utf8_prefix_offsets(text: str) -> array:
    """Map every character boundary to its exact UTF-8 byte coordinate once."""

    offsets = array("Q", [0])
    byte_position = 0
    for character in text:
        codepoint = ord(character)
        if codepoint < 0x80:
            byte_position += 1
        elif codepoint < 0x800:
            byte_position += 2
        elif codepoint < 0x10000:
            byte_position += 3
        else:
            byte_position += 4
        offsets.append(byte_position)
    return offsets


def _capitalized(value: str) -> bool:
    return bool(value) and value[0].isalpha() and value[0].isupper()
