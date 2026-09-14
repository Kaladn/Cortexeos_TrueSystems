# Wolf Engine — Build Tracking (LAW v1.0)

## Master Flowchart

```mermaid
graph TD
    subgraph "Phase 0 — Stabilize"
        P0-GIT["P0-GIT: Git Init"]:::normal
        P0-PKG["P0-PKG: pyproject.toml"]:::normal
        P0-CFG["P0-CFG: Config"]:::normal
        P0-LOG["P0-LOG: Logging"]:::normal
        P0-THR["P0-THR: Thread Safety"]:::normal
        P0-SQL["P0-SQL: SQLite Hardening"]:::normal
        P0-RLD["P0-RLD: Forge Reload"]:::normal
        P0-STR["P0-STR: Stress Tests"]:::normal
    end

    subgraph "Phase 1 — Network Layer"
        P1-SER["P1-SER: Serialization Protocol"]:::normal
        P1-FRG["P1-FRG: Forge Service (Node 1)"]:::normal
        P1-PER["P1-PER: Perception Service (Node 2)"]:::normal
        P1-GW["P1-GW: API Gateway (Node 3)"]:::normal
        P1-HLT["P1-HLT: Health + Discovery"]:::normal
        P1-INT["P1-INT: Integration Tests"]:::normal
    end

    subgraph "Phase 2 — GPU"
        P2-DEV["P2-DEV: GPU Device Detection (ROCm/CUDA)"]:::normal
        P2-WIN["P2-WIN: GPU Window Engine"]:::normal
        P2-FGP["P2-FGP: ForgeMemoryGPU"]:::normal
        P2-NCV["P2-NCV: NCV-73 Batch"]:::normal
        P2-TST["P2-TST: GPU Tests"]:::normal
    end

    subgraph "Phase 3 — Sessions"
        P3-SES["P3-SES: Session Manager"]:::normal
        P3-TST["P3-TST: Session Tests"]:::normal
    end

    subgraph "Phase 4 — Reasoning"
        P4-ENG["P4-ENG: 6-1-6 Engine"]:::normal
        P4-CAS["P4-CAS: Causal Analyzer"]:::normal
        P4-PAT["P4-PAT: Pattern Detector"]:::normal
        P4-CSC["P4-CSC: Cascade Engine"]:::normal
        P4-RSV["P4-RSV: Reasoning Service"]:::normal
        P4-TST["P4-TST: Reasoning Tests"]:::normal
    end

    subgraph "Phase 5 — Archon"
        P5-ORC["P5-ORC: Orchestrator"]:::normal
        P5-JDG["P5-JDG: Judge (3 modules)"]:::normal
        P5-VRD["P5-VRD: Verdict + Audit"]:::normal
        P5-CAM["P5-CAM: CAM Stub"]:::normal
        P5-TST["P5-TST: Archon Tests"]:::normal
    end

    subgraph "Phase 6 — Dashboard"
        P6-MET["P6-MET: Metrics Exporter"]:::normal
        P6-COL["P6-COL: Metrics Collector"]:::normal
        P6-WEB["P6-WEB: Web Dashboard"]:::normal
        P6-API["P6-API: Enhanced API"]:::normal
    end

    %% Phase 0 deps
    P0-GIT --> P0-PKG --> P0-STR
    P0-GIT --> P0-CFG --> P0-LOG --> P0-STR
    P0-GIT --> P0-THR --> P0-RLD --> P0-STR
    P0-GIT --> P0-SQL --> P0-STR

    %% Phase 0 → 1
    P0-STR --> P1-SER
    P0-CFG --> P1-SER

    %% Phase 1 deps
    P1-SER --> P1-FRG
    P1-SER --> P1-PER
    P1-SER --> P1-GW
    P1-FRG --> P1-HLT
    P1-PER --> P1-HLT
    P1-GW --> P1-HLT
    P1-HLT --> P1-INT

    %% Phase 1 → 2
    P1-FRG --> P2-DEV

    %% Phase 2 deps
    P2-DEV --> P2-WIN
    P2-DEV --> P2-FGP
    P2-WIN --> P2-NCV
    P2-NCV --> P2-TST
    P2-FGP --> P2-TST

    %% Phase 2 → 3
    P2-TST --> P3-TMB

    %% Phase 3 deps
    P3-TMB --> P3-SES --> P3-WRK --> P3-FUS --> P3-TST

    %% Phase 3 → 4
    P3-TST --> P4-ENG

    %% Phase 4 deps
    P4-ENG --> P4-CAS --> P4-PAT --> P4-CSC --> P4-RSV --> P4-TST

    %% Phase 4 → 5
    P4-TST --> P5-ORC

    %% Phase 5 deps
    P5-ORC --> P5-JDG --> P5-VRD --> P5-TST
    P5-ORC --> P5-CAM --> P5-TST

    %% Phase 5 → 6
    P5-TST --> P6-MET

    %% Phase 6 deps
    P6-MET --> P6-COL --> P6-WEB
    P6-COL --> P6-API

    classDef grey fill:#ccc,stroke:#999,color:#666
    classDef normal fill:#4CAF50,stroke:#388E3C,color:#fff
    classDef red fill:#F44336,stroke:#D32F2F,color:#fff
    classDef yellow fill:#FFC107,stroke:#FFA000,color:#333
```

---

## Test Matrix

| Phase | Test File | Tests | Status |
|-------|-----------|-------|--------|
| 0 | `tests/test_acceptance.py` | 6 acceptance | 6/6 PASS |
| 0 | `tests/test_stress.py` | 6 stress | 6/6 PASS |
| 1 | `tests/test_services.py` | 11 integration | 11/11 PASS |
| 2 | `tests/test_gpu.py` | 31 GPU (30 pass, 1 skip) | 31/31 PASS |
| 3 | `tests/test_evidence.py` | 26 evidence | 26/26 PASS |
| 4 | `tests/test_reasoning.py` | 30 reasoning | 30/30 PASS |
| 5 | `tests/test_archon.py` | 38 archon | 38/38 PASS |
| 6 | `tests/test_dashboard.py` | 42 dashboard (41 pass, 1 skip) | 42/42 PASS |

**Run all:** `python -m pytest tests/ -v`

---

## Build Log

| Commit | Hash | Tests | Nodes Completed |
|--------|------|-------|-----------------|
| Phase 0 baseline | `a3d4e34` | 6/6 | P0-GIT |
| Phase 0 complete | `97ae2f5` | 12/12 | P0-PKG, P0-CFG, P0-LOG, P0-THR, P0-SQL, P0-RLD, P0-STR |
| Tracking doc | `0eefa9c` | 12/12 | — |
| Phase 1 complete | `4682ccc` | 23/23 | P1-SER, P1-FRG, P1-PER, P1-GW, P1-HLT, P1-INT |
| Phase 2 complete | `e010b75` | 54/54 | P2-DEV, P2-WIN, P2-FGP, P2-NCV, P2-TST |
| Phase 3 complete | `e86568e` | 80/80 | P3-TMB, P3-SES, P3-WRK, P3-FUS, P3-TST |
| Phase 4 complete | `639b44d` | 110/110 | P4-ENG, P4-CAS, P4-PAT, P4-CSC, P4-RSV, P4-TST |
| Phase 5 complete | `7fff9b8` | 148/148 | P5-ORC, P5-JDG, P5-VRD, P5-CAM, P5-TST |
| Phase 6 complete | `16573a5` | 190/190 | P6-MET, P6-COL, P6-WEB, P6-API |

---

## Node Detail Index

### Phase 0 (COMPLETE)

| NodeID | Status | File(s) Modified | Exit Criteria Met |
|--------|--------|-----------------|-------------------|
| P0-GIT | NORMAL | `.gitignore` | git log shows baseline commit |
| P0-PKG | NORMAL | `pyproject.toml` | pytest picks up configfile |
| P0-CFG | NORMAL | `config.py`, `gnome/config.py` | env vars override defaults |
| P0-LOG | NORMAL | `logging_config.py` | JSON output with timestamp/level/module/message |
| P0-THR | NORMAL | `forge/forge_memory.py` | RLock on all methods, concurrent test passes |
| P0-SQL | NORMAL | `sql/sqlite_writer.py`, `sql/sqlite_reader.py` | check_same_thread, batch write, disk check |
| P0-RLD | NORMAL | `forge/forge_memory.py` | reload_from_events() works, Test 5 uses it |
| P0-STR | NORMAL | `tests/test_stress.py` | 6 stress tests all pass |

### Phase 1 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P1-SER | NORMAL | `services/protocol.py` | JSON encode/decode round-trips, contract serialization |
| P1-FRG | NORMAL | `services/forge_service.py` | ZMQ REP, ingest/query/stats/health all tested |
| P1-PER | NORMAL | `services/perception_service.py` | Tokenize + 6-1-6 context windows verified |
| P1-GW | NORMAL | `services/gateway.py` | Flask /think, /query, /stats, /health all tested |
| P1-HLT | NORMAL | `services/health.py`, `cluster_config.json` | Health monitor detects DOWN after miss_threshold |
| P1-INT | NORMAL | `tests/test_services.py` | 11/11 tests: protocol, perception, forge, gateway, health, degradation |

### Phase 2 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P2-DEV | NORMAL | `gpu/device.py` | GPU auto-detect (ROCm/CUDA), fail-hard (no CPU), DeviceInfo, to_tensor |
| P2-WIN | NORMAL | `gpu/window_engine.py` | GPU torch.unique co-occurrence, CPU fallback, parity verified |
| P2-FGP | NORMAL | `gpu/forge_memory_gpu.py` | GPU resonance tensor (ROCm/CUDA), batch_ingest scatter_add_, topk, sparse co-occurrence |
| P2-NCV | NORMAL | `gpu/ncv_batch.py` | 73-dim vector generation, CPU single + GPU batch, domain-agnostic |
| P2-TST | NORMAL | `tests/test_gpu.py` | 31 tests (8 device, 6 window, 10 forge-gpu, 8 ncv), GPU/CPU parity |

### Phase 3 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P3-SES | NORMAL | `evidence/session_manager.py` | Session directories, manifests, and list/stop lifecycle |
| P3-TST | NORMAL | `tests/test_evidence.py` | Session lifecycle tests |

### Phase 4 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P4-ENG | NORMAL | `reasoning/engine.py` | Two-pass 6-1-6 streaming, lifetime counts, windows, resonance |
| P4-CAS | NORMAL | `reasoning/causal_analyzer.py` | Bidirectional validation via ForgeMemory co-occurrence |
| P4-PAT | NORMAL | `reasoning/pattern_detector.py` | Pattern breaks (z-score), causal chains (run-length), anomalies |
| P4-CSC | NORMAL | `reasoning/cascade_engine.py` | BFS on co-occurrence graph, forward/backward, depth/node caps |
| P4-RSV | NORMAL | `reasoning/reasoning_service.py` | ZMQ REP :5002, analyze/detect/cascade/windows/health |
| P4-TST | NORMAL | `tests/test_reasoning.py` | 30 tests (7 engine, 4 causal, 5 pattern, 7 cascade, 7 service) |

### Phase 5 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P5-ORC | NORMAL | `archon/orchestrator.py` | End-to-end governed analysis, wires Engine → Judge → Audit |
| P5-JDG | NORMAL | `archon/judge.py` | 3 modules: Confidence Governance, Temporal Coherence, Citadel Isolation |
| P5-VRD | NORMAL | `archon/verdict.py`, `archon/schemas.py` | SQLite audit trail, NaN sanitization, query by session/status |
| P5-CAM | NORMAL | `archon/cam_stub.py` | Dormant interface, activates on register_engine(), multi-engine comparison ready |
| P5-TST | NORMAL | `tests/test_archon.py` | 38 tests (3 schema, 7 citadel, 4 confidence, 4 temporal, 5 judge, 4 verdict, 5 CAM, 6 orchestrator) |

### Phase 6 (COMPLETE)

| NodeID | Status | File(s) | Exit Criteria Met |
|--------|--------|---------|-------------------|
| P6-MET | NORMAL | `dashboard/metrics_exporter.py` | ZMQ PUB per node, CPU/RAM/GPU/Forge/Archon metrics, JSON-serializable snapshots |
| P6-COL | NORMAL | `dashboard/metrics_collector.py` | ZMQ SUB → SQLite, in-memory latest cache, time-series history, 7-day auto-prune |
| P6-WEB | NORMAL | `dashboard/web.py` | Dark-theme HTML (Flask + SSE + Chart.js CDN), 7 panels, real-time updates |
| P6-API | NORMAL | `dashboard/app.py` | Unified app: /dashboard, /api/metrics, /api/verdicts, /api/sessions, /api/stream SSE, /health |

---

## Hallucination Ledger

| ID | Category | Claim | Status |
|----|----------|-------|--------|
| H-1 | Ghost API | `ForgeMemory.reload_from_events()` | RESOLVED — built in Phase 0 |
| H-2 | Ghost File | `wolf_engine/config.py` | RESOLVED — built in Phase 0 |
| H-3 | Ghost File | `wolf_engine/logging_config.py` | RESOLVED — built in Phase 0 |
| H-4 | Ghost File | `wolf_engine/tests/test_stress.py` | RESOLVED — built in Phase 0 |
| H-5 | Ghost File | `pyproject.toml` | RESOLVED — built in Phase 0 |
| H-6 | Unproven | "~100 writes/sec single-insert SQLite" | UNKNOWN — not benchmarked |
| H-7 | Unproven | "RLock overhead ~2-5%" | UNKNOWN — not measured on Py3.14 |
| H-8 | Hidden Dep | `shutil.disk_usage()` on OneDrive paths | UNKNOWN — works on local, untested on network |

---

## Environment

- **Python:** 3.14.3
- **pytest:** 9.0.2
- **OS:** Windows 11 Pro
- **Shell:** bash (Unix syntax)
- **torch:** >=2.4.0+rocm7.1 (ROCm 7.1, AMD RX 7900 XT 20GB VRAM)
- **Git:** Local only (no remote)
