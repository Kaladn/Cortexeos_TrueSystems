---
prompt_id: factual_startup_boot_readiness
title: Startup Boot Readiness Audit
when_to_use: Use when tracing startup commands, app boot, config loading, health checks, service binding, readiness, or failure behavior.
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

Trace how the application starts and how readiness is determined.

Report only:

* startup commands
* startup files/functions
* config loading
* required directories/files
* service binding/listening
* health/readiness checks
* warmup behavior
* failure behavior
* tests

Rules:

* Do not propose new startup behavior.
* Do not assume readiness unless code/docs prove it.
* Distinguish server started from system ready.

Required sections:

1. Startup commands
2. Startup entrypoints
3. Config loading
4. Required filesystem/data dependencies
5. Service/network binding
6. Health/readiness checks
7. Warmup behavior
8. Failure/error behavior
9. Tests
10. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
