"""Deterministic exact-span structural compilation for DocuFilm intake.

This module does not interpret source with a model.  It records only structures
that can be reconstructed from exact bytes and bounded source-form rules.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


SCHEMA = "truevision_structural_binding@1"
COMPILER = "truevision_deterministic_text_structure_compiler@1"

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
    candidates = _deduplicate_candidates(candidates)
    candidates = _apply_explicit_type_cues(source, candidates)

    structures: list[dict[str, Any]] = []
    for candidate in candidates:
        start = int(candidate["char_start"])
        end = int(candidate["char_end"])
        exact = source[start:end]
        anchor_children = [
            row for row in occurrences
            if int(row["char_start"]) >= start and int(row["char_end"]) <= end
        ]
        if not anchor_children:
            continue
        kind = str(candidate["kind"])
        identity_anchors = [str(row["anchor"]) for row in anchor_children if not str(row["anchor"]).startswith("boundary:")]
        key = structure_key(kind, exact, identity_anchors=identity_anchors)
        byte_start = len(source[:start].encode("utf-8"))
        byte_end = len(source[:end].encode("utf-8"))
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
            "sentence_ordinal": _sentence_ordinal(source, start),
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
        })

    relations, relation_structures = _explicit_relations(source, structures, occurrences, source_identity, block_ordinal, temporary_query_overlay)
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


def _explicit_relations(text: str, structures: list[dict[str, Any]], occurrences: list[dict[str, Any]], source_identity: str, block_ordinal: int, temporary: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subject_objects = [row for row in structures if row["kind"] not in {"DATE", "QUANTITY", "PARENTHETICAL", "RELATION_PHRASE"}]
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
        phrase_children = [row for row in occurrences if int(row["char_start"]) >= rel_start and int(row["char_end"]) <= rel_end]
        relation_identity = [str(row["anchor"]) for row in phrase_children if not str(row["anchor"]).startswith("boundary:")]
        rel_key = structure_key("RELATION_PHRASE", exact_phrase, identity_anchors=relation_identity)
        pair = (str(left["occurrence_id"]), str(right["occurrence_id"]))
        if pair in seen:
            continue
        seen.add(pair)
        byte_start = len(text[:rel_start].encode("utf-8"))
        byte_end = len(text[:rel_end].encode("utf-8"))
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
    return relations, relation_structures


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


def _capitalized(value: str) -> bool:
    return bool(value) and value[0].isalpha() and value[0].isupper()
