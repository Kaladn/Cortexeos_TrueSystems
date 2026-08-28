---
prompt_id: factual_repo_map
title: Repository Factual Map
when_to_use: Use when the operator asks for a facts-only map of a repository, workspace, modules, entrypoints, implemented behavior, or unknowns.
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

Evidence levels:

```text
DIRECT_CODE
DIRECT_TEST
DIRECT_DOC
DIRECT_CONFIG
INFERRED_FROM_CALL_CHAIN
UNKNOWN_FROM_WORKSPACE
```

Runtime status labels:

```text
ACTIVE_RUNTIME_PATH
TEST_ONLY
EXPERIMENT_ONLY
DOCS_ONLY
CONFIG_ONLY
DEFINED_NO_CALLER_FOUND
UNKNOWN_FROM_WORKSPACE
```

Required evidence block for every important claim:

```text
file:
line/range:
evidence:
evidence_level:
runtime_status:
```

Task:

Produce a factual map of this repository/workspace only.

Report only:

* repository/workspace root
* major folders/modules/packages
* runtime entrypoints
* CLI entrypoints
* API/server entrypoints
* UI entrypoints if present
* test entrypoints
* experiment/demo entrypoints
* docs/contracts/specs
* implemented behavior
* implied-only behavior
* not implemented behavior
* references to files/systems outside the workspace
* unknowns

Rules:

* Do not suggest improvements.
* Do not evaluate quality.
* Do not infer future architecture.
* Every major claim needs file/line evidence.

Required sections:

1. Workspace root and boundaries
2. Module/package inventory
3. Entrypoint inventory
4. Runtime status inventory
5. Implemented behavior
6. Implied-only behavior
7. Not implemented behavior
8. Tests and verification commands found
9. External references and dependencies
10. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
