import os
import json
import mmap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

EXCLUDED_DIRS = {
    "$RECYCLE.BIN", "System Volume Information", "Windows", 
    "Program Files", "Program Files (x86)",
    "Steam", "Epic Games", "steamapps", "node_modules", 
    "venv", ".venv", ".git", "__pycache__", 
    "AppData", "ProgramData"
}


CHUNK_SIZE = 400 * 1024 * 1024  # 400 MB chunk size

def is_excluded_dir(dirname):
    return any(excluded in dirname for excluded in EXCLUDED_DIRS)

def collect_files(base_dir, extensions):
    base_path = Path(base_dir).resolve()
    files = []
    for root, dirs, filenames in os.walk(base_dir, topdown=True):
        dirs[:] = [d for d in dirs if not is_excluded_dir(d)]
        for fname in filenames:
            try:
                fpath = Path(root) / fname
                resolved_path = fpath.resolve(strict=False)
                if fpath.suffix in extensions and resolved_path.as_posix().startswith(base_path.as_posix()):
                    files.append(fpath)
            except Exception:
                continue
    return files

def process_file(file):
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
            if file.suffix == ".py":
                content = f"### START OF FILE: {file.name}\n" + content + f"\n### END OF FILE: {file.name}"
            entry = {"prompt": "", "completion": content}
            return entry, len(content.encode('utf-8'))
    except (FileNotFoundError, PermissionError, OSError):
        print(f"[red][SKIP] Skipped (protected/corrupt): {file}")
    except Exception as e:
        print(f"[red][FAIL] Failed to read {file}: {e}")
    return None, 0

def stream_to_jsonl(files, output_path):
    count = 0
    chunk = []
    chunk_bytes = 0
    chunk_index = 0

    def flush_chunk():
        nonlocal chunk, chunk_index, chunk_bytes
        chunk_file = output_path.with_name(f"{output_path.stem}_part{chunk_index}.jsonl")
        chunk_file.parent.mkdir(parents=True, exist_ok=True)
        with open(chunk_file, 'w', encoding='utf-8') as out:
            for entry in chunk:
                out.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"[yellow][SAVE] Flushed chunk {chunk_index} to {chunk_file.name} ({len(chunk)} entries)[/yellow]")
        chunk = []
        chunk_bytes = 0
        chunk_index += 1

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("{task.description}"),
        transient=True,
        console=console
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
            future_to_file = {executor.submit(process_file, file): file for file in files}
            for future in as_completed(future_to_file):
                result, byte_size = future.result()
                if result:
                    chunk.append(result)
                    chunk_bytes += byte_size
                    count += 1
                    if chunk_bytes >= CHUNK_SIZE:
                        flush_chunk()
                
    if chunk:
        flush_chunk()

    print(f"[green][DONE] Complete. {count} items streamed to chunked files in [bold]{output_path.parent}[/bold]")
if __name__ == "__main__":
    base_dir = "D:/"
    output_jsonl = Path("F:/training_data.jsonl")
    extensions = {ext for ext in [
        ".md", ".py", ".txt", ".json", ".yaml", ".yml", ".ipynb", ".log", ".pyw", ".pyx"
    ]}

    print("[bold cyan][SCAN] Scanning directory for files...[/bold cyan]")
    files = collect_files(base_dir, extensions)
    print(f"[blue][FOUND] Found {len(files)} eligible files[/blue]")

    stream_to_jsonl(files, output_jsonl)