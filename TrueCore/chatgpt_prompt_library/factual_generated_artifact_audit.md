---
prompt_id: factual_generated_artifact_audit
title: Generated Artifact Audit
when_to_use: Use when the operator asks for an inventory of generated files, reports, caches, build outputs, sidecars, or derived artifacts.
---

Shared rules:

```text
Facts only.
Inspect only the provided workspace/repository.
Cite file and line numbers for important claims.
Do not assume behavior from names alone.
Classify implemented vs implied.
Separate active runtime code from tests, experiments, demos, and dormant code.
Report unknowns explicitly.
Do not suggest changes unless the prompt asks for recommendations.
```

Task:

Inventory generated files, reports, caches, build outputs, experiment outputs, sidecars, and derived data.

Report only:

* producer command/function
* output path
* committed vs ignored vs temporary
* deterministic vs timestamped/random/hash-derived/unknown
* rebuild command
* cleanup command
* source inputs
* authority/data lane

Rules:

* Do not recommend cleanup.
* Do not assume an artifact can be regenerated unless code/docs prove it.
* Mark external or missing outputs explicitly.

Required sections:

1. Generated artifact inventory
2. Producers
3. Inputs
4. Output paths
5. Git tracking/ignore status
6. Rebuild commands
7. Cleanup behavior
8. Determinism evidence
9. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
