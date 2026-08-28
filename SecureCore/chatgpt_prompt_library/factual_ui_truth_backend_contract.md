---
prompt_id: factual_ui_truth_backend_contract
title: UI Truth Backend Contract Audit
when_to_use: Use when checking whether UI labels, cards, buttons, panels, or displayed status truthfully reflect backend behavior.
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

Check whether UI surfaces truthfully reflect backend behavior.

Report only:

* UI label/text/action
* backend endpoint/command/function
* data returned by backend
* UI state derived from backend
* placeholder/mock/static text
* tests or screenshots if present
* mismatches marked as facts

Rules:

* Do not critique design.
* Do not recommend UX changes.
* A UI label is factual only if backend behavior supports it.
* Mark static/demo/mock behavior explicitly.

Required sections:

1. UI surface inventory
2. Backend contract for each surface
3. Route-to-backend evidence
4. Static/mock/demo behavior
5. Tests or visual verification
6. Mismatch facts
7. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
