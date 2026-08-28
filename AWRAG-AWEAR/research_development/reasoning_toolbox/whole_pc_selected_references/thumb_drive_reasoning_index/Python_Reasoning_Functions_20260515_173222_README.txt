Python Reasoning Functions Collection
Created: 2026-05-15 17:32:27
Source collection: C:\Users\mydyi\OneDrive\Documents\Desktop\Python_Reasoning_Engines_20260515_172849

Scope:
- Extracted Python def / async def blocks only from the previously copied reasoning-engine scripts.
- Kept function bodies and decorators.
- Included methods from classes as dedented snippets with qualified names such as ClassName.method.
- Did not include imports, module-level constants, class wrappers, CLI startup code, or other top-level script body code.
- Nested functions are kept inside their parent function block, not emitted as duplicate standalone snippets.
- Valid Python files used AST extraction. Files with syntax problems used a conservative line-based fallback extractor.

Files:
- functions_by_source/: per-source .functions.py files containing only extracted function/method blocks.
- ALL_EXTRACTED_FUNCTIONS.py: one combined searchable file.
- FUNCTION_INDEX.csv: one row per extracted function/method.
- SOURCE_MANIFEST.csv: one row per source script with extracted functions.
- SUMMARY_BY_FAMILY.csv: grouped counts.
- PARSE_NOTES.csv: files that needed fallback parsing.
- READ_ERRORS.csv: files that could not be read, if any.
