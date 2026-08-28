import os
import ast
import json
from tqdm import tqdm

EXCLUDED_FOLDERS = [
    "site-packages", "venv", "env", ".venv", ".env",
    "__pycache__", "Lib", "Scripts", "Include",
    "Windows", "Program Files", "Program Files (x86)",
    "$Recycle.Bin", "AppData", "node_modules"
]

CHUNK_SIZE = 1500

def should_exclude(path):
    for excluded in EXCLUDED_FOLDERS:
        if excluded.lower() in path.lower():
            return True
    return False

def extract_functions_from_source(source_code, file_path):
    functions = []
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(source_code, node)
                if func_source:
                    functions.append({
                        "name": node.name,
                        "source": func_source,
                        "file": file_path
                    })
        return functions, None
    except Exception as e:
        return [], str(e)

def get_all_python_files(directory_paths):
    file_paths = []
    for root_path in directory_paths:
        for dirpath, _, filenames in os.walk(root_path):
            if should_exclude(dirpath):
                continue
            for file in filenames:
                if file.endswith(".py"):
                    file_paths.append(os.path.join(dirpath, file))
    return file_paths

def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def scan_and_collect(directory_paths):
    all_files = get_all_python_files(directory_paths)
    total_files = len(all_files)
    print(f"[INFO] Total Python files to scan (after exclusions): {total_files}")

    collected = []
    skipped = []

    with tqdm(total=total_files, desc="Scanning Files") as pbar:
        for file_chunk in chunk_list(all_files, CHUNK_SIZE):
            sources = {}
            for file_path in file_chunk:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        sources[file_path] = f.read()
                except Exception as e:
                    skipped.append({
                        "file": file_path,
                        "error": str(e)
                    })
                    pbar.update(1)

            # Process functions from sources in memory
            for file_path, source_code in sources.items():
                funcs, error = extract_functions_from_source(source_code, file_path)
                if error:
                    skipped.append({
                        "file": file_path,
                        "error": error
                    })
                else:
                    collected.extend(funcs)
                pbar.update(1)

            # Optional: Save partial to disk after each chunk
            # with open("partial_functions.json", "w", encoding="utf-8") as f:
            #     json.dump(collected, f, indent=4)

    # Final saves
    with open("all_my_functions.json", "w", encoding="utf-8") as f:
        json.dump(collected, f, indent=4)

    with open("skipped_files.json", "w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4)

    summary = (
        f"Summary Report\n"
        f"---------------\n"
        f"Total Python files scanned: {total_files}\n"
        f"Total skipped files: {len(skipped)}\n"
        f"Total functions extracted: {len(collected)}\n"
    )
    with open("summary_report.txt", "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"[DONE] Functions saved to: all_my_functions.json")
    print(f"[DONE] Skipped file list saved to: skipped_files.json")
    print(f"[DONE] Summary report saved to: summary_report.txt")

if __name__ == "__main__":
    scan_and_collect(["C:/", "D:/"])
