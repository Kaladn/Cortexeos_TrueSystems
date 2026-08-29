# R&D Reasoning Toolbox Implementation Guide

Date: 2026-06-25

## Executive Summary

The R&D toolbox contains useful reasoning shapes, but no old runtime should be
imported into TrueMem. The safe path is:

```text
old reasoning shapes teach
new TrueMem helpers implement
```

The best reusable patterns are small:

```text
anchor coordination
bridge answerability
candidate contradiction checks
topK pressure stability
local-neighborhood cloud comparison
bounded hypothesis composition
temporal receipt ordering
sidecar approval gates
```

Do not revive REAPER, Clearbox, CortexOS, Swarm, Resonance, Cognition, or
TrueCore as product dependencies. Translate specific ideas into TrueMem-native
helpers operating on anchors, counts, citations, coordinates, pressure,
bridge state, contradiction state, admission, audit, and speech.

Recommended next implementation:

```text
Implement one sidecar helper: contradiction_pressure_score(trace_candidate)
```

It should inspect admitted and rejected evidence candidates, compare answer
anchors to nearby cited blocks, and penalize REAPER/pressure promotions when a
candidate has strong missing bridge signals or contradiction anchors. It belongs
beside the existing pressure coordination agent, not in core retrieval.

## R&D Inventory

Inventory source:

```text
research_reference_not_runtime/reasoning_toolbox
```

Directory summary:

```text
imported_reference_code          24 files, about 430 KB
machine_log_reasoners        6,812 files, about 75 MB
reference_requests_do_not_run    2 files, about 4 KB
scan_manifests                   3 files, about 19 MB
truecore_agent_references      5 files, about 18 KB
source_manifests                 5 files, about 18 KB
temporal_causality_manifests     9 files, about 2.4 MB
test_run_logs                   10 files, about 54 KB
whole_pc_selected_references    19 files, about 18 MB
```

Key reference files:

```text
research_reference_not_runtime/reasoning_toolbox/README.md
research_reference_not_runtime/reasoning_toolbox/reference_requests_do_not_run/request.md
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/05_reaper_multi_anchor_scoring/reaper_cognitive_engine.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/clearbox/6a8eeff1be1a__6a8eeff1be1a__engine.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/clearbox/f8e2cd242ef4__f8e2cd242ef4__reasoning_service.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/cortexos/27ef6d1d1bb5__27ef6d1d1bb5__topk_sparse_resonance.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/cortexos/049d01a29e0c__049d01a29e0c__trust_filter.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/cortexos/c0fbc283f01f__c0fbc283f01f__knowledge_reinforcer.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/arc_solver/8de1ac8e8cf0__8de1ac8e8cf0__arc_core.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/arc_solver/f922242d1192__f922242d1192__composition_engine.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/compucog/84da29e6e0eb__84da29e6e0eb__binary_log.functions.py
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/extracted_function_fallbacks/compucog/e8df3326fab3__e8df3326fab3__recognition_field.functions.py
research_reference_not_runtime/reasoning_toolbox/whole_pc_selected_references/phone_download_mtp/swarm_resonance.py
research_reference_not_runtime/reasoning_toolbox/whole_pc_selected_references/phone_download_mtp/resonance_field.py
research_reference_not_runtime/reasoning_toolbox/whole_pc_selected_references/phone_download_mtp/resonance_monitor.py
research_reference_not_runtime/reasoning_toolbox/truecore_agent_references/runner/truecore_agent_runner.py
```

Existing toolbox law:

```text
R&D files are reference snapshots only.
Do not import them from src/truemem.
Do not execute request-note folders or recovered agent code as product runtime.
Promote ideas only through normal TrueMem code, tests, docs, and receipts.
```

## 10 Use-Case Scenarios

### 1. Bridge Answerability Cap

Source reference:

```text
imported_reference_code/05_reaper_multi_anchor_scoring/reaper_cognitive_engine.py
```

Concept extracted:

```text
Multi-anchor coordination and coherence should affect the final pressure state.
```

TrueMem translation:

```text
bridge_answerability_score(trace)
```

Where it belongs:

```text
agent / sidecar
```

Risk:

```text
Too eager promotion if the score ignores missing bridge anchors.
```

Test idea:

```text
needs_bridge cannot become supported when bridge_answerability_score < 0.72
```

Pseudocode:

```text
score = matched_question_anchor_ratio * 0.45
score += answer_anchor_coverage * 0.35
score += local_neighbor_pressure * 0.20
if bridge_needed and score < threshold:
    cap_decision = "needs_bridge"
```

Disposition:

```text
implement now
```

### 2. Contradiction Pressure Score

Source reference:

```text
clearbox/6a8eeff1be1a__6a8eeff1be1a__engine.functions.py
cortexos/049d01a29e0c__049d01a29e0c__trust_filter.functions.py
```

Concept extracted:

```text
Support metrics need uncertainty and trust penalties, not only positive matches.
```

TrueMem translation:

```text
contradiction_pressure_score(candidate, question_anchors, answer_anchors)
```

Where it belongs:

```text
sidecar / agent / audit
```

Risk:

```text
Naive negation words can falsely mark ordinary legal exceptions as contradictions.
```

Test idea:

```text
A candidate with strong answer anchors but a nearby opposite duty/exclusion term
is marked partially_supported or needs_bridge, not supported.
```

Pseudocode:

```text
negative_hits = count(candidate.anchors & contradiction_anchors)
missing_core = count(answer_core_anchors - candidate.anchors)
if negative_hits and missing_core:
    return 0.75
if negative_hits:
    return 0.35
return 0.0
```

Disposition:

```text
implement now
```

### 3. Local Pressure Cloud Compare

Source reference:

```text
clearbox/6a8eeff1be1a__6a8eeff1be1a__engine.functions.py
```

Concept extracted:

```text
Compare a query cloud to candidate clouds with local and layered scoring.
```

TrueMem translation:

```text
compare_pressure_windows(question_field, candidate_prev_current_next)
```

Where it belongs:

```text
sidecar / qualification later
```

Risk:

```text
If promoted into core too early, it can mutate ranking behavior.
```

Test idea:

```text
Same citation previous/current/next blocks raise local_support_delta without
changing original rank order.
```

Pseudocode:

```text
current = coverage(question_evidence_anchors, current_block)
neighbor = max(coverage(question_evidence_anchors, prev), coverage(..., next))
return {"local_support_delta": neighbor - current, "no_rank_mutation": True}
```

Disposition:

```text
implement later
```

### 4. TopK Pressure Stability

Source reference:

```text
cortexos/27ef6d1d1bb5__27ef6d1d1bb5__topk_sparse_resonance.functions.py
```

Concept extracted:

```text
TopK matches can be audited for threshold stability, decay, and sparse pressure.
```

TrueMem translation:

```text
topk_pressure_stability(topk_candidates)
```

Where it belongs:

```text
audit / sidecar
```

Risk:

```text
Do not use it to reorder topK without a separate ranking review.
```

Test idea:

```text
The helper reports stable/unstable topK pressure while candidate order remains unchanged.
```

Pseudocode:

```text
scores = [candidate.native_rank_score for candidate in topk]
gap = scores[0] - scores[-1]
return "stable" if gap >= min_gap and scores[0] >= threshold else "thin"
```

Disposition:

```text
implement later
```

### 5. Evidence Admission Trust Receipt

Source reference:

```text
cortexos/049d01a29e0c__049d01a29e0c__trust_filter.functions.py
```

Concept extracted:

```text
Trust evaluation should be inspectable and based on metadata completeness,
citations, and temporal factors.
```

TrueMem translation:

```text
admission_trust_receipt(candidate)
```

Where it belongs:

```text
audit / qualification later
```

Risk:

```text
Source reputation can become subjective or dataset-specific if not constrained.
```

Test idea:

```text
Candidate with citation, coordinate, source file, and block id scores higher
than candidate with missing coordinate metadata.
```

Pseudocode:

```text
score = 0
score += 0.30 if citation_id else 0
score += 0.30 if source_coordinates else 0
score += 0.20 if source_path else 0
score += 0.20 if block_id else 0
```

Disposition:

```text
keep as doctrine
```

### 6. Bounded Hypothesis Composition

Source reference:

```text
arc_solver/8de1ac8e8cf0__8de1ac8e8cf0__arc_core.functions.py
arc_solver/f922242d1192__f922242d1192__composition_engine.functions.py
```

Concept extracted:

```text
Try single explanations first, then bounded two-step compositions, and stop.
```

TrueMem translation:

```text
bridge_hypothesis_chain(max_depth=2)
```

Where it belongs:

```text
sidecar / audit
```

Risk:

```text
Can become a sprawling reasoning engine if max depth and candidate count are not hard-capped.
```

Test idea:

```text
Given three bridge candidates, helper evaluates at most N single and M pair hypotheses.
```

Pseudocode:

```text
for candidate in candidates[:max_single]:
    test(candidate)
for left, right in pairs(candidates[:max_pair_pool])[:max_pairs]:
    test_bridge(left, right)
```

Disposition:

```text
implement later
```

### 7. Recognition Field From Evidence Shape

Source reference:

```text
arc_solver/5f050450a35f__5f050450a35f__arc_recognition_field.functions.py
compucog/e8df3326fab3__e8df3326fab3__recognition_field.functions.py
```

Concept extracted:

```text
Detect named shapes from observed evidence, then report confidence and trace.
```

TrueMem translation:

```text
evidence_shape_classifier(packet)
```

Where it belongs:

```text
audit / speech later
```

Risk:

```text
The classifier can sound like answer generation if it is allowed to speak.
```

Test idea:

```text
The helper labels a packet as direct_fact, exception_rule, multi_passage_bridge,
or unresolved without changing support_status.
```

Pseudocode:

```text
if one_candidate_high_coverage:
    return "direct_fact"
if multiple_candidates_cover_disjoint_core_terms:
    return "multi_passage_bridge"
if contradiction_pressure:
    return "exception_or_conflict"
```

Disposition:

```text
keep as doctrine
```

### 8. Temporal/Causal Receipt Ordering

Source reference:

```text
temporal_causality_manifests/Temporal_Log_Causality_Manifest_RG_20260516_104606_NO_THIRD_PARTY
compucog/84da29e6e0eb__84da29e6e0eb__binary_log.functions.py
compucog/9e623d2ba26f__9e623d2ba26f__pulse_writer.functions.py
```

Concept extracted:

```text
Append-only records, offsets, pulse ids, time windows, and ordered causality logs.
```

TrueMem translation:

```text
reasoning_run_event_log.jsonl
```

Where it belongs:

```text
audit / receipts
```

Risk:

```text
Binary log complexity is not needed yet; JSONL receipts are enough.
```

Test idea:

```text
A run emits monotonically increasing sequence numbers and preserves phase order:
prepare -> intake -> query -> audit -> sidecar.
```

Pseudocode:

```text
write_event(seq=next_seq(), phase="query", input_hash=..., output_path=...)
assert seq values are strictly increasing
```

Disposition:

```text
implement later
```

### 9. Swarm Consensus Without Swarm Runtime

Source reference:

```text
whole_pc_selected_references/phone_download_mtp/swarm_resonance.py
whole_pc_selected_references/phone_download_mtp/Advanced Swarm Intelligence Algorithm.txt
```

Concept extracted:

```text
Multiple independent candidate views can vote through collective similarity and fallback modes.
```

TrueMem translation:

```text
multi_lane_support_consensus(real_lane, reaper_lane, contradiction_lane)
```

Where it belongs:

```text
agent / sidecar
```

Risk:

```text
Do not create autonomous agents that overwrite evidence mechanics.
```

Test idea:

```text
If real_lane is needs_bridge and contradiction_lane is high, consensus cannot be supported
even when reaper_lane is supported.
```

Pseudocode:

```text
votes = [real, reaper, contradiction]
if real == "needs_bridge" and contradiction > 0.5:
    return "needs_bridge"
return conservative_max(votes)
```

Disposition:

```text
implement later
```

### 10. Human Approval Gate For Mutating Agents

Source reference:

```text
truecore_agent_references/runner/truecore_agent_runner.py
truecore_agent_references/README.md
```

Concept extracted:

```text
Any mutating recovered-agent behavior requires exact human approval and dry-run support.
```

TrueMem translation:

```text
operator_action_gate(action, destruction_score, approval_phrase)
```

Where it belongs:

```text
adapter / operator / future action bridge
```

Risk:

```text
Not needed for current read-only evidence reasoning; can distract from retrieval work.
```

Test idea:

```text
Mutating action refuses unless exact approval phrase is supplied. Dry-run never mutates.
```

Pseudocode:

```text
if action.mutating and supplied_approval != required_phrase:
    return refused_receipt
if dry_run:
    return preview_receipt
```

Disposition:

```text
implement later
```

## Candidate Helper Functions

Implement now:

```text
bridge_answerability_score(trace) -> float
contradiction_pressure_score(candidate, question_anchors, answer_anchors) -> float
```

Implement later:

```text
compare_pressure_windows(question_field, prev_current_next) -> dict
topk_pressure_stability(topk_candidates) -> dict
bridge_hypothesis_chain(candidates, max_depth=2, max_pairs=8) -> dict
multi_lane_support_consensus(real_lane, reaper_lane, contradiction_lane) -> dict
reasoning_run_event_log_append(event) -> receipt
```

Keep as doctrine for now:

```text
admission_trust_receipt(candidate)
evidence_shape_classifier(packet)
operator_action_gate(action)
```

## Candidate Sidecar Agents

Current:

```text
pressure_coordination_audit
```

Next:

```text
contradiction_pressure_audit
```

Later:

```text
bridge_hypothesis_audit
topk_stability_audit
reasoning_run_receipt_audit
```

Sidecar law:

```text
no retrieval mutation
no topK mutation
no intake mutation
no speech mutation
no model calls
no benchmark leakage
write receipts only
```

## Rejected/Unsafe Imports

Reject as runtime imports:

```text
REAPER full cognitive engine
Clearbox reasoning services
CortexOS context engine
CortexOS trust filter as authority
ARC solver engine
CompuCog binary log runtime
SwarmResonance runtime
TrueCore recovered agent runner
phone MTP recovered launchers
machine_log_reasoners bulk source tree
```

Reasons:

```text
sprawling architecture
unknown runtime assumptions
security/mutation risk
third-party or missing dependency risk
old terminology conflicts
would bypass TrueMem evidence mechanics
would blur sidecar and core boundaries
```

Safe reuse:

```text
read files as reference
extract shape
rewrite tiny TrueMem-native helpers
test against TrueMem packet/trace data
preserve docs and receipts
```

## Recommended Next Implementation

Implement:

```text
contradiction_pressure_score(trace_candidate)
```

Add it to:

```text
src/truemem/agents/pressure_coordination.py
tests/test_pressure_coordination_agent.py
system/reasoning/REAPER_PRESSURE_COORDINATION_NOTES.md
```

Rule:

```text
REAPER may promote partial -> supported only when bridge score is strong and contradiction pressure is low.
REAPER may not promote needs_bridge -> supported when contradiction pressure is medium or high.
```

Suggested thresholds:

```text
contradiction_pressure < 0.35: low
0.35 <= contradiction_pressure < 0.65: medium
contradiction_pressure >= 0.65: high
```

Acceptance tests:

```text
1. No contradiction: prior pressure coordination behavior remains unchanged.
2. Medium contradiction: supported promotion is capped at partially_supported.
3. High contradiction plus needs_bridge: decision stays needs_bridge.
4. Output trace includes contradiction_pressure_score and contradiction_cap.
```

## Tests Run

```text
python -m pytest -q
41 passed in 1.95s
```

No product behavior was changed during this R&D mining pass. The test run
verifies the current combined worktree still passes after adding this guide.

## Git Status

At original report verification:

```text
This guide is uncommitted.
Do not commit automatically.
python -m pytest -q passed.
```

Commit split applied afterward:

```text
TrueMem rename / compatibility committed separately.
Pressure coordination sidecar committed separately.
This guide belongs to the R&D reasoning docs commit only.
```
