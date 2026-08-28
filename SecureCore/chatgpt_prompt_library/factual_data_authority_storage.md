---
prompt_id: factual_data_authority_storage
title: Data Authority Storage Lane Audit
when_to_use: Use when the operator asks which stores, lanes, files, schemas, readers, writers, promotion gates, or authority paths exist.
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

Generic lane tags:

```text
source_data
application_state
user_data
configuration
cache
index
database
log
report
artifact
model_or_ml_data
test_fixture
debug_export
credential
temporary_file
unknown
```

Task:

Identify every data store or authority lane used by this workspace and what reads/writes it.

Report only:

* lane name
* files/directories/schemas/tables
* readers
* writers
* mutators
* deletion paths
* precedence rules
* promotion/approval gates if present
* debug/export paths

Rules:

* Every write must have a lane.
* Every authority claim must say whether it is direct code, direct test, direct doc, direct config, or inferred.
* Do not merge debug/export lanes with authority lanes.

Required sections:

1. Data lane inventory
2. Authority stores
3. Derived/debug/export stores
4. Readers by lane
5. Writers by lane
6. Promotion/mutation gates
7. Precedence rules
8. Untested lane behavior
9. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
