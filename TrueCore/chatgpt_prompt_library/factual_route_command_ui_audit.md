---
prompt_id: factual_route_command_ui_audit
title: Route Command UI-To-Behavior Audit
when_to_use: Use when the operator asks whether a public route, CLI command, UI action, handler, card, or exported operation reaches real backend behavior.
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

For every public route, CLI command, UI action, public handler, or exported operation, prove whether it reaches real backend behavior.

Report only:

* public entrypoint exists
* input shape
* output shape
* backend call chain
* backend write/return behavior
* tests proving behavior
* gaps marked as unknown or implied-only

Rules:

* Do not count something as implemented only because a route/function/name exists.
* Distinguish UI/route shell from backend behavior.
* Mark unreachable or uncalled handlers as `DEFINED_NO_CALLER_FOUND`.

Required sections:

1. Public route/command/action inventory
2. Handler evidence
3. Backend call-chain evidence
4. Artifact/write/return evidence
5. Tests proving behavior
6. Runtime status classification
7. Missing or implied-only behavior
8. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
