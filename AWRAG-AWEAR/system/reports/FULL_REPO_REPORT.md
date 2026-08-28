# Full Repo Report

Date: 2026-06-25

## Current Objective

Rename operator-facing product language from AWRAG to AWEAR, keep compatibility
aliases, preserve evidence mechanics and speech, and mine the R&D reasoning
toolbox for AWEAR-native implementation guidance.

## Active Work Completed

```text
1. AWEAR rename pass
2. Compatibility alias package: src/awear
3. Preferred awear CLI/operator command paths
4. Legacy awrag command/module compatibility retained
5. Pressure coordination sidecar module present
6. R&D reasoning toolbox implementation guide added
```

## Important Reports

```text
system/reports/AWEAR_RENAME_REPORT.md
system/contracts/AWEAR_RENAME_COMPATIBILITY.md
system/reasoning/RD_REASONING_TOOLBOX_IMPLEMENTATION_GUIDE.md
```

## Architecture Boundaries

Preserved:

```text
No runtime data changed.
No raw dataset changed.
No historical reports rewritten.
No speech capability removed.
No evidence mechanics changed for the rename.
No old R&D runtime imported into product code.
No benchmark-specific logic promoted into core.
```

Compatibility:

```text
Preferred: awear, awear-operator, python -m awear.cli
Legacy: awrag, awrag-operator, python -m awrag.cli
Internal package path remains src/awrag for migration stability.
```

## Product Files Reviewed During Split

```text
pyproject.toml
src/awear/__init__.py
src/awear/cli.py
src/awear/operator_shell.py
src/awrag/cli.py
src/awrag/agents/__init__.py
src/awrag/agents/pressure_coordination.py
src/awrag/operator_contract.py
src/awrag/operator_live.py
src/awrag/operator_shell.py
src/awrag/ui_server.py
src/awrag/adapters/__init__.py
src/awrag/engine/*.py files with operator-facing AWEAR naming updates
```

## Script/Launcher Files Reviewed During Split

```text
Install_To_Local.ps1
Launch_AWEAR_CLI.cmd
Launch_AWRAG_CLI.cmd
Run_From_USB.ps1
Start_AWEAR_CLI.ps1
Start_AWRAG_CLI.ps1
Start_Laptop_Temp_Intake.ps1
```

## Test Files Reviewed During Split

```text
tests/test_awear_aliases.py
tests/test_operator_live.py
tests/test_pressure_coordination_agent.py
```

## Documentation Files Reviewed During Split

```text
README.md
system/contracts/AWEAR_RENAME_COMPATIBILITY.md
system/reasoning/PRE_REASONING_BASELINE.md
system/reasoning/README.md
system/reasoning/PRESSURE_COORDINATION_AGENT.md
system/reasoning/REAPER_PRESSURE_COORDINATION_NOTES.md
system/reasoning/RD_REASONING_TOOLBOX_IMPLEMENTATION_GUIDE.md
system/reports/AWEAR_RENAME_REPORT.md
system/reports/FULL_REPO_REPORT.md
system/roadmaps/EVIDENCE_CLOUD_BOIL_DOWN.md
```

## R&D Material State

```text
research_development/reasoning_toolbox remains reference-only.
It is ignored/local research material unless promoted through normal docs/tests/code.
No old engine was executed as product runtime in this pass.
No old engine was imported into src.
```

## Verification Already Completed Before This Report

```text
python -m awear.cli --help: pass
python -m awrag.cli --help: pass
python -m awear.operator_shell --help: pass
PYTHONPATH=I:\AWRAG_System_Only\src python -m pytest -q: 41 passed
python -m pytest -q: 41 passed
```

## Verification After This Report

```text
python -m pytest -q
41 passed in 1.95s
```

The original report was written before the split commits were created. After
review, rename/compatibility and pressure sidecar work were committed separately.
This report belongs to the R&D reasoning documentation bucket.

## Recommended Next Session

```text
1. Review RD_REASONING_TOOLBOX_IMPLEMENTATION_GUIDE.md.
2. If approved, implement only contradiction_pressure_score(trace_candidate).
3. Add one cap rule and one test.
4. Re-run 5-question pressure coordination sample.
5. Review before promoting any sidecar behavior into base code.
```

## Commit Guidance

The original worktree contained multiple logical changes:

```text
AWEAR rename and compatibility
pressure coordination sidecar
R&D reasoning guide and repo reports
```

Commit split:

```text
1. Rename AWRAG operator surface to AWEAR with compatibility aliases - committed
2. Add pressure coordination sidecar cap - committed
3. Add R&D reasoning toolbox implementation guide - this docs bucket
```
