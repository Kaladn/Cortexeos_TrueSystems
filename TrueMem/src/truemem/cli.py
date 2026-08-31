from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import (
    batch_questions,
    build_citation_crosslinks,
    count_walk_speech,
    dataset_overview,
    determinism_receipt,
    deeper_wider_after_answer,
    ensure_dataset,
    export_ledger,
    adapt_resonance_sample,
    docufilm_intake,
    query,
    recent_questions,
    run_answer_reasoning_reverse_walk,
    run_evidence_cloud_speech,
    run_packet_speech,
    run_pressure_probe,
    run_topk_diagnostic,
    run_wide_deep_verification,
    show_record,
    stage_codex_sessions,
    stage_chatgpt_export,
    stage_codex_markdown_export,
    status,
    special_search,
    system_metrics,
    with_protected_notice,
)
from .agents import run_pressure_coordination_audit
from .adapters import prepare_source_with_adapter_if_present
from .operator_state import audit_operator_state


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="truemem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="TrueMem dataset-local evidence engine CLI.",
        epilog="""
Batch walkthrough:
  1. Create a plain text file with one question per line.
  2. Make sure the dataset has already been built with truemem docufilm-intake.
  3. Run: truemem batch --runtime-root <runtime> --dataset <name> --questions questions.txt
  4. Watch the tqdm progress bar in the terminal.
  5. Open the reported batch_run_summary.json when complete.
""",
    )
    parser.add_argument("--version", action="version", version="truemem 0.05")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a dataset-local TrueMem scope")
    init_cmd.add_argument("--runtime-root", type=Path, required=True)
    init_cmd.add_argument("--dataset-id", required=True)
    init_cmd.add_argument("--owner", default="operator_defined")

    intake_cmd = sub.add_parser("docufilm-intake", help="Build dataset-local lexicon, counts, coordinates, and citations")
    intake_cmd.add_argument("--runtime-root", type=Path, required=True)
    intake_cmd.add_argument("--dataset-id", required=True)
    intake_cmd.add_argument("--source", type=Path, required=True)
    intake_cmd.add_argument("--owner", default="operator_defined")
    intake_cmd.add_argument("--window", type=int, default=6)
    intake_cmd.add_argument("--workers", default="auto", help="Worker count or auto. Minimum 4 workers; single-core/low-core execution is refused.")
    intake_cmd.add_argument("--reserve-ram-fraction", type=float, default=0.15, help="Fraction of total RAM to reserve for system/operator.")
    intake_cmd.add_argument("--ram-budget-gb", type=float, default=8.0, help="Maximum RAM budget for intake workers. Defaults to 8 GiB.")
    intake_cmd.add_argument("--no-progress", action="store_true", help="Disable tqdm file progress meter.")
    intake_cmd.add_argument(
        "--debug-tiny-single-core",
        action="store_true",
        help="Explicit non-production debug/tiny mode. Allows low-worker intake and marks receipts as debug only.",
    )
    status_cmd = sub.add_parser("status", help="Show dataset-local status")
    status_cmd.add_argument("--runtime-root", type=Path, required=True)
    status_cmd.add_argument("--dataset-id", required=True)

    metrics_cmd = sub.add_parser("system-metrics", help="Show read-only runtime, dataset, resource, and symbol-allocation metrics")
    metrics_cmd.add_argument("--runtime-root", type=Path)
    metrics_cmd.add_argument("--dataset-id")
    metrics_cmd.add_argument("--workspace", type=Path)
    metrics_cmd.add_argument("--repo", type=Path)

    overview_cmd = sub.add_parser(
        "dataset-overview",
        help="Write count-derived dataset overview reports with source trails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Read-only overview from native count artifacts, canonical blocks, citations, and coordinates.",
        epilog="""
Step-by-step:
  1. Build a dataset with truemem docufilm-intake.
  2. Run:
       truemem dataset-overview --runtime-root <runtime> --dataset <name> --out <overview-folder>
  3. Open overview_summary.md for the operator view.
  4. Open anchor_overviews.jsonl and relationship_trails.jsonl for machine-readable trails.
  5. Receipts prove no intake, query, model, or count mutation occurred.
""",
    )
    overview_cmd.add_argument("--runtime-root", type=Path, required=True)
    overview_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    overview_cmd.add_argument("--out", type=Path, required=True)
    overview_cmd.add_argument("--top-anchors", type=int, default=25)
    overview_cmd.add_argument("--top-relations", type=int, default=50)
    overview_cmd.add_argument("--trail-limit", type=int, default=5)

    query_cmd = sub.add_parser("query", help="Return a cited local answer packet from dataset coordinates")
    query_cmd.add_argument("--runtime-root", type=Path, required=True)
    query_cmd.add_argument("--dataset-id", required=True)
    query_cmd.add_argument("--question", required=True)
    query_cmd.add_argument("--top-k", type=int, default=5)
    query_cmd.add_argument("--created-after", help="Optional chat metadata lower bound, e.g. 2024-12-14")
    query_cmd.add_argument("--created-before", help="Optional chat metadata upper bound, e.g. 2024-12-15")
    query_cmd.add_argument("--speaker", choices=["user", "assistant"], help="Optional chat metadata speaker filter")

    deeper_wider_cmd = sub.add_parser(
        "deeper-wider",
        help="Optionally widen native relationships after a first anchor-prediction answer",
    )
    deeper_wider_cmd.add_argument("--runtime-root", type=Path, required=True)
    deeper_wider_cmd.add_argument("--dataset-id", required=True)
    deeper_wider_cmd.add_argument(
        "--first-answer",
        type=Path,
        required=True,
        help="Query-result JSON or truemem_anchor_prediction_walk@2 JSON already returned by the first pass.",
    )
    deeper_wider_cmd.add_argument("--depth", type=int, default=3)
    deeper_wider_cmd.add_argument("--width", type=int, default=12)

    qa_recent_cmd = sub.add_parser("qa-recent", help="Show recent dataset-local Q/A ledger records")
    qa_recent_cmd.add_argument("--runtime-root", type=Path, required=True)
    qa_recent_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    qa_recent_cmd.add_argument("--limit", type=int, default=10)

    qa_export_cmd = sub.add_parser("qa-export", help="Export a dataset-local Q/A ledger JSONL file")
    qa_export_cmd.add_argument("--runtime-root", type=Path, required=True)
    qa_export_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    qa_export_cmd.add_argument("--output", type=Path, required=True)

    qa_show_cmd = sub.add_parser("qa-show", help="Show one dataset-local Q/A record by id")
    qa_show_cmd.add_argument("--runtime-root", type=Path, required=True)
    qa_show_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    qa_show_cmd.add_argument("--record-id", required=True)

    packet_speech_cmd = sub.add_parser(
        "packet-speech",
        help="Form evidence_trace and pretty_answer from existing TrueMem query packet JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Report-only speech from existing TrueMem query packet JSON. Does not run retrieval, topK, intake, or model reasoning.",
        epilog="""
Step-by-step:
  1. Run truemem query and keep the reported output_path.
  2. Run:
       truemem packet-speech --packet <query-output.json> --out <speech-output-folder>
  3. Open evidence_trace/*.json for authority.
  4. Open pretty_answer/*.md or *.json for readable speech.
  5. Receipts prove retrieval/topK/intake/model work did not run.
""",
    )
    packet_speech_cmd.add_argument("--packet", action="append", type=Path, required=True, help="Existing TrueMem query JSON. Repeat for multiple packets.")
    packet_speech_cmd.add_argument("--out", type=Path, required=True)

    evidence_speech_cmd = sub.add_parser(
        "evidence-speech",
        help="Build temporary evidence-cloud speech from one existing query packet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Operator-stepped evidence boil-down from an existing top-K evidence packet. Builds a tiny in-memory micro-map and does not run retrieval.",
        epilog="""
Step-by-step:
  1. Run truemem query and keep the reported output_path.
  2. Run:
       truemem evidence-speech --packet <query-output.json> --out <speech-output-folder>
  3. Optional: add --question "..." to override the packet question for the micro-search.
  4. Open evidence_trace/*_evidence_cloud_trace.json for the proved boil-down step.
  5. Open pretty_answer/*_pretty_answer.md for the short grounded answer.
  6. Decide the next action: stop, continue, widen, or reject.
  7. This command does not run retrieval, topK, intake, model reasoning, or dataset mutation.
""",
    )
    evidence_speech_cmd.add_argument("--packet", type=Path, required=True, help="Existing TrueMem query result JSON.")
    evidence_speech_cmd.add_argument("--question", help="Optional question override for the evidence-cloud micro-search.")
    evidence_speech_cmd.add_argument("--out", type=Path, required=True)
    evidence_speech_cmd.add_argument("--max-passes", type=int, default=1, help="Maximum passes. Defaults to one operator-approved step.")
    evidence_speech_cmd.add_argument(
        "--auto-passes",
        action="store_true",
        help="Run up to --max-passes without stopping for operator review. Off by default.",
    )

    pressure_probe_cmd = sub.add_parser(
        "pressure-probe",
        help="Off-path diagnostic: build bounded follow-up pressure questions from existing query packets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Off-path thinking diagnostic. Reads existing TrueMem query packets and writes second-layer evidence questions. Does not run retrieval, topK, intake, speech, models, or dataset mutation.",
        epilog="""
Step-by-step:
  1. Run truemem query or truemem batch and keep the query JSON or batch_run_summary.json.
  2. Run:
       truemem pressure-probe --packet <query-output.json> --out <probe-folder>
     or:
       truemem pressure-probe --batch-summary <batch_run_summary.json> --out <probe-folder>
  3. Open questions/PRESSURE_PROBE_QUESTIONS.jsonl.
  4. If the probes earn it, feed that JSONL back through normal truemem batch.
  5. Receipts prove no retrieval, ranking, intake, speech, answer generation, or dataset mutation ran in this sidecar.
""",
    )
    pressure_probe_cmd.add_argument("--packet", action="append", type=Path, help="Existing TrueMem query result JSON. Repeat for multiple packets.")
    pressure_probe_cmd.add_argument("--batch-summary", type=Path, help="Existing truemem batch_run_summary.json to probe all completed packets.")
    pressure_probe_cmd.add_argument("--out", type=Path, required=True)
    pressure_probe_cmd.add_argument("--max-questions-per-packet", type=int, default=5)

    topk_diag_cmd = sub.add_parser(
        "topk-diagnostic",
        help="Off-path diagnostic: build no-refusal TopK ladder diagnostics from existing query packets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Off-path retrieval diagnostic. Reads existing TrueMem query packets or batch summaries and walks TopK by rank layer. Does not run retrieval, intake, ranking mutation, or dataset mutation.",
        epilog="""
Step-by-step:
  1. Run truemem query or truemem batch and keep the query JSON or batch_run_summary.json.
  2. Run:
       truemem topk-diagnostic --batch-summary <batch_run_summary.json> --out <folder> --max-rank 5
     or:
       truemem topk-diagnostic --packet <query-output.json> --out <folder> --max-rank 5
  3. Open TOPK_DIAGNOSTIC_PACKETS.jsonl for per-question diagnostic packets.
  4. Open rank_layers/TOPK_LAYER_1.jsonl through TOPK_LAYER_5.jsonl to inspect evidence by rank across questions.
  5. Receipts prove no refusal, no retrieval, no ranking mutation, and no dataset mutation occurred in this sidecar.
""",
    )
    topk_diag_cmd.add_argument("--packet", action="append", type=Path, help="Existing TrueMem query result JSON. Repeat for multiple packets.")
    topk_diag_cmd.add_argument("--batch-summary", type=Path, help="Existing truemem batch_run_summary.json.")
    topk_diag_cmd.add_argument("--out", type=Path, required=True)
    topk_diag_cmd.add_argument("--max-rank", type=int, default=5)

    wide_deep_cmd = sub.add_parser("wide-deep-verify", help="Verify proof support from an existing query packet without changing native rank")
    wide_deep_cmd.add_argument("--packet", type=Path, required=True)
    wide_deep_cmd.add_argument("--expected", type=Path, help="Optional JSON expected/gold candidate for benchmark audit")
    wide_deep_cmd.add_argument("--out", type=Path, required=True)

    reverse_walk_cmd = sub.add_parser(
        "answer-reasoning-reverse-walk",
        help="Off-path thinking: reverse-walk supplied answer claims back into corpus evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Off-path thinking lane. Reads generic question/answer claim packets and writes reverse evidence traces. Does not run intake, query, speech, models, ranking mutation, or dataset mutation.",
        epilog="""
Step-by-step:
  1. Prepare a JSONL claim packet with question and supplied_answer.
  2. Run:
       truemem answer-reasoning-reverse-walk --runtime-root <runtime> --dataset <name> --claims claims.jsonl --out <folder>
  3. Use --mode blind_reverse_walk for answer-rooted corpus search.
  4. Use --mode paired_set_verify only when a claim includes an audit_reference to verify a named evidence item.
  5. Open traces/ANSWER_REASONING_REVERSE_WALK_TRACE.jsonl for the reverse topK tree.
  6. Receipts prove no LLM, no answer generation, no intake, no ranking mutation, no speech mutation, and no dataset mutation.
""",
    )
    reverse_walk_cmd.add_argument("--runtime-root", type=Path, required=True)
    reverse_walk_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    reverse_walk_cmd.add_argument("--claims", type=Path, required=True)
    reverse_walk_cmd.add_argument("--out", type=Path, required=True)
    reverse_walk_cmd.add_argument("--mode", choices=["blind_reverse_walk", "paired_set_verify"], default="blind_reverse_walk")
    reverse_walk_cmd.add_argument("--top-k", type=int, default=8)

    pressure_coordination_cmd = sub.add_parser(
        "pressure-coordination-audit",
        help="Off-path thinking: coordinate real, REAPER-only, and combined support strengths from reverse-walk traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Off-path thinking side module. Reads answer-reasoning reverse-walk traces and writes three output lanes: real system as-is, REAPER-only pressure mutation, and combined strengths. Does not run retrieval, intake, speech, models, ranking mutation, or dataset mutation.",
        epilog="""
Step-by-step:
  1. Run truemem answer-reasoning-reverse-walk and keep ANSWER_REASONING_REVERSE_WALK_TRACE.jsonl.
  2. Run:
       truemem pressure-coordination-audit --trace <trace.jsonl> --out <folder>
  3. Open real_system_as_is/REAL_SYSTEM_TRACE.jsonl for the unchanged system decision.
  4. Open reaper_only/REAPER_PRESSURE_MUTATION_TRACE.jsonl for the pressure-only mutated judgment.
  5. Open combined_strengths/COMBINED_STRENGTH_TRACE.jsonl for the comparison lane.
  6. Receipts prove no source trace mutation or dataset mutation occurred.
""",
    )
    pressure_coordination_cmd.add_argument("--trace", type=Path, required=True)
    pressure_coordination_cmd.add_argument("--out", type=Path, required=True)

    count_walk_cmd = sub.add_parser(
        "count-walk-speech",
        help="Run rough count-guided speech walk from a count-selected local spine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Query selects evidence, block postings provide local spine, relation counts choose continuation branches.",
        epilog="""
Step-by-step:
  1. Build a dataset with truemem docufilm-intake.
  2. Run:
       truemem count-walk-speech --runtime-root <runtime> --dataset <name> --question "..." --out <folder>
  3. Optional: add --starter "known phrase" to require an exact starter inside the selected local spine.
  4. Open evidence_trace/count_walk_trace_*.json to inspect every branch choice.
  5. Open pretty_answer/count_walk_speech_*.md for the rough readable view.
  6. This is not final ClearSpeak and does not change retrieval, ranking, intake, or counts.
""",
    )
    count_walk_cmd.add_argument("--runtime-root", type=Path, required=True)
    count_walk_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    count_walk_cmd.add_argument("--question", required=True)
    count_walk_cmd.add_argument("--out", type=Path, required=True)
    count_walk_cmd.add_argument("--starter")
    count_walk_cmd.add_argument("--top-k", type=int, default=5)
    count_walk_cmd.add_argument("--max-steps", type=int, default=50)
    count_walk_cmd.add_argument("--branch-k", type=int, default=5)

    batch_cmd = sub.add_parser(
        "batch",
        help="Run a plain question list through dataset-local query",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Run many dataset questions through the existing TrueMem query path.",
        epilog="""
Step-by-step:
  1. Put one question per line in questions.txt.
  2. Blank lines are ignored.
  3. Run:
       truemem batch --runtime-root <runtime> --dataset <name> --questions questions.txt --workers 4
  4. tqdm shows question completion progress.
  5. Each question writes its own query JSON output.
  6. The batch writes outputs/batch_<run_id>/batch_run_summary.json.
  7. model_used remains none.
  8. Single-core/low-core execution is refused.
""",
    )
    batch_cmd.add_argument("--runtime-root", type=Path, required=True)
    batch_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    batch_cmd.add_argument("--questions", type=Path, required=True)
    batch_cmd.add_argument("--top-k", type=int, default=5)
    batch_cmd.add_argument("--workers", default="auto", help="Worker count or auto. Single-core is refused.")
    batch_cmd.add_argument("--no-progress", action="store_true", help="Disable tqdm progress display for scripted runs")

    adapters_cmd = sub.add_parser(
        "adapters",
        help="Build source-specific adapter preparation artifacts when a supported adapter exists",
    )
    adapters_sub = adapters_cmd.add_subparsers(dest="adapter_command", required=True)
    auto_prepare = adapters_sub.add_parser("prepare", help="Detect and use a source adapter when one is present")
    auto_prepare.add_argument("--source", type=Path, required=True, help="Source root to inspect for a known adapter signature")
    auto_prepare.add_argument("--out", type=Path, required=True, help="External adapter-selection output folder")

    codex_cmd = sub.add_parser("stage-codex", help="Stage Codex session JSONL as TrueMem chat-turn markdown")
    codex_cmd.add_argument("--sessions-root", type=Path, required=True)
    codex_cmd.add_argument("--output", type=Path, required=True)
    codex_cmd.add_argument("--session-index", type=Path)
    codex_cmd.add_argument("--max-files", type=int)

    codex_md_cmd = sub.add_parser("stage-codex-md", help="Stage visible Codex Markdown chat export as TrueMem chat-turn markdown")
    codex_md_cmd.add_argument("--input", type=Path, required=True)
    codex_md_cmd.add_argument("--output", type=Path, required=True)

    chatgpt_cmd = sub.add_parser("stage-chatgpt", help="Stage ChatGPT data export conversations as TrueMem chat-turn markdown")
    chatgpt_cmd.add_argument("--export-root", type=Path, required=True)
    chatgpt_cmd.add_argument("--output", type=Path, required=True)
    chatgpt_cmd.add_argument("--max-conversations", type=int)

    crosslink_cmd = sub.add_parser("crosslink", help="Build citation crosslinks between two dataset-local scopes")
    crosslink_cmd.add_argument("--runtime-root", type=Path, required=True)
    crosslink_cmd.add_argument("--left-dataset-id", required=True)
    crosslink_cmd.add_argument("--right-dataset-id", required=True)
    crosslink_cmd.add_argument("--question", required=True)
    crosslink_cmd.add_argument("--top-k", type=int, default=8)
    crosslink_cmd.add_argument("--min-shared", type=int, default=3)


    special_cmd = sub.add_parser(
        "special-search",
        help="Run JSON-list driven anchor special search reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Run the locked special-search path: JSON anchors -> solo search -> expanded context -> receipts.",
        epilog="""
Step-by-step:
  1. Prepare a JSON list with anchors or entries.
  2. Make sure the dataset has already been built with truemem docufilm-intake.
  3. Run:
       truemem special-search --runtime-root <runtime> --dataset-id <dataset> --trigger-list triggers.json --out reports/special_search
  4. Open trigger_anchor_summary.md and run_receipt.json when complete.
  5. Grouped phrases that cannot run as solo anchors are written to unmatched_phrases.jsonl.
""",
    )
    special_cmd.add_argument("--runtime-root", type=Path, required=True)
    special_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    special_cmd.add_argument("--trigger-list", type=Path, required=True)
    special_cmd.add_argument("--out", type=Path, required=True)
    special_cmd.add_argument("--expand-prev", type=int, default=1)
    special_cmd.add_argument("--expand-next", type=int, default=1)
    special_cmd.add_argument("--max-hits-per-anchor", type=int, default=500)
    determinism_cmd = sub.add_parser("determinism", help="Write a twin-machine dataset/query determinism receipt")
    determinism_cmd.add_argument("--runtime-root", type=Path, required=True)
    determinism_cmd.add_argument("--dataset-id", "--dataset", dest="dataset_id", required=True)
    determinism_cmd.add_argument("--question", action="append", help="Question to run into the raw packet comparison receipt")
    determinism_cmd.add_argument("--questions", type=Path, help="Plain text file with one question per line")
    determinism_cmd.add_argument("--top-k", type=int, default=5)
    determinism_cmd.add_argument("--output", type=Path, help="Optional receipt JSON path")
    osrl_cmd = sub.add_parser(
        "operator-state-audit",
        help="Audit operator input state without executing commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="OSRL v0 audit-only pass. Classifies operator input anchors, routing mode, and action gate.",
        epilog="""
Step-by-step:
  1. Provide --input or --input-file.
  2. OSRL extracts deterministic anchors and selects an audit mode.
  3. No production command is executed.
  4. No counts, citations, coordinates, or lifetime memory are mutated.
""",
    )
    osrl_cmd.add_argument("--input", dest="input_text", help="Operator input text to audit.")
    osrl_cmd.add_argument("--input-file", type=Path, help="File containing operator input text to audit.")
    osrl_cmd.add_argument("--output", type=Path, help="Optional JSON receipt path.")

    resonance_cmd = sub.add_parser(
        "resonance-adapt",
        help="Adapt an existing 6-1-6 resonance sample into TrueMem review artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Read-only adapter for standalone resonance sample folders. Does not run TrueMem intake, assign symbols, or write binaries.",
        epilog="""
Step-by-step:
  1. Point --source-dir at the standalone resonance sample folder.
  2. Point --out at an ignored runtime/report folder.
  3. Use --copy-source if you want review artifacts copied without touching the original.
  4. Add --symbolize only when you want adapter-local symbol artifacts.
  5. Review resonance_adapter_summary.md and receipts/run_receipt.json.
  6. Decide later whether this output earns native binary count storage.
""",
    )
    resonance_cmd.add_argument("--source-dir", type=Path, required=True)
    resonance_cmd.add_argument("--out", type=Path, required=True)
    resonance_cmd.add_argument("--dataset-id", default="resonance_sample")
    resonance_cmd.add_argument("--copy-source", action="store_true")
    resonance_cmd.add_argument("--symbolize", action="store_true", help="Write adapter-local symbol lexicon and symbolized relation edge files. Does not write native .awbin counts.")
    resonance_cmd.add_argument("--top-n", type=int, default=25)
    args = parser.parse_args()
    if args.command == "init":
        result = ensure_dataset(args.runtime_root, args.dataset_id, owner=args.owner)
    elif args.command == "docufilm-intake":
        result = docufilm_intake(
            args.runtime_root,
            args.dataset_id,
            args.source,
            owner=args.owner,
            window=args.window,
            workers=args.workers,
            reserve_ram_fraction=args.reserve_ram_fraction,
            ram_budget_gb=args.ram_budget_gb,
            show_progress=not args.no_progress,
            debug_tiny_single_core=args.debug_tiny_single_core,
        )
    elif args.command == "status":
        result = status(args.runtime_root, args.dataset_id)
    elif args.command == "system-metrics":
        result = system_metrics(
            runtime_root=args.runtime_root,
            dataset_id=args.dataset_id,
            workspace_path=args.workspace,
            repo_path=args.repo,
        )
    elif args.command == "dataset-overview":
        result = dataset_overview(
            args.runtime_root,
            args.dataset_id,
            args.out,
            top_anchors=args.top_anchors,
            top_relations=args.top_relations,
            trail_limit=args.trail_limit,
        )
    elif args.command == "query":
        result = query(
            args.runtime_root,
            args.dataset_id,
            args.question,
            top_k=args.top_k,
            created_after=args.created_after,
            created_before=args.created_before,
            speaker=args.speaker,
        )
    elif args.command == "deeper-wider":
        first_packet = json.loads(args.first_answer.read_text(encoding="utf-8"))
        first_answer = first_packet.get("anchor_prediction_answer", first_packet)
        first_walk = first_answer.get("prediction", first_answer)
        result = deeper_wider_after_answer(
            args.runtime_root,
            args.dataset_id,
            first_walk,
            depth=args.depth,
            width=args.width,
        )
    elif args.command == "qa-recent":
        result = recent_questions(args.runtime_root, args.dataset_id, limit=args.limit)
    elif args.command == "qa-export":
        result = export_ledger(args.runtime_root, args.dataset_id, args.output)
    elif args.command == "qa-show":
        result = show_record(args.runtime_root, args.dataset_id, args.record_id)
    elif args.command == "packet-speech":
        result = run_packet_speech(packet_paths=args.packet, out_dir=args.out)
    elif args.command == "evidence-speech":
        result = run_evidence_cloud_speech(
            packet_path=args.packet,
            question=args.question,
            out_dir=args.out,
            max_passes=args.max_passes,
            operator_stepped=not args.auto_passes,
        )
    elif args.command == "pressure-probe":
        if not args.packet and not args.batch_summary:
            parser.error("pressure-probe requires --packet or --batch-summary")
        result = run_pressure_probe(
            packet_paths=args.packet,
            batch_summary_path=args.batch_summary,
            out_dir=args.out,
            max_questions_per_packet=args.max_questions_per_packet,
        )
    elif args.command == "topk-diagnostic":
        if not args.packet and not args.batch_summary:
            parser.error("topk-diagnostic requires --packet or --batch-summary")
        result = run_topk_diagnostic(
            packet_paths=args.packet,
            batch_summary_path=args.batch_summary,
            out_dir=args.out,
            max_rank=args.max_rank,
        )
    elif args.command == "wide-deep-verify":
        expected = json.loads(args.expected.read_text(encoding="utf-8")) if args.expected else None
        result = run_wide_deep_verification(packet_path=args.packet, out_dir=args.out, expected=expected)
    elif args.command == "answer-reasoning-reverse-walk":
        result = run_answer_reasoning_reverse_walk(
            runtime_root=args.runtime_root,
            dataset_id=args.dataset_id,
            claims_path=args.claims,
            out_dir=args.out,
            mode=args.mode,
            top_k=args.top_k,
        )
    elif args.command == "pressure-coordination-audit":
        result = run_pressure_coordination_audit(
            trace_path=args.trace,
            out_dir=args.out,
        )
    elif args.command == "count-walk-speech":
        result = count_walk_speech(
            args.runtime_root,
            args.dataset_id,
            args.question,
            args.out,
            starter=args.starter,
            top_k=args.top_k,
            max_steps=args.max_steps,
            branch_k=args.branch_k,
        )
    elif args.command == "batch":
        result = batch_questions(args.runtime_root, args.dataset_id, args.questions, top_k=args.top_k, show_progress=not args.no_progress, workers=args.workers)
    elif args.command == "adapters":
        if args.adapter_command == "prepare":
            result = prepare_source_with_adapter_if_present(args.source, args.out)
        else:
            parser.error("unknown adapter command")
    elif args.command == "stage-codex":
        result = stage_codex_sessions(
            args.sessions_root,
            args.output,
            session_index_path=args.session_index,
            max_files=args.max_files,
        )
    elif args.command == "stage-codex-md":
        result = stage_codex_markdown_export(args.input, args.output)
    elif args.command == "stage-chatgpt":
        result = stage_chatgpt_export(
            args.export_root,
            args.output,
            max_conversations=args.max_conversations,
        )
    elif args.command == "crosslink":
        result = build_citation_crosslinks(
            args.runtime_root,
            args.left_dataset_id,
            args.right_dataset_id,
            args.question,
            top_k=args.top_k,
            min_shared=args.min_shared,
        )
    elif args.command == "special-search":
        result = special_search(
            args.runtime_root,
            args.dataset_id,
            args.trigger_list,
            args.out,
            expand_prev=args.expand_prev,
            expand_next=args.expand_next,
            max_hits_per_anchor=args.max_hits_per_anchor,
        )
    elif args.command == "determinism":
        result = determinism_receipt(
            args.runtime_root,
            args.dataset_id,
            questions=args.question,
            questions_path=args.questions,
            top_k=args.top_k,
            output_path=args.output,
        )
    elif args.command == "operator-state-audit":
        if bool(args.input_text) == bool(args.input_file):
            parser.error("operator-state-audit requires exactly one of --input or --input-file")
        raw_input = args.input_text if args.input_text is not None else args.input_file.read_text(encoding="utf-8")
        result = audit_operator_state(raw_input, output_path=args.output)
    elif args.command == "resonance-adapt":
        result = adapt_resonance_sample(
            args.source_dir,
            args.out,
            dataset_id=args.dataset_id,
            copy_source=args.copy_source,
            symbolize=args.symbolize,
            top_n=args.top_n,
        )
    else:
        parser.error("unknown command")

    print(json.dumps(with_protected_notice(result), ensure_ascii=True))


if __name__ == "__main__":
    main()
