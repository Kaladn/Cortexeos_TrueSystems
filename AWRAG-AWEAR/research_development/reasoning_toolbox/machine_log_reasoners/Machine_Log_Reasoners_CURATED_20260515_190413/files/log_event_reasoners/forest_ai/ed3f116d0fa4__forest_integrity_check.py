import os
import sys
import importlib.util
import traceback
import json
from pathlib import Path

# --- Config ---
ROOT = Path(__file__).parent
REPORT_FILE = ROOT / "forest_integrity_report.json"

IGNORED_DIRS = {"__pycache__", ".venv", "venv", "build", "dist"}
PROJECT_PREFIX = "forest"  # Adjust if your local module namespace differs

# --- Helper Functions ---
def find_imports(file_path):
    """Parse import statements (basic regex-free version)."""
    imports = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("import "):
                parts = line.replace(",", " ").split()
                imports += [p for p in parts[1:] if p != "as"]
            elif line.startswith("from "):
                parts = line.split()
                if len(parts) > 1:
                    imports.append(parts[1])
    return imports


def check_import(name):
    """Check whether module can be found."""
    try:
        spec = importlib.util.find_spec(name)
        return "ok" if spec else "missing"
    except Exception:
        return "error"


def analyze_file(path):
    rel = path.relative_to(ROOT)
    data = {"file": str(rel), "imports": []}
    for imp in find_imports(path):
        result = check_import(imp)
        data["imports"].append({"module": imp, "status": result})
    return data


# --- Main Walk ---
def main():
    print(f"\n🌲 Forest AI Integrity Check\n{'-'*40}")
    results = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                data = analyze_file(file_path)
                results.append(data)
                for imp in data["imports"]:
                    status = imp["status"]
                    symbol = "✅" if status == "ok" else ("⚠️" if status == "missing" else "💥")
                    print(f"{symbol} {file}: {imp['module']} ({status})")

    # --- Summary ---
    missing = sum(1 for r in results for i in r["imports"] if i["status"] == "missing")
    errors = sum(1 for r in results for i in r["imports"] if i["status"] == "error")
    total = sum(len(r["imports"]) for r in results)

    print(f"\nSummary: {total} imports checked | ⚠️ {missing} missing | 💥 {errors} errors\n")
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Report saved to {REPORT_FILE}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
