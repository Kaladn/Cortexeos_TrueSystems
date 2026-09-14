"""Genesis Citation Tool — constants and paths.

All paths are module constants. CORPUS_PATH is NEVER user-supplied.
"""

from pathlib import Path

# ── Repo root resolution ──────────────────────────────────────────────────────
# This file lives at: <repo>/plugins/genesis_cite/config.py
# Repo root is therefore two parents up.
_THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _THIS_DIR.parent.parent

# ── Data source of truth ─────────────────────────────────────────────────────
CORPUS_PATH: Path = REPO_ROOT / "docs" / "GENESIS" / "TRAINING_CORPUS.md"
GENESIS_SPEC_PATH: Path = REPO_ROOT / "docs" / "GENESIS" / "GENESIS_SPEC.md"

# ── Derived index output (write-only dir for generated artefacts) ─────────────
INDEX_DIR: Path = REPO_ROOT / "data" / "derived" / "genesis"
CORPUS_INDEX_PATH: Path = INDEX_DIR / "corpus.index.json"
BM25_INDEX_PATH: Path = INDEX_DIR / "bm25.index.pkl"
BUILD_META_PATH: Path = INDEX_DIR / "build_meta.json"

# ── Block format ──────────────────────────────────────────────────────────────
SEPARATOR_CHAR: str = "\u2501"          # ━  (U+2501 BOX DRAWINGS HEAVY HORIZONTAL)
SEPARATOR_MIN_LEN: int = 20             # minimum run of ━ to count as separator
EXPECTED_BLOCK_COUNT: int = 68

# ── Search defaults ───────────────────────────────────────────────────────────
DEFAULT_SEARCH_LIMIT: int = 5
MAX_SEARCH_LIMIT: int = 20

# ── Required header fields (must be present in every block) ──────────────────
REQUIRED_HEADER_FIELDS: tuple[str, ...] = (
    "GENESIS_BLOCK_ID",
    "SOURCE",
    "DATE_RANGE",
    "SCOPE",
    "WRITE_PERMS",
)

# ── Series boundaries (for filter: series "1"–"12") ──────────────────────────
SERIES_RANGES: dict[str, tuple[int, int]] = {
    "1":  (1,  8),
    "2":  (9,  15),
    "3":  (16, 21),
    "4":  (22, 27),
    "5":  (28, 34),
    "6":  (35, 38),
    "7":  (39, 43),
    "8":  (44, 47),
    "9":  (48, 53),
    "10": (54, 57),
    "11": (58, 60),
    "12": (61, 68),
}
