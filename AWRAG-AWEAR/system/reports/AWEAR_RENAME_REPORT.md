# AWEAR Rename Report

Date: 2026-06-25

## Summary

Renamed operator-facing product language from AWRAG to AWEAR.

Meaning:

```text
AWEAR = AnchorWorks Evidence Aware Retrieval
```

This meaning was supplied by the operator. "Aware" means the system is
evidence-aware, dataset-aware, and operator-domain aware. It is not just RAG;
it maps, counts, tracks who/when/where, and retrieves through AnchorWorks
evidence structures.

## Compatibility

Preferred commands:

```powershell
awear --help
awear-operator
python -m awear.cli --help
python -m awear.operator_shell --help
```

Migration aliases preserved:

```powershell
awrag --help
awrag-operator
python -m awrag.cli --help
python -m awrag.operator_shell --help
```

The internal `awrag` package path remains in place for compatibility. The new
`awear` package forwards to the existing implementation. Runtime schemas,
historical reports, and prior receipts were not rewritten.

## Files Changed

Product/package surface:

```text
pyproject.toml
src/awear/__init__.py
src/awear/cli.py
src/awear/operator_shell.py
```

Operator launchers and install/demo scripts:

```text
Install_To_Local.ps1
Launch_AWEAR_CLI.cmd
Launch_AWRAG_CLI.cmd
Run_From_USB.ps1
Start_AWEAR_CLI.ps1
Start_AWRAG_CLI.ps1
Start_Laptop_Temp_Intake.ps1
```

Active product code and operator text:

```text
src/awrag/adapters/__init__.py
src/awrag/cli.py
src/awrag/engine/base.py
src/awrag/engine/codex.py
src/awrag/engine/count_walk_speech.py
src/awrag/engine/crosslinks.py
src/awrag/engine/dataset_overview.py
src/awrag/engine/evidence_cloud_speech.py
src/awrag/engine/forensic.py
src/awrag/engine/packet_speech.py
src/awrag/engine/pipeline.py
src/awrag/engine/pressure_probe.py
src/awrag/engine/querying.py
src/awrag/engine/resonance_adapter.py
src/awrag/engine/special_search.py
src/awrag/nlp_resolver.py
src/awrag/operator_contract.py
src/awrag/operator_live.py
src/awrag/operator_shell.py
src/awrag/ui_server.py
```

Docs/tests:

```text
README.md
system/contracts/AWEAR_RENAME_COMPATIBILITY.md
system/reasoning/PRE_REASONING_BASELINE.md
system/reasoning/README.md
system/roadmaps/EVIDENCE_CLOUD_BOIL_DOWN.md
tests/test_awear_aliases.py
tests/test_operator_live.py
```

## Verification

Search:

```text
Active uppercase old-name search, excluding system reports: no AWRAG / AW-RAG / A-RAG hits.
This report intentionally names the prior product string and legacy launcher filenames.
Lowercase awrag remains only for compatibility imports, aliases, tests, and migration notes.
```

Commands:

```text
python -m awear.cli --help: pass
python -m awrag.cli --help: pass
python -m awear.operator_shell --help: pass
```

Tests:

```text
PYTHONPATH=I:\AWRAG_System_Only\src python -m pytest -q: 41 passed
python -m pytest -q: 41 passed
```

## Boundaries

```text
No runtime data changed.
No historical reports rewritten.
No speech capability removed.
No evidence mechanics changed for the rename.
No hard package-directory cutover yet.
Compatibility aliases remain intentionally active.
```
