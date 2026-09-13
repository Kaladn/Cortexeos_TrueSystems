# The Basement: Multilevel Relationship-Graph Prototype

## Method

Deterministic lexical-object, sentence, and paragraph graphs. Punctuation is retained in source text but excluded from counts. No semantic weights or model judgments are used. Sentence windows stop at paragraph boundaries; paragraph windows stop at the document boundary.

## Structural counts

- Paragraphs: 235
- Sentences: 1573
- Unique same-sentence object pairs: 29351
- Unique same-paragraph object pairs: 165317
- Pairs corroborated at both levels: 29351
- Relationships exposed only after paragraph expansion: 135966
- Sentence-only invariant violations: 0

- Cross-paragraph neighbor edges prevented by containment: 8752

## Focus-term comparison

| Term | Sentence hits | Paragraph hits | Strong sentence partners | Strong paragraph partners |
|---|---:|---:|---|---|
| ashley | 132 | 107 | mom (14), said (14), demon (7), asked (6), basement (6) | mom (41), said (32), sword (28), time (27), all (27) |
| mom | 97 | 68 | ashley (14), said (9), get (8), help (7), demons (7) | ashley (41), said (19), now (19), going (18), all (18) |
| mother | 9 | 9 | ashley (3), real (2), own (2), added (1), frustration (1) | ashley (7), mom (5), knew (5), way (4), outside (3) |
| sword | 115 | 64 | back (12), demon (12), all (11), light (7), demons (7) | ashley (28), time (23), back (22), demon (19), all (18) |
| dream | 18 | 14 | ashley (4), world (3), control (2), take (2), going (2) | ashley (6), control (6), time (6), like (6), own (5) |
| demons | 54 | 35 | all (8), mom (7), sword (7), two (7), kill (5) | ashley (17), all (14), now (14), mom (13), time (13) |
| demon | 48 | 25 | sword (12), ashley (7), like (5), hunter (4), looked (4) | sword (19), like (13), ashley (11), about (10), head (10) |
| grandpa | 59 | 50 | said (16), ashley (5), told (4), world (4), sword (4) | said (24), ashley (20), about (15), came (14), sword (13) |
| anthony | 36 | 27 | like (5), said (4), went (4), back (4), never (4) | ashley (13), brother (10), back (10), mom (9), said (9) |
| frank | 39 | 26 | said (5), mom (4), down (3), come (3), those (3) | ashley (11), said (11), down (10), mom (10), come (9) |
| rift | 49 | 29 | world (7), open (7), basement (6), seal (5), blood (5) | world (18), ashley (14), mom (13), time (13), sword (11) |
| fear | 20 | 18 | knew (4), mom (3), back (2), like (2), trying (2) | like (9), back (7), basement (7), didn't (7), knew (7) |
| love | 7 | 5 | remember (2), flower (2), little (2), another (1), ashley (1) | said (4), flower (3), little (3), it's (2), know (2) |
| world | 58 | 44 | nether (22), rift (7), enter (6), must (5), life (5) | ashley (19), nether (19), rift (18), all (17), time (16) |
| basement | 44 | 35 | door (12), about (7), creatures (7), ashley (6), rift (6) | ashley (19), mom (16), knew (13), door (13), now (11) |

## Observed findings

1. **Containment materially changes the graph.** An unconstrained ±6 sentence walk would create 8,752 cross-paragraph neighbor edges. The contained graph prevents all of them.
2. **Paragraph expansion adds context rather than merely repeating sentence co-occurrence.** Every same-sentence pair is correctly contained by its paragraph, while 135,966 additional pairs exist only at paragraph scope.
3. **Sentence offsets are sharper than paragraph offsets.** Ashley→sword peaks at +1 sentence (14 of 28 forward observations); Ashley↔mom peaks at +2 sentences. Fear→sword peaks at +1, while sword→fear peaks at +2. These are candidates for replay across other documents, not correction constants.
4. **Paragraph offsets are comparatively flat.** Central cast and story objects recur throughout adjacent paragraphs, so apparent paragraph peaks often differ by only a few counts. A universal paragraph offset is not supported by this document alone.
5. **The levels do not say the same thing.** At sentence level Ashley's strongest inspected partners are mom and speech/action terms; at paragraph level sword, time, and larger scene context rise. Sentence graphs expose propositions; paragraph graphs expose scene membership.
6. **Lexical normalization remains unfinished.** Singular/plural forms (demon/demons), contractions, character aliases (mom/mother), and generic narrative verbs remain separate objects. They are preserved here so later normalization does not silently rewrite evidence.

## Reading rule

Agreement across levels is corroborated recurrence, not truth. Paragraph-only pairs show relationships that sentence-local counting cannot see. Offset peaks are observations to test across more sources, not preselected correction weights.
