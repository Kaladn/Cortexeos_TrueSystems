from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from truemem.engine.answer_reasoning_reverse_walk import run_answer_reasoning_reverse_walk
from truemem.engine.storage import (
    ensure_dataset,
    write_binary_counts,
    write_blocks_jsonl,
    write_citation_jsonl,
    write_coordinate_index,
    write_lexicon,
)


def _build_reverse_walk_dataset(runtime: Path, dataset_id: str) -> None:
    ensure_dataset(runtime, dataset_id)
    from truemem.engine.base import dataset_paths

    paths = dataset_paths(runtime, dataset_id)
    blocks = [
        {
            "block_ordinal": 1,
            "block_id": "b1",
            "citation_id": "c1",
            "marker": "[TMCIT-1]",
            "file_path": "corpus/jury_rule.md",
            "line_start": 1,
            "line_end": 1,
            "text_hash": "h1",
            "text": "PASSAGE_ID: jury_rule",
        },
        {
            "block_ordinal": 2,
            "block_id": "b1b",
            "citation_id": "c1b",
            "marker": "[TMCIT-1B]",
            "file_path": "corpus/jury_rule.md",
            "line_start": 2,
            "line_end": 3,
            "text_hash": "h1b",
            "text": "The court may excuse a potential juror if satisfied the person will not be able to consider the case impartially.",
        },
        {
            "block_ordinal": 3,
            "block_id": "b2",
            "citation_id": "c2",
            "marker": "[TMCIT-2]",
            "file_path": "corpus/noise.md",
            "line_start": 1,
            "line_end": 3,
            "text_hash": "h2",
            "text": "A burglary exhibit may be inspected by the jury during deliberations.",
        },
    ]
    anchors = Counter()
    relations = Counter()
    postings: list[tuple[str, int, int]] = []
    for block in blocks:
        words = [word.casefold().strip(".,") for word in str(block["text"]).split()]
        for pos, word in enumerate(words):
            if len(word) < 3:
                continue
            anchors[word] += 1
            postings.append((word, int(block["block_ordinal"]), pos))
        for left, right in zip(words, words[1:]):
            if len(left) >= 3 and len(right) >= 3:
                relations[(left, right, 1)] += 1
    write_lexicon(paths, anchors)
    write_binary_counts(paths, anchors, relations, postings)
    write_blocks_jsonl(paths, blocks)
    write_citation_jsonl(paths, blocks)
    write_coordinate_index(paths, blocks)
    paths.receipts.mkdir(parents=True, exist_ok=True)
    (paths.receipts / "intake_test.json").write_text(json.dumps({"schema": "test_intake_receipt@1"}) + "\n", encoding="utf-8")


def test_blind_reverse_walk_builds_topk_tree_without_mutation(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    dataset_id = "reverse_demo"
    _build_reverse_walk_dataset(runtime, dataset_id)
    claims = tmp_path / "claims.jsonl"
    claims.write_text(
        json.dumps(
            {
                "claim_id": "q1",
                "question": "Is the judge required to excuse a close friend from jury service?",
                "supplied_answer": "The court may excuse a potential juror if satisfied they cannot consider the case impartially.",
                "audit_reference": {"kind": "passage_id", "value": "jury_rule"},
                "metadata": {"opaque": "kept"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_answer_reasoning_reverse_walk(
        runtime_root=runtime,
        dataset_id=dataset_id,
        claims_path=claims,
        out_dir=tmp_path / "reverse",
        mode="blind_reverse_walk",
        top_k=2,
    )

    assert result["schema"] == "truemem_answer_reasoning_reverse_walk_run@0"
    assert result["mode"] == "blind_reverse_walk"
    assert result["dataset_mutation"] is False
    assert result["ranking_mutation"] is False
    assert result["speech_mutation"] is False
    assert result["model_used"] == "none"
    assert result["no_answer_generation"] is True
    assert result["records_processed"] == 1
    trace = json.loads(Path(result["trace_jsonl_path"]).read_text(encoding="utf-8").splitlines()[0])
    assert trace["claim_id"] == "q1"
    assert trace["support_decision"] == "supported"
    assert trace["expected_passage_seen"] is True
    assert trace["expected_passage_rank_if_seen"] == 1
    assert trace["reverse_topK_candidates"][0]["file_path"] == "corpus/jury_rule.md"
    assert trace["reverse_topK_tree"][0]["candidate"]["citation"] == "[TMCIT-1B]"
    assert trace["reverse_topK_tree"][0]["question_anchor_pressure"]["candidate_to_question_coverage"] > 0
    assert trace["no_mutation_receipt"]["no_answer_generation"] is True


def test_paired_set_verify_checks_named_reference_without_retrieval_seeding(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    dataset_id = "reverse_demo"
    _build_reverse_walk_dataset(runtime, dataset_id)
    claims = tmp_path / "claims.jsonl"
    claims.write_text(
        json.dumps(
            {
                "claim_id": "q1",
                "question": "Is the judge required to excuse a close friend from jury service?",
                "supplied_answer": "The court may excuse a potential juror if satisfied they cannot consider the case impartially.",
                "audit_reference": {"kind": "passage_id", "value": "jury_rule"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_answer_reasoning_reverse_walk(
        runtime_root=runtime,
        dataset_id=dataset_id,
        claims_path=claims,
        out_dir=tmp_path / "reverse",
        mode="paired_set_verify",
        top_k=2,
    )

    trace = json.loads(Path(result["trace_jsonl_path"]).read_text(encoding="utf-8").splitlines()[0])
    assert trace["mode"] == "paired_set_verify"
    assert trace["paired_set_verification"]["reference_found"] is True
    assert trace["paired_set_verification"]["support_decision"] == "supported"
    assert trace["paired_set_verification"]["reference_candidate"]["direct_reference_verification"] is True
    assert trace["support_decision"] == "supported"


def test_answer_reasoning_reverse_walk_cli(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    dataset_id = "reverse_demo"
    _build_reverse_walk_dataset(runtime, dataset_id)
    claims = tmp_path / "claims.jsonl"
    claims.write_text(
        json.dumps(
            {
                "claim_id": "q1",
                "question": "Is the judge required to excuse a close friend from jury service?",
                "supplied_answer": "The court may excuse a potential juror if satisfied they cannot consider the case impartially.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "truemem.cli",
            "answer-reasoning-reverse-walk",
            "--runtime-root",
            str(runtime),
            "--dataset-id",
            dataset_id,
            "--claims",
            str(claims),
            "--out",
            str(tmp_path / "out"),
            "--mode",
            "blind_reverse_walk",
            "--top-k",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["records_processed"] == 1
    assert Path(payload["trace_jsonl_path"]).is_file()
