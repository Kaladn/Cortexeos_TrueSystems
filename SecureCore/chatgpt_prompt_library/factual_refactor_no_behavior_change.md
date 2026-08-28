---
prompt_id: factual_refactor_no_behavior_change
title: Refactor No-Behavior-Change Audit
when_to_use: Use when preparing or reviewing a refactor that must preserve existing behavior exactly.
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

Prepare or review a refactor while preserving behavior exactly.

Report only:

* current behavior receipts
* public interfaces that must remain stable
* tests that currently prove behavior
* files that may be touched
* files that must not be touched
* verification commands
* behavior changes detected after refactor

Rules:

* Do not introduce new features.
* Do not change public output shapes unless explicitly requested.
* If behavior changes, list the exact changed behavior with evidence.

Required sections:

1. Current behavior receipts
2. Stable interfaces
3. Allowed edit scope
4. Forbidden edit scope
5. Verification commands
6. Post-refactor behavior comparison
7. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
