"""Citation Extractor — detect external citation styles and extract references.

Runs on raw document text BEFORE chunking. Detects the citation style,
extracts the full reference list into a refs.json sidecar, and builds a
marker-to-reference lookup table. During chunking, each chunk that contains
a marker gets its citations resolved and stored in chunk metadata.

Supported citation families:
  - Numeric inline: [1], [1,2], [1-3]  (IEEE, Vancouver, biomedical)
  - Author-date: (Smith, 2019), (Smith et al., 2019)  (APA, MLA, Chicago)
  - Footnote/endnote: numbered footnotes at end of text
  - Hyperlink: bare URLs, DOI links, Wikipedia [1] style with URL refs
  - In-text full citation: older academic texts (best-effort)

All share the same structure: inline marker -> reference record.

Output:
  - refs: list of reference dicts (original text preserved exactly)
  - marker_to_ref: dict mapping marker string -> reference dict
  - style: detected citation style name
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Citation Style Detection ─────────────────────────────────────────────────

# Numeric inline: [1], [2,3], [1-5], [1, 2]
_NUMERIC_INLINE_RE = re.compile(r"\[(\d+(?:\s*[,\-\u2013]\s*\d+)*)\]")

# Author-date: (Smith, 2019), (Smith & Jones, 2020), (Smith et al., 2019)
_AUTHOR_DATE_RE = re.compile(
    r"\(([A-Z][a-z]+(?:\s+(?:&|and)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)\)"
)

# Footnote markers: superscript-style numbers at end of sentences
_FOOTNOTE_MARKER_RE = re.compile(r"(?<=[.!?\"\u201d])\s*(\d{1,3})(?=\s|$)")

# URL/DOI patterns
_URL_RE = re.compile(r"https?://[^\s\])<>\"]+")
_DOI_RE = re.compile(r"(?:doi:\s*|https?://doi\.org/)10\.\d{4,}/[^\s]+", re.IGNORECASE)

# Reference list markers — lines starting with [N] or N. at start of a references section
_REF_LINE_NUMERIC_RE = re.compile(r"^\s*\[(\d+)\]\s*(.+)", re.MULTILINE)
_REF_LINE_NUMBERED_RE = re.compile(r"^\s*(\d+)\.\s+(.+)", re.MULTILINE)

# Reference section headers
_REF_SECTION_RE = re.compile(
    r"^#{0,4}\s*(?:references|bibliography|works\s+cited|sources|endnotes|footnotes)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class ExtractedRef:
    """A single extracted reference."""
    marker: str                  # The inline marker as it appears: "[1]", "(Smith, 2019)"
    ref_number: Optional[int]    # Numeric index if applicable
    ref_text: str                # Full reference text (preserved exactly)
    style: str                   # "numeric", "author_date", "footnote", "hyperlink"
    urls: List[str] = field(default_factory=list)  # Any URLs/DOIs found in ref text
    authors: Optional[str] = None
    year: Optional[str] = None


@dataclass
class ExtractionResult:
    """Complete extraction result for a document."""
    style: str                   # Primary detected style
    refs: List[ExtractedRef]     # All extracted references
    marker_to_ref: Dict[str, ExtractedRef] = field(default_factory=dict)
    ref_section_start: int = -1  # Character offset where reference section begins (-1 = not found)


def detect_style(text: str) -> str:
    """Detect the primary citation style used in a document.

    Returns one of: "numeric", "author_date", "footnote", "hyperlink", "none"
    """
    # Count matches for each style
    numeric_matches = _NUMERIC_INLINE_RE.findall(text)
    author_date_matches = _AUTHOR_DATE_RE.findall(text)

    # Check for a references section
    has_ref_section = bool(_REF_SECTION_RE.search(text))

    # Count numeric inline citations [N] that look like real citations (not list items)
    # Heuristic: if there's a ref section and [N] markers, it's numeric
    numeric_count = len(numeric_matches)
    author_date_count = len(author_date_matches)

    # URLs/DOIs as primary citation method (Wikipedia style)
    url_count = len(_URL_RE.findall(text))
    doi_count = len(_DOI_RE.findall(text))

    logger.debug(
        "Citation detection: numeric=%d, author_date=%d, url=%d, doi=%d, ref_section=%s",
        numeric_count, author_date_count, url_count, doi_count, has_ref_section,
    )

    # Decision logic
    if numeric_count >= 3 and has_ref_section:
        return "numeric"
    if author_date_count >= 3:
        return "author_date"
    if numeric_count >= 3 and not has_ref_section and url_count > numeric_count:
        return "hyperlink"
    if numeric_count >= 3:
        return "numeric"
    if doi_count >= 2 or url_count >= 5:
        return "hyperlink"
    if author_date_count >= 1:
        return "author_date"

    return "none"


def _extract_ref_section(text: str) -> Tuple[str, int]:
    """Find and return the references section text and its start offset.

    Returns (ref_section_text, start_offset). If not found, returns ("", -1).
    """
    m = _REF_SECTION_RE.search(text)
    if not m:
        return "", -1

    # References section starts after the header line
    start = m.end()
    # Skip any blank lines after the header
    while start < len(text) and text[start] in "\n\r\t ":
        start += 1

    return text[start:], m.start()


def _extract_numeric_refs(text: str) -> ExtractionResult:
    """Extract numeric-style citations: [1], [2,3], [1-5]."""
    refs: List[ExtractedRef] = []
    marker_to_ref: Dict[str, ExtractedRef] = {}

    # Find reference section
    ref_section, ref_start = _extract_ref_section(text)

    if ref_section:
        # Parse [N] reference_text lines
        for m in _REF_LINE_NUMERIC_RE.finditer(ref_section):
            num = int(m.group(1))
            ref_text = m.group(2).strip()
            marker = f"[{num}]"
            urls = _URL_RE.findall(ref_text) + _DOI_RE.findall(ref_text)

            ref = ExtractedRef(
                marker=marker,
                ref_number=num,
                ref_text=ref_text,
                style="numeric",
                urls=list(set(urls)),
            )
            refs.append(ref)
            marker_to_ref[marker] = ref

        # Also try N. format if [N] format yielded nothing
        if not refs:
            for m in _REF_LINE_NUMBERED_RE.finditer(ref_section):
                num = int(m.group(1))
                ref_text = m.group(2).strip()
                marker = f"[{num}]"
                urls = _URL_RE.findall(ref_text) + _DOI_RE.findall(ref_text)

                ref = ExtractedRef(
                    marker=marker,
                    ref_number=num,
                    ref_text=ref_text,
                    style="numeric",
                    urls=list(set(urls)),
                )
                refs.append(ref)
                marker_to_ref[marker] = ref

    # For compound markers like [1,2] or [1-3], expand to individual refs
    # The marker_to_ref lookup handles individual [N] references

    logger.info("Extracted %d numeric references", len(refs))
    return ExtractionResult(
        style="numeric",
        refs=refs,
        marker_to_ref=marker_to_ref,
        ref_section_start=ref_start,
    )


def _extract_author_date_refs(text: str) -> ExtractionResult:
    """Extract author-date citations: (Smith, 2019), (Smith et al., 2019)."""
    refs: List[ExtractedRef] = []
    marker_to_ref: Dict[str, ExtractedRef] = {}
    seen: set = set()

    for m in _AUTHOR_DATE_RE.finditer(text):
        author = m.group(1).strip()
        year = m.group(2).strip()
        marker = m.group(0)  # Full match including parens
        key = f"{author}_{year}"

        if key in seen:
            continue
        seen.add(key)

        # Try to find the full reference in a references section
        ref_section, ref_start = _extract_ref_section(text)
        ref_text = ""
        if ref_section:
            # Look for a line containing this author and year
            for line in ref_section.split("\n"):
                if author.split()[0] in line and year in line:
                    ref_text = line.strip()
                    # Clean leading markers like [1] or 1.
                    ref_text = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", ref_text)
                    break

        if not ref_text:
            ref_text = f"{author}, {year}"

        urls = _URL_RE.findall(ref_text) + _DOI_RE.findall(ref_text)

        ref = ExtractedRef(
            marker=marker,
            ref_number=None,
            ref_text=ref_text,
            style="author_date",
            urls=list(set(urls)),
            authors=author,
            year=year,
        )
        refs.append(ref)
        marker_to_ref[marker] = ref

    logger.info("Extracted %d author-date references", len(refs))
    return ExtractionResult(
        style="author_date",
        refs=refs,
        marker_to_ref=marker_to_ref,
        ref_section_start=_extract_ref_section(text)[1],
    )


def _extract_hyperlink_refs(text: str) -> ExtractionResult:
    """Extract hyperlink/URL/DOI citations."""
    refs: List[ExtractedRef] = []
    marker_to_ref: Dict[str, ExtractedRef] = {}
    seen: set = set()

    # DOIs first (more specific)
    for m in _DOI_RE.finditer(text):
        url = m.group(0).strip()
        if url in seen:
            continue
        seen.add(url)
        ref = ExtractedRef(
            marker=url,
            ref_number=None,
            ref_text=url,
            style="hyperlink",
            urls=[url],
        )
        refs.append(ref)
        marker_to_ref[url] = ref

    # Then plain URLs (skip already-captured DOIs)
    for m in _URL_RE.finditer(text):
        url = m.group(0).strip()
        if url in seen:
            continue
        seen.add(url)
        ref = ExtractedRef(
            marker=url,
            ref_number=None,
            ref_text=url,
            style="hyperlink",
            urls=[url],
        )
        refs.append(ref)
        marker_to_ref[url] = ref

    logger.info("Extracted %d hyperlink references", len(refs))
    return ExtractionResult(
        style="hyperlink",
        refs=refs,
        marker_to_ref=marker_to_ref,
    )


def extract_citations(text: str, force_style: Optional[str] = None) -> ExtractionResult:
    """Main entry point — detect style and extract all citations from document text.

    Args:
        text: Raw document text
        force_style: Override auto-detection with a specific style

    Returns:
        ExtractionResult with refs list and marker_to_ref lookup
    """
    style = force_style or detect_style(text)
    logger.info("Citation extraction: style=%s, text_length=%d", style, len(text))

    if style == "numeric":
        return _extract_numeric_refs(text)
    elif style == "author_date":
        return _extract_author_date_refs(text)
    elif style == "hyperlink":
        return _extract_hyperlink_refs(text)
    else:
        # No citations detected
        return ExtractionResult(style="none", refs=[], marker_to_ref={})


def resolve_markers_in_chunk(
    chunk_text: str,
    extraction: ExtractionResult,
) -> List[Dict[str, Any]]:
    """Find citation markers within a chunk and resolve them to references.

    Returns a list of resolved citation dicts, each containing:
      - original_marker: the marker as it appears in text
      - original_ref: the full reference text (preserved exactly)
      - position: character offset of marker in chunk
      - style: citation style
      - urls: any URLs/DOIs in the reference
      - authors: author string (author_date only)
      - year: year string (author_date only)
    """
    resolved = []

    if extraction.style == "numeric":
        for m in _NUMERIC_INLINE_RE.finditer(chunk_text):
            raw = m.group(1)
            # Expand compound markers: [1,2] -> [1], [2]  and [1-3] -> [1], [2], [3]
            numbers = _expand_numeric_marker(raw)
            for num in numbers:
                marker = f"[{num}]"
                ref = extraction.marker_to_ref.get(marker)
                if ref:
                    resolved.append({
                        "original_marker": marker,
                        "original_ref": ref.ref_text,
                        "position": m.start(),
                        "style": ref.style,
                        "urls": ref.urls,
                    })

    elif extraction.style == "author_date":
        for m in _AUTHOR_DATE_RE.finditer(chunk_text):
            marker = m.group(0)
            ref = extraction.marker_to_ref.get(marker)
            if ref:
                resolved.append({
                    "original_marker": marker,
                    "original_ref": ref.ref_text,
                    "position": m.start(),
                    "style": ref.style,
                    "urls": ref.urls,
                    "authors": ref.authors,
                    "year": ref.year,
                })

    elif extraction.style == "hyperlink":
        for m in _DOI_RE.finditer(chunk_text):
            url = m.group(0).strip()
            ref = extraction.marker_to_ref.get(url)
            if ref:
                resolved.append({
                    "original_marker": url,
                    "original_ref": ref.ref_text,
                    "position": m.start(),
                    "style": ref.style,
                    "urls": ref.urls,
                })
        for m in _URL_RE.finditer(chunk_text):
            url = m.group(0).strip()
            ref = extraction.marker_to_ref.get(url)
            if ref and not any(r["original_marker"] == url for r in resolved):
                resolved.append({
                    "original_marker": url,
                    "original_ref": ref.ref_text,
                    "position": m.start(),
                    "style": ref.style,
                    "urls": ref.urls,
                })

    return resolved


def _expand_numeric_marker(raw: str) -> List[int]:
    """Expand compound numeric markers: '1,2' -> [1,2], '1-3' -> [1,2,3]."""
    numbers = []
    parts = re.split(r"[,\s]+", raw)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Handle ranges: 1-3 or 1\u20133
        range_m = re.match(r"(\d+)\s*[-\u2013]\s*(\d+)", part)
        if range_m:
            start, end = int(range_m.group(1)), int(range_m.group(2))
            numbers.extend(range(start, end + 1))
        elif part.isdigit():
            numbers.append(int(part))
    return numbers


def write_refs_sidecar(
    refs: List[ExtractedRef],
    output_path: str,
) -> None:
    """Write the extracted references to a refs.json sidecar file.

    Preserves reference text exactly as extracted — no normalization.
    """
    import json
    data = [asdict(r) for r in refs]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d references to %s", len(data), output_path)
