"""Evidence-conditioned HotpotQA speech preparation and relationship gating.

Reference answers in this module are supervision authority only.  They are
never returned as model speech.  Model speech must be produced by a later
walk from a question plus a qualified, coordinate-backed evidence workspace.
"""
from __future__ import annotations

import hashlib
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .hotpotqa_retrieval_evaluation import canonical, file_sha256

SCHEMA = "truesystems_hotpotqa_evidence_speech@1"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parquet_rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required; run with `uv run --with pyarrow`") from error
    return parquet.read_table(path).to_pylist()


def _supporting_sentences(row: dict[str, Any]) -> list[dict[str, Any]] | None:
    context = row["context"]
    by_title = {str(title): sentences for title, sentences in zip(context["title"], context["sentences"])}
    result = []
    for title, sentence_ordinal in zip(row["supporting_facts"]["title"], row["supporting_facts"]["sent_id"]):
        sentences = by_title.get(str(title))
        ordinal = int(sentence_ordinal)
        if sentences is None or not 0 <= ordinal < len(sentences):
            return None
        text = str(sentences[ordinal])
        result.append({
            "title": str(title),
            "sentence_ordinal": ordinal,
            "text": text,
            "text_sha256": _sha(text.encode("utf-8")),
        })
    return result


def build_evidence_speech_sessions(
    authority_parquet: Path,
    consumed_query_results: Path,
    output: Path,
    *,
    validation_modulus: int = 10,
) -> dict[str, Any]:
    """Build exact evidence-conditioned chat sessions without running training."""
    if output.exists():
        raise FileExistsError(output)
    consumed = {
        json.loads(line)["query_id"]
        for line in consumed_query_results.read_text().splitlines()
        if line.strip()
    }
    accepted = []
    quarantined = []
    for row in sorted(_parquet_rows(authority_parquet), key=lambda value: str(value["id"])):
        query_id = str(row["id"])
        if query_id in consumed:
            quarantined.append({"query_id": query_id, "reason": "CONSUMED_EVALUATION_GROUP_NEVER_TRAIN"})
            continue
        evidence = _supporting_sentences(row)
        if evidence is None:
            quarantined.append({"query_id": query_id, "reason": "INCOMPLETE_SUPPORTING_SENTENCE_AUTHORITY"})
            continue
        question = str(row["question"])
        answer = str(row["answer"])
        workspace = "\n".join(
            f"[{item['title']}#sentence-{item['sentence_ordinal']}] {item['text']}"
            for item in evidence
        )
        user_content = f"Question\n{question}\nEvidence workspace\n{workspace}"
        split = "validation" if int(_sha(query_id.encode())[:8], 16) % validation_modulus == 0 else "train"
        session_id = _sha(canonical({"query_id": query_id, "question": question, "evidence": evidence, "answer": answer}))
        accepted.append({
            "query_id": query_id,
            "session_id": session_id,
            "split": split,
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": answer},
            ],
            "reference_supervision": {
                "classification": "REFERENCE_ANSWER_SUPERVISION_NOT_MODEL_SPEECH",
                "answer": answer,
                "answer_sha256": _sha(answer.encode("utf-8")),
                "supporting_sentences": evidence,
            },
        })
    output.mkdir(parents=True)
    package = output / "source-package"
    package.mkdir()
    hashes = {}
    for split in ("train", "validation"):
        payload = b"".join(canonical({"session_id": row["session_id"], "messages": row["messages"]}) for row in accepted if row["split"] == split)
        path = package / f"{split}.jsonl"
        path.write_bytes(payload)
        hashes[path.name] = _sha(payload)
    # The historical preparer expects a test artifact.  It is intentionally
    # empty here: this stage prepares training, not another evaluation opening.
    (package / "test.jsonl").write_bytes(b"")
    hashes["test.jsonl"] = _sha(b"")
    (package / "sha256_manifest.json").write_bytes(canonical(hashes))
    (output / "assignments.jsonl").write_bytes(b"".join(canonical({key: value for key, value in row.items() if key != "messages"}) for row in accepted))
    (output / "quarantine.jsonl").write_bytes(b"".join(canonical(row) for row in quarantined))
    manifest = {
        "schema": SCHEMA,
        "classification": "EVIDENCE_CONDITIONED_SPEECH_PREPARED_NOT_TRAINED",
        "authority_parquet": {"path": str(authority_parquet.resolve()), "sha256": file_sha256(authority_parquet)},
        "consumed_evaluation": {"path": str(consumed_query_results.resolve()), "sha256": file_sha256(consumed_query_results), "query_count": len(consumed)},
        "accepted": len(accepted),
        "train_sessions": sum(row["split"] == "train" for row in accepted),
        "validation_sessions": sum(row["split"] == "validation" for row in accepted),
        "quarantined": len(quarantined),
        "reference_answers_are_supervision_not_model_speech": True,
        "source_text_normalization": "none",
        "optimizer_updates": 0,
        "model_training_performed": False,
        "evaluation_opened": False,
        "authority_created": False,
    }
    manifest["release_id"] = _sha(canonical(manifest))
    (output / "manifest.json").write_bytes(canonical(manifest))
    return manifest


def relationship_demands(question: str) -> list[dict[str, Any]]:
    """Return exact signed query relationships without deleting glue positions."""
    from truemem.engine.anchors import anchor_kind, anchorize
    anchors = anchorize(question)
    endpoints = {index for index, anchor in enumerate(anchors) if anchor_kind(anchor) in {"content", "relation"}}
    result = []
    for left in sorted(endpoints):
        for right in sorted(endpoints):
            distance = right - left
            if left != right and -6 <= distance <= 6:
                result.append({"center": anchors[left], "neighbor": anchors[right], "signed_distance": distance, "query_positions": [left, right]})
    return result


def qualify_block_relationships(question: str, block: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    """Require exact positional query paths or exact parent/title anchors."""
    from truemem.engine.anchors import anchor_kind, anchorize
    demands = relationship_demands(question)
    matches = []
    block_id = int(block["block_ordinal"])
    for demand in demands:
        center = index["anchor_to_symbol"].get(demand["center"])
        neighbor = index["anchor_to_symbol"].get(demand["neighbor"])
        if center is None or neighbor is None:
            continue
        left_positions = index["posting_positions"].get(center, {}).get(block_id, [])
        right_positions = set(index["posting_positions"].get(neighbor, {}).get(block_id, []))
        witnesses = [position for position in left_positions if position + demand["signed_distance"] in right_positions]
        if witnesses:
            matches.append({**demand, "block_center_positions": witnesses, "native_lane_count": int(index["signed_relations"].get(center, {}).get(demand["signed_distance"], {}).get(neighbor, 0))})
    title = str(block["text"]).splitlines()[0] if str(block["text"]) else ""
    title_anchors = set(anchorize(title))
    query_content = [anchor for anchor in anchorize(question) if anchor_kind(anchor) == "content"]
    parent_hits = list(dict.fromkeys(anchor for anchor in query_content if anchor in title_anchors))
    return {
        "qualified": bool(matches or parent_hits),
        "relationship_matches": matches,
        "relationship_match_count": len(matches),
        "parent_anchor_hits": parent_hits,
        "parent_anchor_hit_count": len(parent_hits),
        "qualification_law": "exact signed query relationship in one block OR exact content anchor in parent/title region",
    }


def select_relationship_workspace(
    question: str,
    blocks: dict[int, dict[str, Any]],
    index: dict[str, Any],
    *,
    maximum_blocks: int = 2,
) -> dict[str, Any]:
    """Select a coordinate-backed block chain using positions and shared anchors."""
    from truemem.engine.anchors import anchor_kind, anchorize
    query_anchors = anchorize(question)
    query_set = set(query_anchors)
    candidate_ids: set[int] = set()
    for anchor in query_anchors:
        symbol = index["anchor_to_symbol"].get(anchor)
        if symbol is not None:
            candidate_ids.update(index["posting_positions"].get(symbol, {}))
    qualified = []
    for block_id in sorted(candidate_ids):
        qualification = qualify_block_relationships(question, blocks[block_id], index)
        if not qualification["qualified"]:
            continue
        content = {
            anchor for anchor in anchorize(str(blocks[block_id]["text"]))
            if anchor_kind(anchor) == "content" and anchor not in query_set
        }
        covered = set(qualification["parent_anchor_hits"])
        for match in qualification["relationship_matches"]:
            covered.update((match["center"], match["neighbor"]))
        qualified.append({"block_id": block_id, "qualification": qualification, "content": content, "covered": covered})
    # Retain the strongest exact-path candidates and every parent/title
    # candidate.  This prevents generic direct-hit volume from controlling the
    # chain pool while keeping named parent regions available.
    relationship_rows = sorted(
        qualified,
        key=lambda row: (-row["qualification"]["relationship_match_count"], -len(row["covered"]), row["block_id"]),
    )[:100]
    parent_rows = [row for row in qualified if row["qualification"]["parent_anchor_hit_count"]]
    pool = {row["block_id"]: row for row in [*relationship_rows, *parent_rows]}
    rows = [pool[key] for key in sorted(pool)]
    chains = []
    if maximum_blocks >= 2:
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1:]:
                bridges = sorted(left["content"] & right["content"])
                coverage = left["covered"] | right["covered"]
                vector = {
                    "query_anchor_coverage": len(coverage),
                    "shared_bridge_anchor_count": len(bridges),
                    "relationship_match_count": left["qualification"]["relationship_match_count"] + right["qualification"]["relationship_match_count"],
                    "parent_anchor_hit_count": left["qualification"]["parent_anchor_hit_count"] + right["qualification"]["parent_anchor_hit_count"],
                }
                chains.append({"block_ids": [left["block_id"], right["block_id"]], "bridge_anchors": bridges, "covered_query_anchors": sorted(coverage), "vector": vector})
    chains.sort(key=lambda row: (-row["vector"]["query_anchor_coverage"], -int(row["vector"]["shared_bridge_anchor_count"] > 0), -row["vector"]["shared_bridge_anchor_count"], -row["vector"]["relationship_match_count"], -row["vector"]["parent_anchor_hit_count"], tuple(row["block_ids"])))
    if chains:
        chosen_ids = chains[0]["block_ids"]
        chosen_chain = chains[0]
    elif rows:
        chosen_ids = [max(rows, key=lambda row: (len(row["covered"]), row["qualification"]["relationship_match_count"], row["qualification"]["parent_anchor_hit_count"], -row["block_id"]))["block_id"]]
        chosen_chain = {"block_ids": chosen_ids, "bridge_anchors": [], "covered_query_anchors": sorted(pool[chosen_ids[0]]["covered"]), "vector": {"query_anchor_coverage": len(pool[chosen_ids[0]]["covered"]), "shared_bridge_anchor_count": 0, "relationship_match_count": pool[chosen_ids[0]]["qualification"]["relationship_match_count"], "parent_anchor_hit_count": pool[chosen_ids[0]]["qualification"]["parent_anchor_hit_count"]}}
    else:
        chosen_ids = []
        chosen_chain = None
    selected = []
    for block_id in chosen_ids:
        block = blocks[block_id]
        selected.append({
            "block_ordinal": block_id,
            "corpus_id": block["corpus_id"],
            "citation_id": block["citation_id"],
            "citation_marker": block["marker"],
            "file_path": block["file_path"],
            "line_start": block["line_start"],
            "line_end": block["line_end"],
            "source_row_sha256": block["source_row_sha256"],
            "source_text_sha256": block["source_text_sha256"],
            "text": block["text"],
            "sentences": block.get("sentences", []),
            "qualification": pool[block_id]["qualification"],
        })
    return {
        "schema": f"{SCHEMA}:relationship_workspace",
        "question": question,
        "candidate_block_count": len(candidate_ids),
        "qualified_block_count": len(qualified),
        "selected_chain": chosen_chain,
        "blocks": selected,
        "kaley_style_disconnected_hits_rejected": True,
        "model_used": False,
    }


def _answer_map(prepared: Path) -> tuple[list[tuple[str, str, int, int]], Counter[str], set[str]]:
    mapping = json.loads((prepared / "symbol-index-mapping.json").read_text())
    symbol_to_anchor = {str(row["permanent_symbol"]): str(row["surface"]) for row in mapping["entries"]}
    relations = []
    with gzip.open(prepared / "M002.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            center = symbol_to_anchor.get(str(row["center"]))
            neighbor = symbol_to_anchor.get(str(row["neighbor"]))
            if center is not None and neighbor is not None:
                relations.append((center, neighbor, int(row["offset"]), int(row["count"])))
    frequencies: Counter[str] = Counter()
    with gzip.open(prepared / "M001.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            anchor = symbol_to_anchor.get(str(row["symbol"]))
            if anchor is not None:
                frequencies[anchor] = int(row["count"])
    return relations, frequencies, set(symbol_to_anchor.values())


def walk_evidence_answer(
    question: str,
    workspace: dict[str, Any],
    prepared_answer_map: Path,
    *,
    top_k: int,
    max_new_anchors: int = 24,
) -> dict[str, Any]:
    """Walk an answer from the deterministic map, constrained to evidence."""
    from truemem.engine.anchors import anchor_kind, anchorize, anchors_to_text, answer_direction_anchors
    from truemem.engine.prediction_walk import citation_coordinates_for_path, predict_anchor_path
    relations, frequencies, vocabulary = _answer_map(prepared_answer_map)
    evidence_anchors = []
    for block in workspace.get("blocks", []):
        evidence_anchors.extend(anchorize(str(block["text"])))
    question_anchors = anchorize(question)
    factual = set(question_anchors) | set(evidence_anchors)
    allowed = {
        anchor for anchor in vocabulary
        if anchor in factual or anchor.startswith("<") or anchor_kind(anchor) in {"glue", "relation", "boundary"}
    }
    resolved_history = ["<END_MESSAGE>", "<ASSISTANT>", "<BEGIN_MESSAGE>"]
    walk = predict_anchor_path(
        relations,
        resolved_history=resolved_history,
        query_anchors=answer_direction_anchors([*question_anchors, *evidence_anchors]),
        anchor_frequencies=frequencies,
        max_new_anchors=max_new_anchors,
        top_k=top_k,
        beam_width=top_k,
        allowed_anchors=allowed,
    )
    spoken = [anchor for anchor in walk["generated_anchors"] if not anchor.startswith("<")]
    citation_blocks = [{**block, "marker": block["citation_marker"]} for block in workspace.get("blocks", [])]
    citations = citation_coordinates_for_path(spoken, blocks=citation_blocks)
    return {
        "schema": f"{SCHEMA}:model_walk_output",
        "classification": "MODEL_WALK_OUTPUT_NOT_REFERENCE_ANSWER",
        "top_k": top_k,
        "speech_anchors": spoken,
        "speech_text": anchors_to_text(spoken),
        "walk": walk,
        "workspace_block_ids": [block["block_ordinal"] for block in workspace.get("blocks", [])],
        "citations": citations,
        "content_anchor_workspace_enforced": True,
        "reference_answer_copied": False,
    }
