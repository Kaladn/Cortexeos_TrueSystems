---
prompt_id: factual_implementation_acceptance
title: Implementation Acceptance Audit
when_to_use: Use when deciding whether implementation satisfies a plan, ticket, acceptance contract, or claimed completion.
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

Decide whether an implementation satisfies a stated plan, ticket, or acceptance contract.

Report only:

* acceptance item
* evidence found
* evidence level
* pass/fail/unknown
* verification command output
* unverified claims

Rules:

* Do not accept claims without receipts.
* Do not treat passing tests as proof of untested acceptance items.
* Mark any item not directly verified as `UNKNOWN_FROM_WORKSPACE`.

Required sections:

1. Acceptance checklist
2. Code evidence
3. Test evidence
4. Command evidence
5. Missing evidence
6. Final acceptance status
7. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
