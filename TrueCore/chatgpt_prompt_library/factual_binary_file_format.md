---
prompt_id: factual_binary_file_format
title: Binary File Format Contract Audit
when_to_use: Use when auditing binary formats, custom formats, manifests, sidecars, caches, readers, writers, or corruption behavior.
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

Audit binary formats, custom file formats, sidecars, manifests, indexes, caches, readers, and writers.

Report only:

* file format names
* magic/version/header fields
* row/record sizes
* metadata shape
* checksums/CRC/integrity checks
* readers/writers
* corrupt-data behavior
* tests
* debug/export parity paths

Rules:

* Do not infer binary safety from file extension names.
* Every format claim needs reader/writer evidence.
* Distinguish binary/cache artifacts from source-of-truth data.

Required sections:

1. File/binary format inventory
2. Writer paths
3. Reader paths
4. Header/version/integrity checks
5. Sidecar/manifest relationships
6. Debug/export relationships
7. Corruption/error behavior
8. Tests
9. Open factual questions

Final line:

```text
END OF FACTUAL REPORT
```
