#!/usr/bin/env python3
"""Unified lexicon ingestion, merge, and validation engine for NEW LEXICON.

The module consolidates token harvesting, sanitisation, lexicon merging,
reporting, and symbol assignment into a single entry point.  It exposes a
command-line interface and an interactive numeric menu so operators can
run end-to-end workflows or scriptable sub-commands.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LEXICON_ROOT = BASE_DIR / "Cleaned_Lexicon"
WORDLIST_ROOT = BASE_DIR / "lexicon clean words"
BACKUP_ROOT = BASE_DIR / "Lexicon_Backup"
REPORTS_ROOT = BASE_DIR / "Reports"
LOGS_ROOT = BASE_DIR / "Logs"
CACHE_ROOT = BASE_DIR / "Cache"
PUBMED_ROOT = BASE_DIR / "PubMed_Cleaned"
STARRED_PUBMED_ROOT = BASE_DIR / "Lexicon_Starred_PubMed"
SYSTEM_BACKUP_ROOT = BASE_DIR / "System_Backup"
INTAKE_ROOT = BASE_DIR / "Intake"

DEFAULT_MIN_LEN = 5
STAR_POLICY = {"external": "*", "pubmed": "**"}
SUPPORTED_LETTERS = tuple(chr(code) for code in range(ord("A"), ord("Z") + 1))

for path in (
    BACKUP_ROOT,
    REPORTS_ROOT,
    LOGS_ROOT,
    CACHE_ROOT,
    LEXICON_ROOT,
    WORDLIST_ROOT,
    PUBMED_ROOT,
    STARRED_PUBMED_ROOT,
    SYSTEM_BACKUP_ROOT,
    INTAKE_ROOT,
):
    path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOGS_ROOT / "build_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
LOGGER = logging.getLogger("lexicon_engine")


def _populate_wordlists_from_source(source: Path, *, move: bool) -> None:
    WORDLIST_ROOT.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        iterator = (item for item in source.iterdir() if item.is_file())
    else:
        iterator = (source,)

    for item in iterator:
        destination = WORDLIST_ROOT / item.name
        try:
            if move:
                shutil.move(str(item), destination)
            else:
                shutil.copy2(item, destination)
        except Exception as exc:  # pragma: no cover - filesystem variability
            LOGGER.error("Failed to transfer %s -> %s: %s", item, destination, exc)


def _prompt_for_wordlists() -> None:
    if any(WORDLIST_ROOT.iterdir()):
        LOGGER.info("Wordlist directory already populated at %s", WORDLIST_ROOT)
        return

    print(
        "\n--- Wordlist Setup ---\n"
        f"Word list files will live under: {WORDLIST_ROOT}\n"
        "If you already have alphabetised JSON files, provide their directory path now.\n"
        "Leave blank to skip and add them later by placing the files in the folder above.\n"
    )
    response = input("Existing word list path (blank to skip): ").strip().strip('"')
    if not response:
        LOGGER.info("Skipping wordlist import; drop files into %s any time.", WORDLIST_ROOT)
        return

    source = Path(response).expanduser().resolve()
    if not source.exists():
        LOGGER.error("Provided wordlist path does not exist: %s", source)
        return

    move_files = input("Move files instead of copying? (y/N): ").strip().lower().startswith("y")
    _populate_wordlists_from_source(source, move=move_files)
    action = "moved" if move_files else "copied"
    LOGGER.info("Successfully %s wordlist files into %s", action, WORDLIST_ROOT)


def bootstrap_environment(*, interactive: bool) -> None:
    if not any(WORDLIST_ROOT.iterdir()):
        if interactive and sys.stdin.isatty():
            _prompt_for_wordlists()
        else:
            LOGGER.info(
                "Wordlist directory %s is empty. Add files manually or rerun in interactive mode to import.",
                WORDLIST_ROOT,
            )

# ---------------------------------------------------------------------------
# SYMBOL ASSIGNMENT HOOK
# ---------------------------------------------------------------------------
try:  # pragma: no cover - import shim
    from Compression_Engine_symbolmaker import generate_symbol  # type: ignore
except Exception:  # pragma: no cover - deterministic fallback
    LOGGER.warning("Falling back to internal symbol generator; symbolic metadata will be minimal.")

    def generate_symbol(word: str, /) -> Dict[str, str]:
        token = unicodedata.normalize("NFKC", word.strip().lower())
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        binary = bin(int(digest[:16], 16))[2:].zfill(64)
        hex_value = f"0x{digest[:10].upper()}"
        font_symbol = f"CHAR_{digest[10:20].upper()}"
        tone_signature = f"TONE_{int(digest[20:26], 16) % 900000 + 100000}"
        return {
            "binary": binary,
            "hex": hex_value,
            "font_symbol": font_symbol,
            "tone_signature": tone_signature,
        }


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------
@dataclass
class MergeStats:
    letter: str
    examined: int
    duplicates: int
    appended: int


# ---------------------------------------------------------------------------
# LEXICON I/O UTILITIES
# ---------------------------------------------------------------------------
def _lexicon_file(letter: str, root: Path) -> Path:
    return root / f"{letter}.json"


def load_lexicon(root: Path = LEXICON_ROOT) -> Dict[str, List[Dict[str, object]]]:
    lexicon: Dict[str, List[Dict[str, object]]] = {}
    for letter in SUPPORTED_LETTERS:
        path = _lexicon_file(letter, root)
        if not path.exists():
            lexicon[letter] = []
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                lexicon[letter] = payload
            else:
                LOGGER.warning("%s is not a list; skipping", path)
                lexicon[letter] = []
        except json.JSONDecodeError as exc:  # pragma: no cover - rare corrupt file
            LOGGER.error("Failed to decode %s: %s", path, exc)
            lexicon[letter] = []
    return lexicon


def save_lexicon(data: Dict[str, List[Dict[str, object]]], root: Path = LEXICON_ROOT) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for letter, records in data.items():
        path = _lexicon_file(letter, root)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def backup_lexicon(root: Path = LEXICON_ROOT, destination: Path = BACKUP_ROOT) -> Path:
    timestamp = datetime.now().strftime("symbolized_%Y%m%d_%H%M%S")
    backup_dir = destination / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for letter in SUPPORTED_LETTERS:
        src = _lexicon_file(letter, root)
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)
    LOGGER.info("Backup created at %s", backup_dir)
    return backup_dir


# ---------------------------------------------------------------------------
# TOKENISATION & NORMALISATION
# ---------------------------------------------------------------------------
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z\-]{0,127}")


def tokenize_text(text: str) -> Iterator[str]:
    yield from _WORD_PATTERN.findall(text)


def normalize_token(token: str, *, min_len: int = DEFAULT_MIN_LEN, alpha_only: bool = True) -> Optional[str]:
    if not token:
        return None
    normalized = unicodedata.normalize("NFKC", token).strip().lower()
    if len(normalized) < min_len:
        return None
    if alpha_only and not re.fullmatch(r"[a-z\-]+", normalized):
        return None
    while normalized.endswith("-"):
        normalized = normalized[:-1]
    return normalized or None


def sanitize_tokens(tokens: Iterable[str], *, min_len: int = DEFAULT_MIN_LEN) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for token in tokens:
        normalized = normalize_token(token, min_len=min_len)
        if normalized and normalized not in seen:
            seen.add(normalized)
            cleaned.append(normalized)
    return cleaned


# ---------------------------------------------------------------------------
# SOURCE HANDLERS
# ---------------------------------------------------------------------------
def iter_text_xml(path: Path) -> Iterator[str]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    tags = {"ArticleTitle", "AbstractText", "Keyword", "MeshHeading"}
    with opener(path, "rt", encoding="utf-8", errors="ignore") as handle:
        context = ET.iterparse(handle, events=("end",))
        for _, element in context:
            if element.tag in tags and element.text:
                yield element.text
            element.clear()


def iter_text_txt(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        yield from handle


def iter_text_json(path: Path) -> Iterator[str]:
    def walk(node: object) -> Iterator[str]:
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value)

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        payload = json.load(handle)
    yield from walk(payload)


def iter_text_csv(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            yield " ".join(row)


def iter_text_docx(path: Path) -> Iterator[str]:  # pragma: no cover - optional dependency
    try:
        import docx  # type: ignore
    except ImportError:
        LOGGER.warning("python-docx not installed; skipping %s", path)
        return iter(())
    document = docx.Document(path)
    return (paragraph.text for paragraph in document.paragraphs)


def iter_text_pdf(path: Path) -> Iterator[str]:  # pragma: no cover - optional dependency
    try:
        from pdfminer.high_level import extract_text  # type: ignore
    except ImportError:
        LOGGER.warning("pdfminer.six not installed; skipping %s", path)
        return iter(())
    text = extract_text(str(path))
    return text.splitlines()


HANDLER_MAP = {
    ".xml": iter_text_xml,
    ".gz": iter_text_xml,
    ".txt": iter_text_txt,
    ".json": iter_text_json,
    ".csv": iter_text_csv,
    ".docx": iter_text_docx,
    ".pdf": iter_text_pdf,
}


def discover_files(source: Path, *, allowed_exts: Optional[Sequence[str]] = None) -> List[Path]:
    allowed = {ext.lower() for ext in (allowed_exts or HANDLER_MAP.keys())}
    files: List[Path] = []
    for candidate in source.rglob("*"):
        if candidate.suffix.lower() in allowed:
            files.append(candidate)
    return files


# ---------------------------------------------------------------------------
# KNOWN SET & VALIDATION
# ---------------------------------------------------------------------------
def canonical_status(entry: Dict[str, object]) -> str:
    status = entry.get("status", "")
    if not isinstance(status, str):
        return ""
    return status.rstrip("*").strip().lower()


def build_known_set(lexicon: Dict[str, List[Dict[str, object]]]) -> set[str]:
    return {canonical_status(entry) for buckets in lexicon.values() for entry in buckets if canonical_status(entry)}


def validate_lexicon(
    lexicon: Dict[str, List[Dict[str, object]]],
    *,
    mark_external: bool = False,
) -> Dict[str, int]:
    required = {"binary", "hex", "font_symbol", "tone_signature", "status"}
    stats = Counter()
    for letter, entries in lexicon.items():
        for idx, entry in enumerate(entries):
            stats["slots"] += 1
            missing = required.difference(entry.keys())
            if missing:
                stats["malformed_slots"] += 1
                LOGGER.warning("%s[%d] missing keys: %s", letter, idx, sorted(missing))
            status = entry.get("status")
            if not isinstance(status, str) or not status.strip():
                stats["invalid_status"] += 1
            elif mark_external and (status.endswith("*") or status.endswith("**")):
                stats["external_marked"] += 1
    return dict(stats)


# ---------------------------------------------------------------------------
# MERGE / APPEND LOGIC
# ---------------------------------------------------------------------------
def append_words(
    lexicon: Dict[str, List[Dict[str, object]]],
    words: Iterable[str],
    *,
    source_tag: Optional[str] = None,
    assign_symbols: bool = True,
    prefer_uppercase: bool = False,
) -> List[MergeStats]:
    updates: List[MergeStats] = []
    for letter in SUPPORTED_LETTERS:
        bucket = lexicon.setdefault(letter, [])
        existing = {canonical_status(entry) for entry in bucket}
        candidates = [word for word in words if word.startswith(letter.lower()) and word not in existing]
        if not candidates:
            continue
        appended = 0
        for token in candidates:
            status_value = token.upper() if prefer_uppercase else token
            if source_tag in STAR_POLICY:
                status_value = f"{status_value}{STAR_POLICY[source_tag]}"
            payload = generate_symbol(token) if assign_symbols else {}
            record = {
                "binary": payload.get("binary", ""),
                "hex": payload.get("hex", ""),
                "font_symbol": payload.get("font_symbol", ""),
                "tone_signature": payload.get("tone_signature", ""),
                "status": status_value,
            }
            bucket.append(record)
            appended += 1
        updates.append(MergeStats(letter=letter, examined=len(candidates), duplicates=0, appended=appended))
    return updates


# ---------------------------------------------------------------------------
# CORPUS PROCESSING
# ---------------------------------------------------------------------------
def _process_file_worker(args: Tuple[Path, int]) -> set[str]:
    path, min_len = args
    handler = HANDLER_MAP.get(path.suffix.lower())
    if handler is None:
        return set()
    collected: set[str] = set()
    for text in handler(path):
        for token in tokenize_text(text):
            normalized = normalize_token(token, min_len=min_len)
            if normalized:
                collected.add(normalized)
    return collected


def process_corpus(
    source: Path,
    *,
    min_len: int = DEFAULT_MIN_LEN,
    workers: Optional[int] = None,
) -> set[str]:
    files = discover_files(source)
    if not files:
        LOGGER.warning("No supported files discovered under %s", source)
        return set()
    LOGGER.info("Processing %d files from %s", len(files), source)
    aggregate: set[str] = set()
    worker_count = max(1, workers or os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(_process_file_worker, (path, min_len)) for path in files]
        for future in as_completed(futures):
            try:
                aggregate |= future.result()
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.error("Worker failed: %s", exc)
    LOGGER.info("Harvested %d unique tokens", len(aggregate))
    return aggregate


# ---------------------------------------------------------------------------
# REPORTING
# ---------------------------------------------------------------------------
def write_summary(name: str, data: Dict[str, object]) -> Path:
    destination = REPORTS_ROOT / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return destination


# ---------------------------------------------------------------------------
# ORCHESTRATORS
# ---------------------------------------------------------------------------
def intake_and_merge(
    source_dir: Path,
    *,
    min_len: int = DEFAULT_MIN_LEN,
    tag: Optional[str] = "pubmed",
    workers: Optional[int] = None,
    update_wordlists: bool = False,
    dry_run: bool = False,
) -> Dict[str, object]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    lexicon = load_lexicon()
    known = build_known_set(lexicon)
    harvested = process_corpus(source_dir, min_len=min_len, workers=workers)
    novel = sorted(token for token in harvested if token not in known)

    LOGGER.info("%d novel tokens identified", len(novel))
    updates = append_words(lexicon, novel, source_tag=tag, assign_symbols=True)

    if not dry_run:
        save_lexicon(lexicon)
        if update_wordlists:
            _update_wordlists(novel)

    summary = {
        "source_dir": str(source_dir),
        "min_len": min_len,
        "tag": tag,
        "workers": workers or os.cpu_count(),
        "tokens_harvested": len(harvested),
        "novel_tokens": len(novel),
        "dry_run": dry_run,
        "update_wordlists": update_wordlists,
        "per_letter": [dataclass.__dict__ for dataclass in updates],
    }
    write_summary("intake_merge_summary.json", summary)
    return summary


def _update_wordlists(tokens: Sequence[str]) -> None:
    index: Dict[str, List[str]] = defaultdict(list)
    for token in tokens:
        letter = token[0].upper()
        index[letter].append(token)
    for letter, words in index.items():
        path = WORDLIST_ROOT / f"{letter}.json"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            LOGGER.warning("%s is not a list; skipping wordlist update", path)
            continue
        existing = {str(item).strip().lower() for item in data if isinstance(item, str)}
        appended = False
        for word in words:
            if word.lower() not in existing:
                data.append(word)
                appended = True
        if appended:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(sorted(data), handle, ensure_ascii=False, indent=2)
                handle.write("\n")


def run_validation(mark_external: bool = False) -> Dict[str, int]:
    lexicon = load_lexicon()
    report = validate_lexicon(lexicon, mark_external=mark_external)
    write_summary("validation_report.json", report)
    return report


def build_known_set_report() -> Dict[str, object]:
    lexicon = load_lexicon()
    known = build_known_set(lexicon)
    payload = {"unique_tokens": len(known)}
    write_summary("known_set_summary.json", payload)
    return payload


def regenerate_pubmed_marks(
    lexicon_root: Path = LEXICON_ROOT,
    pubmed_root: Path = PUBMED_ROOT,
    output_dir: Optional[Path] = STARRED_PUBMED_ROOT,
    workers: Optional[int] = None,
) -> Optional[Path]:
    marker_script = BASE_DIR / "mark_pubmed_terms.py"
    if not marker_script.exists():  # pragma: no cover - optional helper
        LOGGER.error("mark_pubmed_terms.py not found; cannot regenerate PubMed marks")
        return None
    import subprocess

    args = [
        sys.executable,
        str(marker_script),
        "--lexicon-root",
        str(lexicon_root),
        "--pubmed-root",
        str(pubmed_root),
    ]
    if output_dir is not None:
        args += ["--output-dir", str(output_dir)]
    if workers is not None:
        args += ["--workers", str(workers)]
    LOGGER.info("Running PubMed marker: %s", " ".join(args))
    subprocess.run(args, check=True)
    return output_dir


# ---------------------------------------------------------------------------
# CLI UTILITIES
# ---------------------------------------------------------------------------
def interactive_menu() -> None:
    MENU = (
        "\n=== Lexicon Engine ===\n"
        "1) Intake & merge\n"
        "2) Validate lexicon\n"
        "3) Backup lexicon\n"
        "4) Known-set summary\n"
        "5) Regenerate PubMed marks\n"
        "6) Quit\n"
        "Select: "
    )
    while True:
        choice = input(MENU).strip()
        if choice == "1":
            source_raw = input(f"Source directory [{INTAKE_ROOT}]: ").strip().strip('"')
            source_dir = Path(source_raw).expanduser().resolve() if source_raw else INTAKE_ROOT
            min_len = int(input(f"Min token length [{DEFAULT_MIN_LEN}]: ") or DEFAULT_MIN_LEN)
            workers = input(f"Workers [{os.cpu_count()}]: ")
            workers_val = int(workers) if workers else os.cpu_count()
            tag = input("Tag (pubmed/external/none) [pubmed]: ").strip() or "pubmed"
            update_wordlists = input("Update wordlists? (y/N): ").lower().startswith("y")
            dry_run = input("Dry run? (y/N): ").lower().startswith("y")
            intake_and_merge(
                source_dir,
                min_len=min_len,
                tag=None if tag == "none" else tag,
                workers=workers_val,
                update_wordlists=update_wordlists,
                dry_run=dry_run,
            )
        elif choice == "2":
            mark = input("Count external markers? (y/N): ").lower().startswith("y")
            report = run_validation(mark_external=mark)
            LOGGER.info("Validation report: %s", report)
        elif choice == "3":
            backup_lexicon()
        elif choice == "4":
            payload = build_known_set_report()
            LOGGER.info("Known-set summary: %s", payload)
        elif choice == "5":
            regenerate_pubmed_marks(output_dir=STARRED_PUBMED_ROOT)
        elif choice == "6":
            LOGGER.info("Goodbye")
            break
        else:
            LOGGER.warning("Invalid selection: %s", choice)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified lexicon engine for NEW LEXICON")
    parser.add_argument("--menu", action="store_true", help="Launch interactive menu")
    parser.add_argument("--intake", type=Path, help=f"Directory to ingest (drop files into {INTAKE_ROOT} for menu use)")
    parser.add_argument("--min-len", type=int, default=DEFAULT_MIN_LEN, help="Minimum token length")
    parser.add_argument("--tag", type=str, default="pubmed", choices=["pubmed", "external", "none"], help="Star tagging policy")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Process pool size")
    parser.add_argument("--update-wordlists", action="store_true", help="Append new tokens to lexicon clean words")
    parser.add_argument("--dry-run", action="store_true", help="Process without writing lexicon updates")
    parser.add_argument("--validate", action="store_true", help="Run lexicon validation")
    parser.add_argument("--mark-external", action="store_true", help="Count external markers during validation")
    parser.add_argument("--backup", action="store_true", help="Create a lexicon backup snapshot")
    parser.add_argument("--known-set", action="store_true", help="Emit known-set summary")
    parser.add_argument("--regen-pubmed", action="store_true", help="Regenerate PubMed star markers using mark_pubmed_terms.py")
    parser.add_argument("--pubmed-output", type=Path, default=STARRED_PUBMED_ROOT, help="Output directory for PubMed marker regeneration")
    parser.add_argument("--pubmed-root", type=Path, default=PUBMED_ROOT, help="PubMed cleaned directory for marker regeneration")
    parser.add_argument("--lexicon-root", type=Path, default=LEXICON_ROOT, help="Lexicon root for marker regeneration")
    parser.add_argument("--workers-marker", type=int, default=None, help="Worker override for marker regeneration")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)

    interactive_mode = args.menu or not any(
        [
            args.intake,
            args.validate,
            args.backup,
            args.known_set,
            args.regen_pubmed,
        ]
    )

    bootstrap_environment(interactive=interactive_mode)

    if interactive_mode:
        interactive_menu()
        return

    if args.intake:
        intake_and_merge(
            args.intake,
            min_len=args.min_len,
            tag=None if args.tag == "none" else args.tag,
            workers=args.workers,
            update_wordlists=args.update_wordlists,
            dry_run=args.dry_run,
        )
    if args.validate:
        report = run_validation(mark_external=args.mark_external)
        LOGGER.info("Validation report: %s", report)
    if args.backup:
        backup_lexicon()
    if args.known_set:
        payload = build_known_set_report()
        LOGGER.info("Known-set summary: %s", payload)
    if args.regen_pubmed:
        regenerate_pubmed_marks(
            lexicon_root=args.lexicon_root,
            pubmed_root=args.pubmed_root,
            output_dir=args.pubmed_output,
            workers=args.workers_marker,
        )


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
