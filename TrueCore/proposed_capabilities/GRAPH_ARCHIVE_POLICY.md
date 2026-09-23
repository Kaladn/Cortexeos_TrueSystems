# Focused-dataset graph archive policy

Owner instruction, 2026-09-14: from now on, previous graphs of the dataset in
focus must be compressed into ZIP files with provenance-bearing names.

## Scope and identity

- Select the explicitly focused dataset by its canonical identity. Do not use
  folder recency, a similar title, or a reused dataset alias as identity.
- Preserve each earlier graph snapshot and its original manifest. Archive full
  and scoped graphs distinctly; a scoped graph is never renamed as a full map.
- Record why a snapshot is historical/superseded and its successor when known.
  A later modification makes an older source snapshot historical, but does not
  prove that a replacement graph has already been built.
- Do not include unrelated datasets, disposable test graphs, credentials,
  source conversations, or canonical media just because they share a parent
  directory. A graph package contains its declared graph artifacts.

## Archive naming

Use a filesystem-safe form:

```text
<dataset-alias>__<scope>__snapshot-<snapshot-sha256>__commit-<commit-prefix-or-unknown>__manifest-<manifest-hash-prefix>__archived-<YYYYMMDDTHHMMSSZ>.zip
```

Names are readable provenance labels, not substitutes for full identity. Include
an `ARCHIVE_PROVENANCE.json` member with:

- schema/version and canonical dataset identity;
- original snapshot identity, full source commit when recorded, and scope;
- original manifest hash and original graph directory;
- graph observation time when recorded in the original manifest;
- archive creation time in UTC and producing tool/operator identity;
- each archived member's relative name, byte size, and SHA-256;
- native manifest unchanged, plus its artifact identities;
- supersession reason and successor snapshot when independently recorded;
- compression method and lossless verification scope;
- original-directory retention/removal status and reference obligations.

Unknown commit, observation time, or successor must remain unknown. Never fill
them with today's commit/time or assume timestamps prove chronological order.
For existing manifests without observation/successor fields, their absence is
`NOT_RECORDED`; archive time is never substituted for either. Packaging a prior
snapshot alone does not assert that a replacement graph exists.

## Publication and verification

1. Freeze the focused dataset/snapshot set and member identities before work.
2. Confirm the snapshots are not being modified. Reject symlinks and unexpected
   members rather than following them outside the graph root.
3. Validate member hashes against the historical native manifest; do not
   incorrectly require old graphs to match today's changed source code.
4. Write a uniquely named pending ZIP outside the repository, never overwrite a
   prior archive, then read every archived member and verify its exact SHA-256
   and size. CRC alone is insufficient for the identity check.
5. Recheck original member identities and set membership before publishing the
   archive atomically. Failed or interrupted pending output is not a valid
   archive. Never delete originals on failure.
6. Return one bounded archival-job result with archive hashes, counts, sizes,
   verification status, retained originals, and actual reclaimed bytes. Keep
   per-member provenance inside the ZIP; do not scatter one receipt per file.

## Retention and operation

ZIP compression does not authorize removal of canonical evidence or break
existing path-bound receipts. Only an explicitly admitted retention operation
may remove an inactive unpinned original after verified archive publication and
qualified consumer/reference migration. Do not claim disk space was reclaimed
when both copies remain. Active graphs stay available for their consumers.

Archive completed snapshots at job/change boundaries. Do not compress, scan all
history, or rebuild full graphs per query, frame, audio sample, or intake item.
Do not let an archival/publication failure recast a successful native AV or
intake operation as an execution failure. Report operation and publication
outcomes separately.

This is an operator working requirement plus proposed automation. It does not
claim an automatic TrueCore archive worker, archive-aware map reader, scheduler,
or retention migration exists. Their placeholders live in `catalog.json`; new
implementations belong in the external refactored PluginRunner.
