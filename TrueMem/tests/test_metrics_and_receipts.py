from __future__ import annotations

import json
from pathlib import Path

from truemem.engine.base import dataset_paths
from truemem.engine.querying import _cloud_mismatch_result
from truemem.engine.storage import ensure_dataset, index_readiness
from truemem.engine.system_metrics import system_metrics


def test_system_metrics_reports_manifest_symbol_count(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    dataset_root = runtime / "datasets" / "demo"
    dataset_root.mkdir(parents=True)
    (dataset_root / "dataset_manifest.json").write_text(
        json.dumps({"symbol_start": 10, "symbol_end": 14}),
        encoding="utf-8",
    )

    metrics = system_metrics(runtime)

    assert metrics["datasets"][0]["symbol_count"] == 5
    assert metrics["totals"]["total_symbols_allocated"] == 5
    assert metrics["totals"]["last_global_symbol_id"] == 14


def test_cloud_mismatch_receipt_contains_output_path_on_first_write(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    dataset_id = "demo"
    ensure_dataset(runtime, dataset_id)
    paths = dataset_paths(runtime, dataset_id)

    output = _cloud_mismatch_result(
        paths=paths,
        dataset_id=dataset_id,
        question="outside cloud question",
        q_counter={},
        readiness=index_readiness(runtime, dataset_id),
        cloud_gate={
            "significant_question_anchors": [],
            "approved": False,
            "retrieval_ran": False,
            "topk_ran": False,
        },
        anchor_focus={},
    )

    written = json.loads(Path(output["output_path"]).read_text(encoding="utf-8"))
    assert written["output_path"] == output["output_path"]
