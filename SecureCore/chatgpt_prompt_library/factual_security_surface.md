---
prompt_id: factual_security_surface
title: Security Surface Inventory
when_to_use: Use when the operator asks for a facts-only inventory of security-relevant code surfaces, trust boundaries, secrets, auth, logging, or mutation authority.
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

Produce a facts-only inventory of security-relevant surfaces in this workspace.

Report only:

* path handling
* file writes/deletes/overwrites
* secrets/credentials/API keys
* network ingress/egress
* process/shell execution
* serialization/deserialization
* input trust boundaries
* logging/audit traces
* concurrency/locking
* permissions/authorization/authentication

Rules:

* Do not recommend fixes.
* Do not call something secure/insecure unless the code/docs directly state it.
* If none are found, use exact `NO_*_FOUND` markers.

Required sections:

1. Workspace boundary / path safety
2. Write/delete/mutation authority
3. Destructive command inventory
4. Secrets and sensitive data
5. Network/external egress
6. Process/shell/tool execution
7. Serialization/deserialization
8. Input trust boundaries
9. Logging/audit/trace behavior
10. Concurrency/locking/atomicity
11. Authentication/authorization/permissions
12. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
