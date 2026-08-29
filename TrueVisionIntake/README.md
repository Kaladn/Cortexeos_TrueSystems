# TrueVision Intake

TrueVision Intake is the top-level DocuFilm document and glyph-state intake
authority. It reads admitted document state, assigns stable glyph-state records,
and constructs the parent/contained handoff consumed by TrueMem. TrueVision may
produce visual state, but it does not own this intake after separation.

Run its native tests from this directory with:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```
