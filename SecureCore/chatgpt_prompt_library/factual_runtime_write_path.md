---
prompt_id: factual_runtime_write_path
title: Runtime Write-Path Audit
when_to_use: Use when the operator asks to trace runtime writes, appends, overwrites, deletes, moves, truncates, path construction, or write authority.
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

Trace all runtime write, overwrite, delete, move, rename, truncate, and append paths.

Report only:

* writer function
* caller chain
* path construction
* authority/data lane
* write mode
* atomicity
* target constraints
* tests

Rules:

* Include direct file writes and helper-mediated writes.
* Include APIs such as:
  * `open(..., "w")`
  * `open(..., "a")`
  * `write_text`
  * `write_bytes`
  * `Path.unlink`
  * `os.remove`
  * `os.replace`
  * `rename`
  * `shutil.move`
  * `shutil.rmtree`
  * database writes
  * object store writes
  * subprocesses that write files
* Separate production runtime writes from tests and experiments.

Required sections:

1. Runtime write inventory
2. Experiment/test write inventory
3. Delete/truncate inventory
4. Atomic replace/temp-file behavior
5. Path boundary checks
6. Authority/data lanes
7. Tests proving constraints
8. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
