# TrueVision code glyph reading

Code reading begins with visual state, not guessed text.

```text
page or screen frame
-> frozen deciphering context
-> DocuFilm cell state
-> explicitly calibrated monospace cells
-> exact approved glyph matches
-> coordinate-preserving transcription
-> complete TrueMem anchor admission
-> declared-language syntax parser
-> source-cited structure records
```

## Perception rules

1. A frozen deciphering context must identify the source, the visual-object
   kind, the code source profile, the language authority, the glyph lexicon,
   the monospace calibration, and the view boundaries before recognition.
2. The stored DocuFilm cell state is the visual source of truth.
3. Glyph segmentation uses caller-supplied origin, cell size, rows, and columns.
   The first implementation does not infer a font grid.
4. One calibrated cell is one possible glyph. This keeps disconnected marks
   such as `:`, `=`, quotes, and dots together.
5. Only exact patterns from the approved, read-only glyph lexicon are recognized.
6. Unknown glyphs remain unknown and occupy their original cell. They are never
   dropped, guessed, autocorrected, or recovered from hidden source text.
7. Blank cells preserve visual whitespace and indentation. A static frame does
   not prove whether indentation came from tabs or spaces, nor whether the file
   ended with a newline.

The accepted visual-object kinds are a source-code file, an isolated editor
code region, a terminal code listing, or a document code block. Editor gutters
must be excluded, soft wrapping must be off, and the view must be declared a
complete file or complete snippet. Unknown object type, unknown language,
unisolated gutters, ambiguous wrapping, or missing identity blocks code parsing.

## Anchor rules

Every observed glyph state is admitted as a glyph-object anchor candidate.
After a complete glyph read, the derived code stream enters the existing
complete-anchor law unchanged:

- identifiers and keywords remain exact complete-word anchors;
- case is preserved;
- operators and punctuation remain boundary or structural-object anchors;
- glue anchors remain admitted and counted;
- no anchor is deleted because a parser considers it unimportant;
- whitespace receives no symbol, but its row and column runs remain structure;
- TrueMem alone allocates dataset-local symbols and owns counts, relations,
  coordinates, citations, and traversal.

Syntax structures supplement the anchor stream. They never replace it.

## Syntax rules

The language is declared by the caller or an already verified source profile.
It is not guessed from keywords. A real language parser may run only when every
occupied glyph cell has an exact one-character match.

Python is the first supported grammar. It uses the standard-library tokenizer
and AST parser and returns exact token surfaces, source coordinates,
definitions, imports, and call surfaces. It does not import, compile, evaluate,
or execute the observed program. Syntax proves only that the derived glyph
transcription is accepted by that grammar; it does not prove runtime behavior,
call resolution, safety, intent, or correctness.

Exact lexical reading is broader than grammar verification. Pygments-backed
lexers currently preserve and classify every token surface for Python,
JavaScript/JSX, TypeScript/TSX, PowerShell, Windows batch/command, C, C++, C#,
Rust, Bash/shell, Zsh, Fish, Java, Kotlin, Go, Ruby, Lua, PHP, Swift, SQL, and
F#. The lexer output must reconstruct the complete derived glyph text byte for
byte at the character layer. It supplies basic code vocabulary and boundaries;
it is not represented as a successful grammar parse.

JavaScript additionally uses Node's parse-only `--check` path with injection
options cleared and a fixed timeout. It returns syntax acceptance or rejection
without running the program. Python remains the only adapter that currently
returns AST definitions, imports, and call surfaces.

## Current recovered-code priority

The admitted recovered corpus sets the implementation order:

| Language family | Files | Current visual-code read |
| --- | ---: | --- |
| Python | 7,814 | exact glyphs + exact lexical tokens + AST/token grammar |
| JavaScript | 145 | exact glyphs + exact lexical tokens + parse-only syntax check |
| PowerShell | 60 | exact glyphs + exact lexical tokens; grammar pending |
| C/C++ and headers | 21 | exact glyphs + exact lexical tokens; grammar pending |
| TypeScript | 13 | exact glyphs + exact lexical tokens; grammar pending |
| Windows batch/command | 10 | exact glyphs + exact lexical tokens; grammar pending |
| C# | 8 | exact glyphs + exact lexical tokens; grammar pending |
| Rust | 2 | exact glyphs + exact lexical tokens; grammar pending |
| Shell | 2 | exact glyphs + exact lexical tokens; grammar pending |

These are capability levels, not accuracy claims. The next parser adapters are
chosen from this table and require real grammar tooling plus acceptance fixtures.

An unsupported declared grammar returns `NOT_IMPLEMENTED`. An incomplete glyph
read returns `not_attempted_incomplete_glyph_coverage`. Neither condition may be
upgraded into a successful code read by a receipt or presentation layer.

## Promotion rule

New glyph patterns require an explicit approved lexicon record. New languages
require a deterministic parser adapter, fixtures that include syntax failures
and dangerous-looking non-executed code, and an external acceptance test. A
heuristic lexer or an LLM description is not a grammar adapter.
