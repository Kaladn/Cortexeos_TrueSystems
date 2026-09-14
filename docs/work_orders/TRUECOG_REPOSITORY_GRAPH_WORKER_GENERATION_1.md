# TrueCog repository graph workers — generation 1

This generation implements the first fifteen investigations from the preserved
work order without promoting missing graph authority.

The TrueMachine view engine is
`TrueMachine/src/truemachine/repository_views.py`. TrueCore worker callables are
in `TrueCore/truecore/agents/repository_graph_workers.py`. Their manifests are
generated through `truecore.live_agents.creator`, registered in the normal
catalog, exposed through code-derived help, and published in the system skill
index.

## Static candidate or witnessed locators

- `repo_external_entrypoints`
- `repo_filesystem_writers`
- `repo_process_execution`
- `repo_direct_truemem_references`
- `repo_agent_registration`
- `repo_detached_subgraphs`
- `repo_no_incoming_dependencies`
- `repo_duplicate_implementations`

These operations return exact matching source/map records and the explicit
classifier rule. Except for the existence of exact call/import surfaces and
exact duplicate hashes, the findings remain investigation candidates.

## Explicit missing-authority workers

- `repo_truecore_bypass`
- `repo_security_config_writers`
- `repo_canonical_evidence_writers`
- `repo_untested_privileged_sinks`
- `repo_unresolved_privileged_reachability`
- `repo_documentation_without_code`
- `repo_code_without_documentation`

These are callable workers, but their correct current result is
`NOT_IMPLEMENTED`. Each names the absent registry or relationship channel.
They will retain the same identity and outer result contract as those graph
channels are qualified later.

## Governing limits

- All views are bounded by a caller-selected result limit.
- Every request names explicit source `scopes`. The host binds `allowed_scopes`
  per map resource; unknown, omitted, duplicate, and ungranted scopes fail closed.
- Scope selection and deterministic ordering precede the limit. Results retain
  unfiltered `total_matches`, in-scope `filtered_matches`, `returned`, and
  in-scope `truncated`. Duplicate groups are requalified after member filtering.
- Every view returns `answer: null` from TrueMachine.
- Every TrueCore worker returns `truecore.worker_result@1` with no claims.
- Static surface classification is not control flow, data flow, reachability,
  authorization, vulnerability, dead-code proof, or deletion authority.
- Positional proximity never promotes ownership.
- Exact duplicate source hashes prove identical spans, not duplicate purpose.
- Same names prove only a same-name candidate group.
- No worker mutates the repository or map.
