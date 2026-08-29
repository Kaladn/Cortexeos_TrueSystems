---
prompt_id: factual_dependency_external_service
title: Dependency And External Service Audit
when_to_use: Use when inventorying dependencies, imports, runtime services, external network calls, credentials, versions, or fallback behavior.
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

Inventory dependencies and external services used by the workspace.

Report only:

* package/dependency name
* where declared
* where imported/called
* runtime vs dev/test usage
* external network/service usage
* credentials/config required
* version constraints
* known optional/fallback behavior

Rules:

* Do not recommend dependency changes.
* Do not assume a dependency is used just because it is declared.
* Separate declared dependencies from actually imported/called dependencies.

Required sections:

1. Declared dependencies
2. Imported/called dependencies
3. Runtime dependency paths
4. Dev/test-only dependency paths
5. External services and network calls
6. Credential/config requirements
7. Optional/fallback behavior
8. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
