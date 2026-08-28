# AWEAR Rename Compatibility

Status: active migration contract.

Meaning:

```text
AWEAR = AnchorWorks Evidence Aware Retrieval
```

The name is operator-defined. "Aware" carries the system intent: the engine is
evidence-aware, dataset-aware, and operator-domain aware. It is not just RAG; it
maps, counts, tracks who/when/where, and retrieves through AnchorWorks evidence
structures.

Preferred operator surface:

```powershell
awear --help
awear-operator
python -m awear.cli --help
python -m awear.operator_shell --help
```

Compatibility surface:

```powershell
awrag --help
awrag-operator
python -m awrag.cli --help
python -m awrag.operator_shell --help
```

Compatibility rules:

```text
The internal awrag package path remains a migration alias.
Legacy awrag console scripts remain available.
Runtime schemas and historical receipt IDs are not rewritten.
Historical reports are not renamed.
New operator-facing docs and examples should say AWEAR/awear.
No evidence mechanics change because of the rename.
No speech behavior change because of the rename.
```
