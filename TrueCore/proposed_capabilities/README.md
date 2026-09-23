# Proposed capabilities — not executable registration

`catalog.json` is TrueCore's explicit placeholder ledger for the current
structural-completion plan, graph authorities, receipt/AV preservation work,
focused-dataset graph archival, and the supplied history-archaeology mission.

Every entry describes a **proposed delta or qualification task**. Existing
native functionality may already support part of it; a placeholder does not
erase that functionality or claim its integration is complete.

All entries have `callable: false`, `entrypoint: null`, and
`status: PROPOSED_NOT_IMPLEMENTED`. They are deliberately outside the executable
capability registry, agent manifests, generated skill index, and model-operation
contracts. Do not advertise them in executable help, dispatch them, create
success-shaped stub workers, or use their presence as evidence of authority.

The catalog preserves proposal-source hashes, source coordinates, dependencies,
existing support, missing work, and acceptance obligations. Source text is a
requirement/proposal, not a verified capability. Links into the previous audit
refer to that frozen audit; changes here make its source snapshot historical.

## Implementation boundary

New capability implementations belong **outside this repository**, in a
PluginRunner refactored and qualified for this current system. Existing source
repairs and explicit integration changes require their own admitted work and
external acceptance. The historical runner under
`research_reference_not_runtime/TruePlug/` remains read-only evidence and must
never become a live plugin-discovery root.

An entry becomes executable only after implementation exists, exact source and
input/output contracts are bound, dependencies and permissions are qualified,
positive/negative/recovery acceptance passes externally, and the real worker is
separately admitted into the existing TrueCore execution boundary. Do not flip
this catalog's flag to simulate that process. Preserve the proposal record and
link a separately qualified implementation/version when one exists.

The archaeology attachment is feasibility-first. It does not authorize reading
private chats, submitting prompts into old conversations, rewriting history,
parallel corpus processing, paid API use, or building its proposed system.
Original conversations remain immutable evidence; local findings and later
lineage reconciliation remain separate derived layers with uncertainty.

## Graph archive requirement

Read `GRAPH_ARCHIVE_POLICY.md`. Superseded graph snapshots for the dataset in
focus must have provenance-named, losslessly verified ZIP archives outside the
source repository. Packaging is not deletion authority or evidence of a
registered automatic archive worker. Keep active and reference-pinned graphs
available until their consumers have a separately qualified archive-aware
transition. Archival and historical analysis never enter the live AV/intake
critical path.
