# LocalMemoryChat checkpoint — native chat intake before 6-1-6 work

**Date:** 2026-09-19
**Checkpoint status:** native adapter gate passed; graph projection is next
**Bulk historical admission:** not started

## Exact current truth

LocalMemoryChat can immutably admit exactly selected native chats from Codex,
an official OpenAI export ZIP, and LM Studio. The admitted structure is:

```text
source occurrence
-> logical historical source
-> conversation
-> turn
-> message / message variant / tool call / tool result
-> paragraph block
-> exact word occurrences
-> raw artifacts
```

The adapter acceptance used one real chat per source family and proved source
hash preservation, parentage, order, tool identities, Codex attachment binding,
OpenAI ZIP media binding, LM Studio artifacts, exact-surface occurrences,
duplicate logical-source collapse, no automatic HOT admission, and historical
immutability.

The chats are not a full graph. The current implementation persists measured
signed ±6 relationship rows during admission. The accepted next correction is
to make exact ordered occurrences the durable flat chat authority and create
relation fields and graphs only for explicitly selected scopes.

## Immutable laws

1. Native source bytes remain authoritative and immutable.
2. Import time never replaces event time and never grants HOT status.
3. Physical duplicate locations collapse to one logical chat while every
   custody occurrence remains recorded.
4. Chat word surfaces remain exact observations. They are not hash symbols.
5. Dataset, chat, turn, message, block, sentence, tool, and artifact identities
   are structural identities.
6. Tool calls, tool results, files, images, video, audio, graphs, and other
   artifacts remain first-class children rather than flattened prose.
7. A temporary graph never replaces its source locations.
8. No positional relationship crosses a sentence boundary.
9. No dataset/training pair representation is introduced.
10. No decay/re-cay work is authorized by this checkpoint.

## Known current-code limitations

1. `relational_v2.py` still calculates and stores signed ±6 rows during native
   admission. That is checkpointed behavior, not the final chat law.
2. Paragraph blocks exist, but stable sentence objects and sentence-local word
   ordinals do not yet exist.
3. `retrieve_v2()` scans stored message/block text and consults persisted
   relation rows; it is not yet the flat-location-first search path.
4. Query/retrieval provenance sidecars are not persisted in the relational
   database.
5. Exact-offset top-K fields, temporary 6-1-6 maps, full scoped relation maps,
   and graph walking are not implemented.
6. The gateway exists, but it must be requalified after the flat occurrence and
   scoped graph changes.
7. Loose TXT/Markdown transcripts are not admitted by the three native adapters.
8. Current-day writable-chat rollover and prior-day sealing are not complete.
9. The full chat estate has not been dry-run or admitted.

## Next work — required order

### 1. Finish the durable flat chat representation

- Add stable sentence objects beneath paragraph blocks.
- Assign every exact word occurrence a sentence-local and block-local ordinal.
- Preserve character and byte coordinates.
- Preserve timestamp, role, source, conversation, turn, message, block, and
  sentence ownership.
- Stop generating durable signed relationship rows during ordinary chat
  admission.
- Preserve flat exact-surface counts and occurrence addresses.
- Update acceptance so a native import leaves no pre-expanded graph state.

### 2. Add scoped relation projection

Input must be immutable locations such as:

```text
dataset/source
conversation/document
block 34, sentences 3-6
block 45, sentence 3
```

The projector must:

1. resolve only the admitted IDs;
2. load exact ordered sentence occurrences;
3. calculate only the requested relationship field;
4. aggregate observed counts without crossing sentence boundaries;
5. return source-owned top-K fields and graph edges;
6. record the exact input scope and source hashes;
7. discard the expanded working map after the operation.

Required projection modes:

- one signed offset, such as `+3`;
- complete temporary 6-1-6;
- sentence co-occurrence;
- full expansion inside an explicitly selected sentence set;
- continuation from selected top-K neighbors into additional admitted
  locations.

### 3. Exercise 6-1-6

Use deliberate deterministic questions rather than model prose:

- For `AnchorWorks` at `+3`, return every observed surface and count, then top-K.
- Compare `+3` with `-3` to prove direction.
- Combine selected sentences from two blocks and prove that counts combine while
  position does not cross boundaries.
- Walk from one top-K neighbor into its own signed fields.
- Run full scoped expansion and compare it with the limited ±6 view.
- Prove that repeating a projection produces byte-identical measured output.
- Prove that discarding a projection leaves the flat admitted chat unchanged.

### 4. Correct flat search and explicit admission

- Search lexicon and occurrence locations first.
- Return dataset/chat/block/sentence addresses before evidence text.
- Resolve only selected immutable IDs into bounded evidence.
- Keep historical evidence outside HOT until explicitly admitted.
- Exclude unrelated historical material from the model packet.

### 5. Persist compact provenance

- Record query surface and timestamp.
- Record searched scope.
- Record returned immutable addresses and source hashes.
- Record explicitly admitted evidence IDs.
- Record projection mode and parameters when relational work is requested.
- Keep bounded success/failure counts and last-use timestamps for useful lookup
  anchors without building histories for stop words.

### 6. Requalify the gateway and Qwen

- Use the existing OpenAI-compatible gateway only.
- Verify the configured LM Studio endpoint and Qwen model identity.
- Enforce GPU-only execution with no CPU fallback.
- Send one current-day question requiring one admitted historical fact.
- Capture exact evidence, packet, request result, response, citation, timing,
  token counts, and provenance sidecar.
- Prove unrelated history is absent and the historical source is unchanged.

### 7. Measure before full historical bootstrap

- Add a no-write estate manifest.
- Benchmark smallest, median, large, and maximum chats.
- Record parse time, sentence/occurrence counts, temporary projection time,
  peak memory, WAL growth, and database bytes.
- Estimate total bootstrap time and storage from observed source-family values.
- Do not bulk-admit until the estimate and a small multi-chat batch pass.

### 8. Complete source coverage

- Add chat-aware TXT/Markdown transcript classification and reconstruction.
- Quarantine ambiguous text instead of inventing speakers or turns.
- Exclude native-export derivatives and training/dataset rows.
- Add current-day incremental admission and calendar-day sealing.

### 9. Deliver and synchronize

- Run the final integrated acceptance suite.
- Produce the exact laptop update package from the passing Git state.
- Verify hashes and versions on both machines.
- Preserve the external acceptance logs and manifests.

## Checkpoint acceptance evidence

External test:

`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/tests/test_localmemorychat_native_adapters.py`

Final passing output:

`/home/lamercey/Documents/User System Test/repositories/TrueSystems-Alignment/output/localmemorychat-native-adapters-20260919T204214Z/acceptance.log`

Results at checkpoint:

- native adapter acceptance: 25 checks passed;
- existing LocalMemoryChat regression: 13 passed;
- CLI import/help smoke: passed;
- Git whitespace check: passed.
