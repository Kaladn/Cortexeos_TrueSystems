# TrueVision Intake

TrueVision Intake is the top-level DocuFilm document and glyph-state intake
authority. It reads admitted document state, assigns stable glyph-state records,
and constructs the parent/contained handoff consumed by TrueMem. TrueVision may
produce visual state, but it does not own this intake after separation.

The persisted output choice is exposed by TrueMem's `docufilm-intake` command,
because TrueMem owns dataset symbols, counts, relationships, and query storage.
Interactive intake asks before writing: `split` retains the current layout;
`native` additionally writes a verified all-in-one `.lxhcc` while retaining the
split runtime for compatibility. Headless intake requires
`--output-format split|native`. Native publication does not activate a native
query backend or change deterministic answers by itself.

DocuFilm classifies each admitted source with deterministic, declarative rules
before structural compilation. The profile records the matched rule, source
role, format, language, capabilities, and exact classification basis; it does
not infer meaning from file contents. CSV, JSONL, and JSON additionally receive
a sparse tabular-grid view. Columns grow in first-observed order to the widest
row, short rows stay sparse, and each observed cell retains its exact value,
deterministic anchor, and local observation weight. New type rules and parsers
can be added without changing preserved source bytes.

When chat metadata supplies a conversation ID and turn index, the native copy
includes typed `CHAT_TURN` nodes and `NEXT_TURN` edges. Multi-paragraph messages
remain one turn. Timestamp-only identity, ambiguous duplicate turns,
cross-conversation links, and inferred semantic links are prohibited.
