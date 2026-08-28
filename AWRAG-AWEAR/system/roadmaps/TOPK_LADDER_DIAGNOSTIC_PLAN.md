# TopK Ladder Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded diagnostic lane that walks TopK evidence by rank layer, preserves the original evidence, classifies question/evidence anchors, recounts local evidence bundles, and reports bridge/gap/conflict without refusing or pretending final truth.

**Architecture:** This is a sidecar diagnostic path over existing AWEAR query packets and batch outputs. It must not mutate intake, retrieval ranking, qualification, speech, datasets, or benchmark metadata handling. Formula work is deferred until the diagnostic receipts show what the evidence field is doing.

**Tech Stack:** Python package under `src/awrag`, existing AWEAR CLI, pytest, JSON/JSONL receipts, existing anchor/count/query helpers.

---

## Current Repo Boundary

There is already dirty work in the active checkout for the pressure coordination sidecar:

- `src/awrag/cli.py`
- `src/awrag/agents/pressure_coordination.py`
- `tests/test_pressure_coordination_agent.py`
- `system/reasoning/PRESSURE_COORDINATION_AGENT.md`
- `system/reasoning/REAPER_PRESSURE_COORDINATION_NOTES.md`
- `system/reasoning/RD_REASONING_TOOLBOX_IMPLEMENTATION_GUIDE.md`
- `system/reports/FULL_REPO_REPORT.md`
- `system/reasoning/README.md`
- `tests/test_awear_aliases.py`

Do not mix TopK ladder work into that commit unless explicitly approved. Finish or shelve that bucket first, or create the TopK ladder changes as a separate commit after it.

## Three Run Split

### Run 1: Non-Refusal TopK Diagnostic Packet

**Purpose:** For each question, classify anchors, retrieve TopK, preserve pulled passages, classify each evidence location, cross-classify question anchors against evidence anchors, generate per-rank speech attempts, recount the TopK bundle, and emit a diagnostic packet.

**Files:**
- Create: `src/awrag/engine/legal_anchor_typing.py`
- Create: `src/awrag/engine/topk_diagnostic.py`
- Modify: `src/awrag/engine/__init__.py`
- Modify: `src/awrag/cli.py`
- Test: `tests/test_topk_diagnostic.py`
- Test: `tests/test_legal_anchor_typing.py`
- Document: `system/reasoning/TOPK_LADDER_DIAGNOSTIC.md`

**Behavior Contract:**
- No refusal during this diagnostic run.
- No fake certainty.
- No ranking mutation.
- No dataset mutation.
- No answer-key or benchmark metadata logic.
- Preserve every original TopK passage exactly as pulled.
- Output says `diagnostic_not_final_truth`.
- Local anchor typing is diagnostic metadata only. It must not hardcode dataset-specific IDs, answer keys, or expected passages.

- [ ] **Step 0: Write failing tests for typed legal/local anchors**

Create `tests/test_legal_anchor_typing.py`:

```python
from awrag.engine.legal_anchor_typing import classify_anchor_occurrences


def test_classifies_same_word_by_local_legal_shape():
    text = "Section 12 means court. The court may excuse a juror unless the statute requires service."

    rows = classify_anchor_occurrences(text)
    by_anchor = {}
    for row in rows:
        by_anchor.setdefault(row["anchor"], []).append(row)

    section_rows = by_anchor["section"]
    court_rows = by_anchor["court"]
    may_rows = by_anchor["may"]
    unless_rows = by_anchor["unless"]
    requires_rows = by_anchor["requires"]

    assert section_rows[0]["anchor_type"] == "authority_anchor"
    assert court_rows[0]["anchor_type"] == "definition_anchor"
    assert may_rows[0]["anchor_type"] == "discretion_anchor"
    assert unless_rows[0]["anchor_type"] == "exception_anchor"
    assert requires_rows[0]["anchor_type"] == "duty_anchor"
    assert court_rows[0]["proof_need"] == "definition_controls_meaning"
```

- [ ] **Step 0a: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_legal_anchor_typing.py -q
```

Expected: fail because `awrag.engine.legal_anchor_typing` does not exist.

- [ ] **Step 0b: Implement small typed-anchor helper**

Create `src/awrag/engine/legal_anchor_typing.py`:

```python
from __future__ import annotations

import re
from typing import Any

from .anchors import anchorize


AUTHORITY_MARKERS = {"section", "statute", "rule", "s", "§"}
DEFINITION_MARKERS = {"means", "includes", "defined"}
EXCEPTION_MARKERS = {"unless", "except", "provided"}
MANDATORY_MARKERS = {"must", "shall", "required", "requires"}
DISCRETION_MARKERS = {"may", "can", "discretion"}


def classify_anchor_occurrences(text: str, *, window: int = 6) -> list[dict[str, Any]]:
    tokens = _tokenize_with_shape(text)
    rows: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        anchor = _clean_anchor(token["text"])
        if not anchor:
            continue
        left = [_clean_anchor(row["text"]) for row in tokens[max(0, index - window) : index]]
        right = [_clean_anchor(row["text"]) for row in tokens[index + 1 : index + 1 + window]]
        features = {
            "has_section_marker": anchor in AUTHORITY_MARKERS or _contains(left + right, AUTHORITY_MARKERS),
            "has_case_marker": _near_case_marker(tokens, index, window),
            "has_definition_marker": anchor in DEFINITION_MARKERS or _contains(right, DEFINITION_MARKERS),
            "has_exception_marker": anchor in EXCEPTION_MARKERS or _contains(left + right, EXCEPTION_MARKERS),
            "has_mandatory_marker": anchor in MANDATORY_MARKERS or _contains(left + right, MANDATORY_MARKERS),
            "has_discretion_marker": anchor in DISCRETION_MARKERS or _contains(left + right, DISCRETION_MARKERS),
            "punctuation_shape": token["punctuation_shape"],
            "heading_shape": token["heading_shape"],
        }
        anchor_type, proof_need = _type_from_features(features)
        rows.append(
            {
                "anchor": anchor,
                "anchor_type": anchor_type,
                "symbol": f"{anchor}[{anchor_type}]",
                "features": features,
                "proof_need": proof_need,
            }
        )
    return rows


def typed_anchor_summary(text: str) -> dict[str, Any]:
    rows = classify_anchor_occurrences(text)
    return {
        "schema": "awear_typed_anchor_summary@1",
        "all_anchors": anchorize(text),
        "typed_anchors": rows,
        "proof_needs": sorted({row["proof_need"] for row in rows}),
    }


def _type_from_features(features: dict[str, Any]) -> tuple[str, str]:
    if features["has_definition_marker"]:
        return "definition_anchor", "definition_controls_meaning"
    if features["has_exception_marker"]:
        return "exception_anchor", "check_if_exception_applies"
    if features["has_mandatory_marker"]:
        return "duty_anchor", "prove_required_condition"
    if features["has_discretion_marker"]:
        return "discretion_anchor", "prove_allowed_not_required"
    if features["has_section_marker"]:
        return "authority_anchor", "cite_statute_or_section"
    if features["has_case_marker"]:
        return "case_authority_anchor", "cite_case_relationship"
    return "plain_language_anchor", "ordinary_context_check"


def _tokenize_with_shape(text: str) -> list[dict[str, Any]]:
    rows = []
    for match in re.finditer(r"\S+", text):
        raw = match.group(0)
        rows.append(
            {
                "text": raw,
                "punctuation_shape": "".join(ch for ch in raw if not ch.isalnum()),
                "heading_shape": raw.isupper() and len(raw) > 1,
            }
        )
    return rows


def _clean_anchor(token: str) -> str:
    cleaned = re.sub(r"(^[^\w§]+|[^\w§]+$)", "", token.lower())
    return cleaned if cleaned in anchorize(cleaned) or cleaned == "§" else cleaned


def _contains(values: list[str], markers: set[str]) -> bool:
    return any(value in markers for value in values if value)


def _near_case_marker(tokens: list[dict[str, Any]], index: int, window: int) -> bool:
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)
    nearby = " ".join(str(row["text"]) for row in tokens[start:end]).lower()
    return bool(re.search(r"\bv\.|\bvs\.", nearby))
```

- [ ] **Step 0c: Run typed-anchor tests**

Run:

```powershell
python -m pytest tests/test_legal_anchor_typing.py -q
```

Expected: pass.

- [ ] **Step 1: Write failing tests for a single diagnostic packet**

Create `tests/test_topk_diagnostic.py` with fixture packets and assertions for:

```python
from awrag.engine.topk_diagnostic import build_topk_diagnostic_packet


def test_topk_diagnostic_preserves_passages_and_refuses_nothing():
    packet = {
        "question": "What excuses a juror from serving?",
        "answer_packet": {
            "locations": [
                {
                    "rank": 1,
                    "citation": "rule-1.md",
                    "text": "A juror may be excused from serving if disqualified by law.",
                    "qualification": {"support_state": "unsupported"},
                }
            ],
            "speech": {"answer": "Existing speech attempt."},
        },
    }

    result = build_topk_diagnostic_packet(packet, max_rank=5)

    assert result["schema"] == "awear_topk_diagnostic_packet@1"
    assert result["diagnostic_mode"] == "no_refusal"
    assert result["truth_status"] == "diagnostic_not_final_truth"
    assert result["topk_results"][0]["original_passage"] == "A juror may be excused from serving if disqualified by law."
    assert result["topk_results"][0]["rank"] == 1
    assert "juror" in result["question_anchor_classification"]["all_anchors"]
    assert "typed_anchors" in result["topk_results"][0]["evidence_anchor_classification"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_topk_diagnostic.py -q
```

Expected: fail because `awrag.engine.topk_diagnostic` does not exist.

- [ ] **Step 3: Implement minimal diagnostic packet builder**

Create `src/awrag/engine/topk_diagnostic.py` with:

```python
from __future__ import annotations

from collections import Counter
from typing import Any

from .anchors import anchorize
from .legal_anchor_typing import typed_anchor_summary


def build_topk_diagnostic_packet(packet: dict[str, Any], *, max_rank: int = 5) -> dict[str, Any]:
    question = str(packet.get("question") or packet.get("input_question") or "")
    answer_packet = packet.get("answer_packet") if isinstance(packet.get("answer_packet"), dict) else packet
    locations = answer_packet.get("locations") if isinstance(answer_packet, dict) else []
    question_anchors = _classify_question_anchors(question)
    rows = []
    bundle_counter: Counter[str] = Counter()

    for index, location in enumerate(locations or [], start=1):
        if index > max_rank:
            break
        if not isinstance(location, dict):
            continue
        text = str(location.get("text") or location.get("passage") or "")
        evidence_anchors = _classify_evidence_anchors(text)
        bundle_counter.update(evidence_anchors["all_anchors"])
        rows.append(
            {
                "rank": int(location.get("rank") or index),
                "citation": location.get("citation"),
                "coordinates": location.get("coordinates"),
                "original_passage": text,
                "evidence_anchor_classification": evidence_anchors,
                "question_evidence_cross_classification": _cross_classify(question_anchors, evidence_anchors),
                "topk_speech_answer": _rank_speech(question, location, evidence_anchors),
                "local_recount": dict(Counter(evidence_anchors["all_anchors"]).most_common(25)),
                "bridge_conflict_gap_status": _bridge_status(question_anchors, evidence_anchors),
            }
        )

    return {
        "schema": "awear_topk_diagnostic_packet@1",
        "diagnostic_mode": "no_refusal",
        "truth_status": "diagnostic_not_final_truth",
        "question": question,
        "question_anchor_classification": question_anchors,
        "topk_results": rows,
        "topk_bundle_recount": dict(bundle_counter.most_common(50)),
        "receipt": {
            "no_refusal": True,
            "no_ranking_mutation": True,
            "no_dataset_mutation": True,
            "no_answer_key_leakage": True,
        },
    }


def _classify_question_anchors(question: str) -> dict[str, Any]:
    typed = typed_anchor_summary(question)
    anchors = typed["all_anchors"]
    return {
        "all_anchors": anchors,
        "typed_anchors": typed["typed_anchors"],
        "proof_needs": typed["proof_needs"],
        "scenario_anchors": [],
        "evidence_bearing_anchors": anchors,
        "ambiguity_anchors": [],
    }


def _classify_evidence_anchors(text: str) -> dict[str, Any]:
    typed = typed_anchor_summary(text)
    anchors = typed["all_anchors"]
    return {
        "all_anchors": anchors,
        "typed_anchors": typed["typed_anchors"],
        "proof_needs": typed["proof_needs"],
        "evidence_anchors": anchors,
        "weak_anchors": [],
    }


def _cross_classify(question_anchors: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    q = set(question_anchors.get("all_anchors") or [])
    e = set(evidence_anchors.get("all_anchors") or [])
    return {
        "matched_anchors": sorted(q & e),
        "missing_question_anchors": sorted(q - e),
        "extra_evidence_anchors": sorted(e - q),
    }


def _bridge_status(question_anchors: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    cross = _cross_classify(question_anchors, evidence_anchors)
    matched = len(cross["matched_anchors"])
    missing = len(cross["missing_question_anchors"])
    status = "bridge_possible" if matched and missing else "direct_overlap" if matched else "gap"
    return {"status": status, "matched_count": matched, "missing_count": missing, "conflict_count": 0}


def _rank_speech(question: str, location: dict[str, Any], evidence_anchors: dict[str, Any]) -> dict[str, Any]:
    citation = location.get("citation") or "uncited"
    dominant = ", ".join((evidence_anchors.get("all_anchors") or [])[:8])
    return {
        "mode": "topk_rank_attempt",
        "answer": f"Rank evidence at {citation} points to: {dominant}",
        "warning": "diagnostic speech from one TopK slice; not final truth",
    }
```

- [ ] **Step 4: Export the function**

Modify `src/awrag/engine/__init__.py`:

```python
from .topk_diagnostic import build_topk_diagnostic_packet
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_topk_diagnostic.py -q
```

Expected: pass.

- [ ] **Step 6: Add CLI command after current dirty CLI bucket is handled**

Modify `src/awrag/cli.py` only in a separate TopK commit:

```python
topk_diag_cmd = sub.add_parser("topk-diagnostic", help="Build no-refusal TopK diagnostic packets from existing query or batch output")
topk_diag_cmd.add_argument("--packet", type=Path)
topk_diag_cmd.add_argument("--batch-summary", type=Path)
topk_diag_cmd.add_argument("--out", type=Path, required=True)
topk_diag_cmd.add_argument("--max-rank", type=int, default=5)
```

Implement loading existing query/batch packet files and writing:

```text
TOPK_DIAGNOSTIC_PACKETS.jsonl
TOPK_DIAGNOSTIC_SUMMARY.json
RUN_RECEIPT.json
```

- [ ] **Step 7: Document the lane**

Create `system/reasoning/TOPK_LADDER_DIAGNOSTIC.md` describing:

```text
No refusal.
No fake certainty.
Diagnostic packet, not final truth.
TopK evidence preserved exactly.
Speech is per-rank diagnostic speech.
```

- [ ] **Step 8: Run full tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

### Run 2: Rank-Layer TopK Ladder Walk

**Purpose:** Walk TopK by rank across all questions: all rank 1 evidence first, then all rank 2, through rank 5. This detects whether rank 2/3/4/5 carry bridge evidence that rank 1 misses.

**Files:**
- Modify: `src/awrag/engine/topk_diagnostic.py`
- Modify: `src/awrag/cli.py`
- Test: `tests/test_topk_diagnostic.py`
- Document: `system/reasoning/TOPK_LADDER_DIAGNOSTIC.md`

**Output Files:**

```text
rank_layers/TOPK_LAYER_1.jsonl
rank_layers/TOPK_LAYER_2.jsonl
rank_layers/TOPK_LAYER_3.jsonl
rank_layers/TOPK_LAYER_4.jsonl
rank_layers/TOPK_LAYER_5.jsonl
TOPK_LADDER_SUMMARY.json
TOPK_LADDER_SUMMARY.md
```

- [ ] **Step 1: Write failing layer-order test**

Add test:

```python
from awrag.engine.topk_diagnostic import build_rank_layer_walk


def test_rank_layer_walk_runs_across_questions_by_rank():
    packets = [
        {"question": "Q1 juror excuse", "answer_packet": {"locations": [{"rank": 1, "text": "juror excuse"}, {"rank": 2, "text": "jury service"}]}},
        {"question": "Q2 court rule", "answer_packet": {"locations": [{"rank": 1, "text": "court rule"}, {"rank": 2, "text": "judge order"}]}},
    ]

    result = build_rank_layer_walk(packets, max_rank=2)

    assert [row["question_index"] for row in result["layers"][1]] == [1, 2]
    assert [row["rank"] for row in result["layers"][1]] == [1, 1]
    assert [row["question_index"] for row in result["layers"][2]] == [1, 2]
    assert [row["rank"] for row in result["layers"][2]] == [2, 2]
```

- [ ] **Step 2: Implement `build_rank_layer_walk`**

Add:

```python
def build_rank_layer_walk(packets: list[dict[str, Any]], *, max_rank: int = 5) -> dict[str, Any]:
    diagnostics = [
        build_topk_diagnostic_packet(packet, max_rank=max_rank)
        for packet in packets
    ]
    layers: dict[int, list[dict[str, Any]]] = {rank: [] for rank in range(1, max_rank + 1)}
    for question_index, diagnostic in enumerate(diagnostics, start=1):
        question = diagnostic["question"]
        starter = _answer_starter_with_subject(question, diagnostic["question_anchor_classification"])
        for row in diagnostic["topk_results"]:
            rank = int(row["rank"])
            if 1 <= rank <= max_rank:
                layers[rank].append(
                    {
                        "question_index": question_index,
                        "question": question,
                        "answer_starter_with_subject": starter,
                        **row,
                    }
                )
    return {
        "schema": "awear_topk_ladder_walk@1",
        "walk_order": "rank_layer_across_questions",
        "max_rank": max_rank,
        "layers": layers,
        "receipt": {"no_refusal": True, "no_dataset_mutation": True, "no_ranking_mutation": True},
    }


def _answer_starter_with_subject(question: str, classification: dict[str, Any]) -> str:
    anchors = classification.get("evidence_bearing_anchors") or classification.get("all_anchors") or []
    subject = str(anchors[0]) if anchors else "the question"
    return f"For {subject}, the cited evidence starts from"
```

- [ ] **Step 3: Add writer function**

Add a writer that creates one JSONL per rank layer and a summary receipt. Use JSON APIs only.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/test_topk_diagnostic.py -q
```

Expected: pass.

- [ ] **Step 5: Operational dry run on existing batch output**

Use an existing batch summary from runtime if available. Output to a new runtime report folder, not source:

```powershell
python -m awear.cli topk-diagnostic --batch-summary <batch_run_summary.json> --out I:\AWRAG_Central_Raw_Data\awrag_runtime\reports\topk_ladder_run_1 --max-rank 5
```

Expected: writes layer files and receipts. It must not ingest, query, rank, or mutate datasets.

### Run 3: Formula Candidate Sandbox

**Purpose:** Use the TopK ladder receipts to design evidence math candidates. This run does not promote formulas into core behavior until they are tested against diagnostic packets.

**Files:**
- Create: `src/awrag/engine/evidence_formula.py`
- Test: `tests/test_evidence_formula.py`
- Document: `system/reasoning/EVIDENCE_FORMULA_CANDIDATES.md`

**Candidate Formula Shape:**

```text
final_support =
  evidence_anchor_strength
+ citation_pressure
+ local_field_coherence
+ bridge_strength
- contradiction_pressure
- missing_required_anchor_penalty
```

**Boundaries:**
- Claude/Manus may produce ideas only.
- No outside tool gets repo/data authority.
- No formula changes retrieval, ranking, qualification, speech, or intake in this run.
- Formula outputs are diagnostics only.

- [ ] **Step 1: Write tests for bounded score components**

Create `tests/test_evidence_formula.py`:

```python
from awrag.engine.evidence_formula import score_evidence_formula


def test_formula_rewards_bridge_and_penalizes_missing_required():
    row = {
        "question_evidence_cross_classification": {
            "matched_anchors": ["juror", "excuse"],
            "missing_question_anchors": ["judge"],
        },
        "bridge_conflict_gap_status": {"status": "bridge_possible", "conflict_count": 0},
        "local_recount": {"juror": 3, "excuse": 2},
        "citation": "rule.md",
    }

    score = score_evidence_formula(row)

    assert 0.0 <= score["support_score"] <= 1.0
    assert score["components"]["bridge_strength"] > 0
    assert score["components"]["missing_required_anchor_penalty"] > 0
```

- [ ] **Step 2: Implement small scoring helper**

Create `src/awrag/engine/evidence_formula.py`:

```python
from __future__ import annotations

from typing import Any


def score_evidence_formula(row: dict[str, Any]) -> dict[str, Any]:
    cross = row.get("question_evidence_cross_classification") or {}
    bridge = row.get("bridge_conflict_gap_status") or {}
    recount = row.get("local_recount") or {}
    matched = len(cross.get("matched_anchors") or [])
    missing = len(cross.get("missing_question_anchors") or [])
    conflicts = int(bridge.get("conflict_count") or 0)
    citation_pressure = 0.15 if row.get("citation") else 0.0
    evidence_anchor_strength = min(0.35, matched * 0.08)
    local_field_coherence = min(0.2, len(recount) * 0.01)
    bridge_strength = 0.15 if bridge.get("status") in {"bridge_possible", "direct_overlap"} else 0.0
    contradiction_pressure = min(0.35, conflicts * 0.12)
    missing_required_anchor_penalty = min(0.3, missing * 0.04)
    raw = evidence_anchor_strength + citation_pressure + local_field_coherence + bridge_strength - contradiction_pressure - missing_required_anchor_penalty
    return {
        "schema": "awear_evidence_formula_score@1",
        "support_score": round(max(0.0, min(1.0, raw)), 4),
        "components": {
            "evidence_anchor_strength": round(evidence_anchor_strength, 4),
            "citation_pressure": round(citation_pressure, 4),
            "local_field_coherence": round(local_field_coherence, 4),
            "bridge_strength": round(bridge_strength, 4),
            "contradiction_pressure": round(contradiction_pressure, 4),
            "missing_required_anchor_penalty": round(missing_required_anchor_penalty, 4),
        },
        "diagnostic_only": True,
    }
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/test_evidence_formula.py -q
```

Expected: pass.

- [ ] **Step 4: Document formula candidates**

Create `system/reasoning/EVIDENCE_FORMULA_CANDIDATES.md` with:

```text
Formula candidates are diagnostic-only.
They do not decide final truth.
They do not mutate ranking, retrieval, qualification, or speech.
Promotion requires a separate review and tests.
```

- [ ] **Step 5: Run full tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

## Commit Boundaries

Use three separate commits only after each run is tested:

```text
1. Add no-refusal TopK diagnostic packets
2. Add TopK rank-layer ladder walk
3. Add diagnostic evidence formula sandbox
```

Do not commit runtime reports. Runtime reports belong under:

```text
I:\AWRAG_Central_Raw_Data\awrag_runtime\reports
```

## Self-Review

Spec coverage:

- No-refusal diagnostic run: Run 1.
- Preserve pulled passages/data: Run 1.
- Classify question and evidence anchors: Run 1.
- Cross-classify question/evidence: Run 1.
- Generate TopK speech attempts: Run 1.
- Recount TopK evidence bundle: Run 1.
- Remap local evidence field: Run 1/2 via recount and bridge/gap/conflict fields.
- TopK ladder walk across all questions by rank: Run 2.
- Answer starter with subject anchor: Run 2.
- Math/formula work after receipts: Run 3.
- External idea engines have no authority: Run 3 boundaries.

No known placeholders remain. Formula constants are intentionally initial diagnostic defaults, not production truth thresholds.
