# Three-Lane Cleanup Report

Date: 2026-06-26

## Law Locked

```text
Intake builds the field.
Retrieval pulls cited evidence packets.
Speech renders packets.
Thinking consumes packets off-path.
```

## Hot-Path Leak Found

`src/truemem/engine/qualification.py` performed pressure promotion inside the
retrieval/query path. A strong rejected-but-found candidate could clear reject
reasons and enter admitted `locations`.

Classification:

```text
HOT_PATH_LEAK
```

## Fix

Retrieval now keeps pressure information as diagnostics only:

```text
candidate_needs_pressure
scenario_gap
coverage_miss
bridge_required
pressure_inspection_needed
```

Retrieval no longer promotes, bridges, synthesizes, or validates deeper meaning.
Off-path thinking tools may consume the packet later.

## Preserved

```text
intake/status/system-metrics
query/batch retrieval
locations and rejected_locations packet shape
packet speech
pressure-probe sidecar
TopK diagnostic sidecar
pressure coordination sidecar
compatibility commands
```

## Proof Commands

```powershell
python -m pytest tests/test_qualification_pressure.py -q
python -m pytest tests/test_qualification_pressure.py tests/test_pressure_probe.py tests/test_topk_diagnostic.py tests/test_pressure_coordination_agent.py -q
python -m pytest -q
python -m truemem.cli status --runtime-root <runtime> --dataset <dataset>
python -m truemem.cli system-metrics --runtime-root <runtime> --dataset-id <dataset> --repo <repo>
python -m truemem.cli query --runtime-root <runtime> --dataset-id <dataset> --question "<dataset-local question>" --top-k 5
python -m truemem.cli packet-speech --packet <fresh-query-packet> --out <runtime-report-folder>\packet_speech
python -m truemem.cli batch --runtime-root <runtime> --dataset <dataset> --questions <questions.txt> --top-k 5 --workers 6 --no-progress
python -m truemem.cli pressure-probe --batch-summary <fresh-batch-summary> --out <runtime-report-folder>\pressure_probe --max-questions-per-packet 2
```

## Results

```text
targeted pressure tests: 3 passed
targeted sidecar tests: 14 passed
full suite: 57 passed
dataset status: INDEX_READY
query proof: support_state=qualified_evidence, pressure_promoted_count=0
packet speech: records_processed=1, retrieval_ran=false, intake_ran=false
batch proof: 2 completed / 0 failed, workers_effective=6
pressure probe proof: records_processed=2, retrieval_ran=false, topk_ran=false, intake_ran=false
```

## Remaining Risks

Held language-graph speech formulas remain documentation/pseudocode.

Reasoning tools remain sidecars. They are not one production orchestrator.
