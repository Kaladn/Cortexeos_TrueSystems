from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas


DEFAULT_EXTS = {
    ".txt", ".md", ".py", ".json", ".yaml", ".yml", ".log", ".csv", ".ini", ".cfg"
}

DEFAULT_SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".vs", ".idea", "node_modules",
    "dist", "build", ".mypy_cache", ".pytest_cache"
}


def iter_files(root: Path, recurse: bool, exts: set[str], skip_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    if recurse:
        for p in root.rglob("*"):
            if p.is_dir() and p.name in skip_dirs:
                # rglob won't let us prune easily; just skip files under these dirs via check below
                continue
            if p.is_file() and p.suffix.lower() in exts:
                # skip if any parent folder is a skipped dir
                if any(parent.name in skip_dirs for parent in p.parents):
                    continue
                files.append(p)
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                files.append(p)

    return sorted(files, key=lambda x: str(x).lower())


def safe_pdf_name(root: Path, file_path: Path) -> str:
    # name PDFs based on relative path to avoid collisions
    rel = file_path.relative_to(root)
    s = str(rel)
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "_")
    return s + ".pdf"


def wrap_text_to_width(text: str, max_chars: int) -> list[str]:
    # simple char-based wrapping that respects existing newlines
    lines_out: list[str] = []
    for raw_line in text.splitlines():
        if raw_line == "":
            lines_out.append("")
            continue
        line = raw_line
        while len(line) > max_chars:
            lines_out.append(line[:max_chars])
            line = line[max_chars:]
        lines_out.append(line)
    return lines_out


def write_pdf_for_file(root: Path, file_path: Path, out_dir: Path, font_name: str = "Courier", font_size: int = 8):
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / safe_pdf_name(root, file_path)

    # Read text safely
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="utf-8", errors="replace")

    # PDF setup
    page_w, page_h = LETTER
    left = 36
    right = 36
    top = 36
    bottom = 36

    line_height = font_size + 2
    usable_w = page_w - left - right

    # Courier is monospaced; approx width per char:
    # This is a pragmatic heuristic that works well enough for code/text.
    approx_char_w = font_size * 0.6
    max_chars = max(40, int(usable_w / approx_char_w))

    wrapped_lines = wrap_text_to_width(content, max_chars=max_chars)

    c = Canvas(str(pdf_path), pagesize=LETTER)

    def header(page_num: int):
        c.setFont("Helvetica", 10)
        c.drawString(left, page_h - top, f"FILE: {str(file_path)}")
        c.setFont("Helvetica", 8)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawRightString(page_w - right, page_h - top, f"Generated: {ts}   Page: {page_num}")

        # separator line
        c.line(left, page_h - top - 8, page_w - right, page_h - top - 8)

    page_num = 1
    y = page_h - top - 20
    header(page_num)
    c.setFont(font_name, font_size)

    for line in wrapped_lines:
        if y < bottom:
            c.showPage()
            page_num += 1
            y = page_h - top - 20
            header(page_num)
            c.setFont(font_name, font_size)

        # drawString can choke on some control chars; sanitize a bit
        safe_line = line.replace("\t", "    ").replace("\x00", "�")
        c.drawString(left, y, safe_line)
        y -= line_height

    c.save()
    return pdf_path


def main():
    ap = argparse.ArgumentParser(description="Convert text-like files in parent directory to one-PDF-per-file.")
    ap.add_argument("--source", default="..", help="Source directory (default: parent directory '..').")
    ap.add_argument("--out", default="_pdf_out", help="Output directory (default: ./_pdf_out).")
    ap.add_argument("--recurse", action="store_true", help="Recurse into subfolders.")
    ap.add_argument("--ext", action="append", default=[], help="Add allowed extension (e.g. --ext .md). Can repeat.")
    ap.add_argument("--skipdir", action="append", default=[], help="Add skipped dir name (e.g. --skipdir .venv). Can repeat.")
    args = ap.parse_args()

    root = Path(args.source).resolve()
    out_dir = Path(args.out).resolve()

    exts = set(DEFAULT_EXTS)
    for e in args.ext:
        e = e.strip()
        if not e.startswith("."):
            e = "." + e
        exts.add(e.lower())

    skip_dirs = set(DEFAULT_SKIP_DIRS)
    for d in args.skipdir:
        skip_dirs.add(d.strip())

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Source directory not found: {root}")

    files = iter_files(root, recurse=args.recurse, exts=exts, skip_dirs=skip_dirs)
    if not files:
        print(f"No matching files in: {root}")
        print(f"Extensions: {', '.join(sorted(exts))}")
        return

    print(f"Source: {root}")
    print(f"Output: {out_dir}")
    print(f"Files:  {len(files)}")
    print("")

    ok = 0
    for f in files:
        try:
            pdf_path = write_pdf_for_file(root, f, out_dir)
            print(f"OK   {pdf_path.name}")
            ok += 1
        except Exception as ex:
            print(f"FAIL {f}  ({ex})")

    print(f"\nDone. PDFs created: {ok}/{len(files)}")


if __name__ == "__main__":
    main()
