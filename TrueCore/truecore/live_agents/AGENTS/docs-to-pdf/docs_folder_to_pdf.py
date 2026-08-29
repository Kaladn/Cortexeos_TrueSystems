#!/usr/bin/env python3
"""Convert a documentation folder into a combined PDF artifact.

This agent is intentionally narrow:
- reads Markdown, TXT, and common image files from one folder tree
- writes one generated PDF plus manifest and receipt
- plan-only mode writes nothing
- manifests and receipts store metadata and hashes, not raw document content
"""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import UTC, datetime


TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PAGE_SIZE = (1240, 1754)
MARGIN = 70
LINE_WIDTH = 118
LINES_PER_PAGE = 64


@dataclass(frozen=True, slots=True)
class SourceItem:
    path: Path
    suffix: str
    size: int
    sha256: str
    item_type: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert docs folder to a combined PDF artifact.")
    parser.add_argument("--source-folder", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    try:
        result = convert_docs_folder_to_pdf(
            source_folder=Path(args.source_folder),
            out_dir=Path(args.out_dir),
            plan_only=args.plan_only,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def convert_docs_folder_to_pdf(*, source_folder: Path, out_dir: Path, plan_only: bool = False) -> dict[str, Any]:
    source = source_folder.resolve()
    if not source.exists() or not source.is_dir():
        raise ValueError(f"source folder does not exist: {source}")

    items = _collect_source_items(source)
    supported = [item for item in items if item.item_type in {"text", "image"}]
    plan = {
        "schema_version": 1,
        "kind": "truecore_docs_folder_to_pdf_plan",
        "created_at_utc": _utc_now(),
        "dry_run": plan_only,
        "source_folder": str(source),
        "out_dir": str(out_dir.resolve()),
        "source_file_count": len(items),
        "supported_file_count": len(supported),
        "unsupported_file_count": len(items) - len(supported),
        "supported_suffixes": sorted(TEXT_SUFFIXES | IMAGE_SUFFIXES),
        "source_items": [_source_item_metadata(source, item) for item in items],
        "writes_performed": False,
        "raw_content_logged": False,
        "artifact_kind": "generated_pdf",
    }
    if plan_only:
        return plan
    if not supported:
        raise ValueError("no supported files found; expected Markdown, TXT, or image files")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        raise RuntimeError("PIL is required for PDF rendering") from exc

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"docs-pdf-{_safe_time()}-{uuid4().hex[:8]}"
    pages = _render_pages(source, supported, Image, ImageDraw, ImageFont)
    pdf_path = out_dir / f"{run_id}.pdf"
    pages[0].save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    for page in pages:
        page.close()

    manifest = {
        "schema_version": 1,
        "kind": "truecore_docs_folder_to_pdf_manifest",
        "created_at_utc": _utc_now(),
        "run_id": run_id,
        "source_folder": str(source),
        "pdf_path": str(pdf_path),
        "pdf_sha256": _file_hash(pdf_path),
        "pdf_size": pdf_path.stat().st_size,
        "source_file_count": len(items),
        "supported_file_count": len(supported),
        "source_items": [_source_item_metadata(source, item) for item in supported],
        "raw_content_logged": False,
        "artifact_kind": "generated_pdf",
    }
    manifest_path = out_dir / f"{run_id}.manifest.json"
    _write_json(manifest_path, manifest)
    receipt = {
        "schema_version": 1,
        "kind": "truecore_docs_folder_to_pdf_receipt",
        "created_at_utc": _utc_now(),
        "run_id": run_id,
        "source_folder": str(source),
        "pdf_path": str(pdf_path),
        "manifest_path": str(manifest_path),
        "pdf_sha256": manifest["pdf_sha256"],
        "source_file_count": len(items),
        "supported_file_count": len(supported),
        "raw_content_logged": False,
        "artifact_kind": "generated_pdf",
        "writes_performed": True,
    }
    receipt_path = out_dir / f"{run_id}.receipt.json"
    _write_json(receipt_path, receipt)
    return {
        "status": "ok",
        "dry_run": False,
        "run_id": run_id,
        "pdf_path": str(pdf_path),
        "manifest_path": str(manifest_path),
        "receipt_path": str(receipt_path),
        "supported_file_count": len(supported),
        "writes_performed": True,
        "raw_content_logged": False,
    }


def _collect_source_items(source: Path) -> list[SourceItem]:
    items: list[SourceItem] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        item_type = "text" if suffix in TEXT_SUFFIXES else "image" if suffix in IMAGE_SUFFIXES else "unsupported"
        items.append(
            SourceItem(
                path=path,
                suffix=suffix,
                size=path.stat().st_size,
                sha256=_file_hash(path),
                item_type=item_type,
            )
        )
    return items


def _render_pages(source: Path, items: list[SourceItem], Image, ImageDraw, ImageFont) -> list[Any]:
    pages = []
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    for item in items:
        relative = str(item.path.relative_to(source))
        if item.item_type == "text":
            pages.extend(_render_text_file(item.path, relative, Image, ImageDraw, font, title_font))
        elif item.item_type == "image":
            pages.append(_render_image_file(item.path, relative, Image, ImageDraw, font))
    return pages


def _render_text_file(path: Path, title: str, Image, ImageDraw, font, title_font) -> list[Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines: list[str] = [title, ""]
    for raw_line in text.splitlines():
        if not raw_line.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(raw_line, width=LINE_WIDTH, replace_whitespace=False) or [""])

    pages = []
    for start in range(0, max(1, len(lines)), LINES_PER_PAGE):
        page = Image.new("RGB", PAGE_SIZE, "white")
        draw = ImageDraw.Draw(page)
        y = MARGIN
        draw.text((MARGIN, y), title, fill=(20, 20, 20), font=title_font)
        y += 36
        for line in lines[start : start + LINES_PER_PAGE]:
            draw.text((MARGIN, y), line, fill=(30, 30, 30), font=font)
            y += 24
        pages.append(page)
    return pages


def _render_image_file(path: Path, title: str, Image, ImageDraw, font) -> Any:
    page = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(page)
    draw.text((MARGIN, MARGIN), title, fill=(20, 20, 20), font=font)
    with Image.open(path) as image:
        image = image.convert("RGB")
        max_width = PAGE_SIZE[0] - (MARGIN * 2)
        max_height = PAGE_SIZE[1] - (MARGIN * 3)
        image.thumbnail((max_width, max_height))
        x = (PAGE_SIZE[0] - image.width) // 2
        y = MARGIN + 50 + max(0, (max_height - image.height) // 2)
        page.paste(image, (x, y))
    return page


def _source_item_metadata(source: Path, item: SourceItem) -> dict[str, Any]:
    return {
        "relative_path": str(item.path.relative_to(source)),
        "suffix": item.suffix,
        "size": item.size,
        "sha256": item.sha256,
        "item_type": item.item_type,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _safe_time() -> str:
    return _utc_now().replace(":", "").replace(".", "").replace("Z", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
