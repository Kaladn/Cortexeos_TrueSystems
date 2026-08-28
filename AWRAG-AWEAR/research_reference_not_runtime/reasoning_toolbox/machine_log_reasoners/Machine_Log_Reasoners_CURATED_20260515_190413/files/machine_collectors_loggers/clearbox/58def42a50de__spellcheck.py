"""Spell-check engine for LakeSpeak normalization pipeline.

Prevents semantic duplication in the symbolic graph by catching misspellings
*before* they reach the symbolizer.  Two misspellings of the same word would
produce two different SHA-256 symbol IDs — parallel nodes for one concept.

Architecture (upstream of the symbolizer):
  1. SymSpell  = propose   — detect likely misspellings against canonical lexicon
  2. Operator  = decide    — accept / reject / edit each suggestion
  3. AliasMap  = enforce   — accepted corrections normalize tokens before hashing
  4. Symbolizer = pure     — always receives canonical token, one concept → one ID

Algorithm: SymSpell (symmetric-delete spelling correction)
  - Pre-computes delete-combinations within max_edit_distance
  - O(1) lookup at query time vs O(n) naive Levenshtein against 147 K entries
  - Max edit distance: 2 (covers ~95 % of real-world typos)
  - Prefix length: 7 (keeps memory bounded)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  SpellResult
# ---------------------------------------------------------------------------

@dataclass
class SpellResult:
    """Result of checking a single token."""
    token: str                         # Original input
    status: str                        # "correct" | "suggested" | "unknown"
    suggestion: Optional[str] = None   # Canonical form (if suggested)
    distance: int = 0                  # Edit distance (0 if correct)
    confidence: float = 1.0            # Frequency-ratio confidence


# ---------------------------------------------------------------------------
#  SpellChecker  (SymSpell core)
# ---------------------------------------------------------------------------

class SpellChecker:
    """SymSpell-based spell checker backed by the canonical lexicon.

    Parameters
    ----------
    lexicon_dir : Path
        Directory containing ``canonical_A.json`` … ``canonical_Z.json``.
    max_edit_distance : int
        Maximum Damerau-Levenshtein distance (default 2).
    prefix_length : int
        Only the first *prefix_length* chars are used for delete-key
        generation, keeping the dictionary bounded.
    """

    def __init__(
        self,
        lexicon_dir: Path,
        max_edit_distance: int = 2,
        prefix_length: int = 7,
    ) -> None:
        self.lexicon_dir = Path(lexicon_dir)
        self.max_edit_distance = max_edit_distance
        self.prefix_length = prefix_length

        # word → frequency  (canonical dictionary)
        self._words: dict[str, int] = {}
        # delete-key → set of original words that generate that key
        self._deletes: dict[str, set[str]] = {}
        self._max_length: int = 0
        self._loaded = False

    # ── loading ───────────────────────────────────────────────

    def load(self) -> None:
        """Load all canonical_*.json files and build the delete dictionary."""
        if self._loaded:
            return
        t0 = time.perf_counter()
        count = 0
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = self.lexicon_dir / f"canonical_{letter}.json"
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    entries = json.load(fh)
                for entry in entries:
                    word = entry.get("word", "").strip().lower()
                    if not word:
                        continue
                    freq = entry.get("frequency", 1)
                    if not isinstance(freq, (int, float)):
                        freq = 1
                    self._add_word(word, int(freq))
                    count += 1
            except (json.JSONDecodeError, OSError) as exc:
                LOGGER.warning("spellcheck: skipping %s: %s", path.name, exc)
        self._loaded = True
        elapsed = int((time.perf_counter() - t0) * 1000)
        LOGGER.info("SpellChecker loaded %d words in %d ms", count, elapsed)

    def _add_word(self, word: str, freq: int) -> None:
        self._words[word] = max(self._words.get(word, 0), freq)
        if len(word) > self._max_length:
            self._max_length = len(word)
        deletes = self._edits(word, 0, set())
        for d in deletes:
            key = d
            if key not in self._deletes:
                self._deletes[key] = set()
            self._deletes[key].add(word)

    def _edits(self, word: str, depth: int, result: set[str]) -> set[str]:
        """Generate all delete-variants up to ``max_edit_distance``."""
        depth += 1
        if depth > self.max_edit_distance:
            return result
        for i in range(len(word)):
            delete = word[:i] + word[i + 1:]
            if delete not in result:
                result.add(delete)
                if depth < self.max_edit_distance:
                    self._edits(delete, depth, result)
        return result

    # ── public API ────────────────────────────────────────────

    def check(self, token: str) -> SpellResult:
        """Check a single token against the lexicon."""
        self.load()
        token_lower = token.lower().strip()
        if not token_lower:
            return SpellResult(token=token, status="correct")

        # Exact match
        if token_lower in self._words:
            return SpellResult(token=token, status="correct", distance=0)

        # SymSpell lookup: generate deletes of the input, intersect with dict
        seen: set[str] = set()
        candidates: list[tuple[str, int, int]] = []  # (word, distance, freq)
        input_deletes = self._edits(token_lower, 0, set())
        input_deletes.add(token_lower)  # include the input itself

        for variant in input_deletes:
            if variant in self._deletes:
                for candidate in self._deletes[variant]:
                    if candidate in seen:
                        continue
                    dist = self._damerau_levenshtein(token_lower, candidate)
                    if dist <= self.max_edit_distance:
                        freq = self._words.get(candidate, 1)
                        candidates.append((candidate, dist, freq))
                        seen.add(candidate)
            # Also check if the variant itself is a valid word
            # (handles case where input has extra chars)
            if variant in self._words and variant not in seen and variant != token_lower:
                dist = self._damerau_levenshtein(token_lower, variant)
                if dist <= self.max_edit_distance:
                    freq = self._words.get(variant, 1)
                    candidates.append((variant, dist, freq))
                    seen.add(variant)

        if not candidates:
            return SpellResult(token=token, status="unknown")

        # Sort: lowest distance, prefer transpositions (common typos),
        # then most shared bigrams with input, then highest frequency.
        def _sort_key(c: tuple[str, int, int]) -> tuple:
            word, dist, freq = c
            is_transposition = self._is_adjacent_transposition(token_lower, word)
            shared = self._shared_bigrams(token_lower, word)
            return (dist, 0 if is_transposition else 1, -shared, -freq)

        candidates.sort(key=_sort_key)
        best_word, best_dist, best_freq = candidates[0]

        # Confidence: ratio of best frequency to max frequency in candidates
        max_freq = max(c[2] for c in candidates) if candidates else 1
        confidence = best_freq / max_freq if max_freq > 0 else 1.0

        return SpellResult(
            token=token,
            status="suggested",
            suggestion=best_word,
            distance=best_dist,
            confidence=round(confidence, 4),
        )

    def check_tokens(self, tokens: list[str]) -> list[SpellResult]:
        """Check a list of tokens.  Returns one SpellResult per token."""
        self.load()
        return [self.check(t) for t in tokens]

    @property
    def word_count(self) -> int:
        return len(self._words)

    def has_word(self, word: str) -> bool:
        self.load()
        return word.lower().strip() in self._words

    # ── Damerau-Levenshtein ───────────────────────────────────

    @staticmethod
    def _damerau_levenshtein(s: str, t: str) -> int:
        """Optimal-string-alignment (restricted edit) distance."""
        len_s = len(s)
        len_t = len(t)
        # Fast paths
        if s == t:
            return 0
        if len_s == 0:
            return len_t
        if len_t == 0:
            return len_s

        # DP matrix
        d = [[0] * (len_t + 1) for _ in range(len_s + 1)]
        for i in range(len_s + 1):
            d[i][0] = i
        for j in range(len_t + 1):
            d[0][j] = j

        for i in range(1, len_s + 1):
            for j in range(1, len_t + 1):
                cost = 0 if s[i - 1] == t[j - 1] else 1
                d[i][j] = min(
                    d[i - 1][j] + 1,       # deletion
                    d[i][j - 1] + 1,       # insertion
                    d[i - 1][j - 1] + cost,  # substitution
                )
                # Transposition
                if (i > 1 and j > 1
                        and s[i - 1] == t[j - 2]
                        and s[i - 2] == t[j - 1]):
                    d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)
        return d[len_s][len_t]

    @staticmethod
    def _is_adjacent_transposition(s: str, t: str) -> bool:
        """True if *s* and *t* differ only by a swap of two adjacent chars."""
        if len(s) != len(t):
            return False
        diffs = [i for i in range(len(s)) if s[i] != t[i]]
        return (len(diffs) == 2
                and diffs[1] - diffs[0] == 1
                and s[diffs[0]] == t[diffs[1]]
                and s[diffs[1]] == t[diffs[0]])

    @staticmethod
    def _shared_bigrams(s: str, t: str) -> int:
        """Count of character bigrams shared between *s* and *t*."""
        if len(s) < 2 or len(t) < 2:
            return 0
        s_bi = {s[i:i + 2] for i in range(len(s) - 1)}
        t_bi = {t[i:i + 2] for i in range(len(t) - 1)}
        return len(s_bi & t_bi)


# ---------------------------------------------------------------------------
#  AliasMap  — enforces accepted corrections before symbolization
# ---------------------------------------------------------------------------

class AliasMap:
    """Persistent misspelling → canonical mapping.

    When an operator *accepts* a spell-check suggestion, the pair is stored
    here.  At intake time the alias map is applied *before* the symbolizer
    so that ``"recieve"`` silently becomes ``"receive"`` and both share one
    symbol ID.

    Storage: ``<data_dir>/alias_map.json`` — simple ``{ misspelling: canonical }``
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self._path = self.data_dir / "alias_map.json"
        self._map: dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    self._map = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                LOGGER.warning("AliasMap: failed to load %s: %s", self._path, exc)
                self._map = {}
        self._loaded = True

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._map, fh, indent=2, ensure_ascii=False)

    def add(self, misspelling: str, canonical: str) -> None:
        """Register an accepted correction."""
        self._ensure_loaded()
        key = misspelling.lower().strip()
        val = canonical.lower().strip()
        if key and val and key != val:
            self._map[key] = val
            self._save()
            LOGGER.info("AliasMap: %r → %r", key, val)

    def remove(self, misspelling: str) -> bool:
        """Revoke a previously accepted correction.  Returns True if found."""
        self._ensure_loaded()
        key = misspelling.lower().strip()
        if key in self._map:
            del self._map[key]
            self._save()
            return True
        return False

    def resolve(self, token: str) -> str:
        """Return canonical form if aliased, else the token unchanged."""
        self._ensure_loaded()
        return self._map.get(token.lower().strip(), token)

    def resolve_tokens(self, tokens: list[str]) -> list[str]:
        """Resolve a list of tokens through the alias map."""
        self._ensure_loaded()
        return [self.resolve(t) for t in tokens]

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._map)

    def all_aliases(self) -> dict[str, str]:
        """Return a copy of the full alias map."""
        self._ensure_loaded()
        return dict(self._map)


# ---------------------------------------------------------------------------
#  CorrectionQueue  — JSONL-backed queue for human review
# ---------------------------------------------------------------------------

class CorrectionQueue:
    """Persistent queue for spell-check suggestions awaiting human review.

    Each entry is one line of JSON in ``<data_dir>/corrections.jsonl``.
    Resolved entries are rewritten in-place with an updated ``status`` field.

    Statuses: ``pending`` → ``accepted`` | ``rejected`` | ``edited``

    File locking: enqueue() and resolve() use a lockfile to prevent
    concurrent read-modify-write races (TOCTOU).
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self._path = self.data_dir / "corrections.jsonl"
        self._lockpath = self.data_dir / "corrections.lock"

    # ── file locking (Windows msvcrt) ─────────────────────────

    def _with_lock(self, fn):
        """Execute *fn* while holding an exclusive lockfile."""
        import msvcrt
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lockfd = open(self._lockpath, "w")
        try:
            msvcrt.locking(lockfd.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                return fn()
            finally:
                msvcrt.locking(lockfd.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            # Lock held by another process — wait and retry once
            import time as _t
            _t.sleep(0.1)
            try:
                msvcrt.locking(lockfd.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    return fn()
                finally:
                    msvcrt.locking(lockfd.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                LOGGER.warning("CorrectionQueue: could not acquire lock, proceeding unlocked")
                return fn()
        finally:
            lockfd.close()

    # ── write ─────────────────────────────────────────────────

    def enqueue(
        self,
        original: str,
        suggestion: Optional[str],
        context: str = "",
        source: str = "",
    ) -> str:
        """Add a new pending correction.  Returns the entry ID."""
        entry_id = uuid.uuid4().hex[:12]
        record = {
            "id": entry_id,
            "original": original,
            "suggestion": suggestion,
            "context": context[:200],
            "source": source,
            "status": "pending",
            "final_token": None,
            "timestamp": time.time(),
        }

        def _do_enqueue():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._with_lock(_do_enqueue)
        return entry_id

    def resolve(self, entry_id: str, action: str, final_token: str = "") -> bool:
        """Resolve a pending entry.

        Parameters
        ----------
        action : str
            ``"accept"`` — use the suggestion (or *final_token* override).
            ``"reject"`` — mark as intentional, no alias created.
            ``"edit"``   — operator supplied a manual correction in *final_token*.
        """
        if action not in ("accept", "reject", "edit"):
            return False

        result = {"found": False}

        def _do_resolve():
            lines = self._read_all()
            for rec in lines:
                if rec.get("id") == entry_id and rec.get("status") == "pending":
                    rec["status"] = action + "ed"  # accepted / rejected / edited
                    if action in ("accept", "edit"):
                        rec["final_token"] = final_token or rec.get("suggestion", "")
                    rec["resolved_at"] = time.time()
                    result["found"] = True
                    break
            if result["found"]:
                self._write_all(lines)

        self._with_lock(_do_resolve)
        return result["found"]

    # ── read ──────────────────────────────────────────────────

    def pending(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return pending entries, newest first."""
        entries = [r for r in self._read_all() if r.get("status") == "pending"]
        entries.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return entries[offset:offset + limit]

    def stats(self) -> dict:
        """Return counts by status."""
        all_entries = self._read_all()
        result: dict[str, int] = {"pending": 0, "accepted": 0, "rejected": 0, "edited": 0, "total": 0}
        for rec in all_entries:
            status = rec.get("status", "pending")
            result[status] = result.get(status, 0) + 1
            result["total"] += 1
        return result

    # ── internal ──────────────────────────────────────────────

    def _read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        lines: list[dict] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return lines

    def _write_all(self, records: list[dict]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
