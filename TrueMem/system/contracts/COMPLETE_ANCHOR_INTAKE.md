# Complete anchor intake contract

TrueMem admits complete words as anchors through the DocuFilm intake authority. A word joined internally by a
hyphen, dash, or apostrophe is one anchor. Intake does not delete common or
grammatical words.

Uppercase and lowercase forms have distinct identities. TrueMem performs zero
normalization: hyphen and dash variants, Unicode forms, spelling, and case remain
exactly as admitted before dataset-native symbol assignment. Apostrophes inside a word remain inside that one anchor. SHA hashes
and non-word entries are objects. No whitespace character receives a symbol;
ordered edges, block coordinates, and boundaries carry start/stop structure.

Every admitted anchor receives a deterministic symbol and position. Punctuation
is represented by the boundary or structural role it denotes. A mark without a
known structural role is represented as a Unicode object anchor instead of being
discarded. Original source text remains available alongside the exact-form map.

Answer direction is a view over the complete map, not a destructive intake
step. Content anchors and relationship operators may steer evidence retrieval. Glue anchors and boundaries
remain present, counted, positioned, and available to candidate-path continuity,
but they do not independently choose the subject of an answer. Evidence fit uses
dataset presence, inverse block frequency, and signed relationship counts.

The output walk remains deterministic: the current anchor produces a ranked
field of at most six next-anchor choices; the selected anchor becomes the new
center; the field is recalculated; and relationship continuity is evaluated over
the growing path. A deeper/wider relationship search is a separately requested
second pass after the first answer packet, not an automatic replacement for it.

DocuFilm is the only public intake entrypoint. A document object is represented
as a parent anchor followed by ordered contained anchors for its glyphs, words,
punctuation boundaries, nested objects, cells, labels, and values. Dataset-local
symbols never cross the model boundary as meaning: returned evidence uses the
original strings and citations.
