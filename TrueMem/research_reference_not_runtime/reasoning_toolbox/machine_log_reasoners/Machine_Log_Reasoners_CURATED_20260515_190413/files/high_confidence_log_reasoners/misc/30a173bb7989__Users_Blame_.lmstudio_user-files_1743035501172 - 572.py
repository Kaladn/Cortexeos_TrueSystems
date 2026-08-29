# FatAI_Control.py
import os
import time
import shutil
import subprocess
from pathlib import Path

# === CONFIGURATION ===
INPUT_DIR = Path("input_drop")
RAW_DIR = Path("raw")
CLEAN_DIR = Path("clean")
MERGED_DIR = Path("merged")
MODEL_DIR = Path("models")
CONTEXT_DIR = Path("context_stats")

MODULES = {
    "csv": "CSV toJSON.py",
    "json": "JsonPreCleaner.py",
    "txt": "tokenization_schema_Cleaner.py",
    "json_clean": "jsonmeld.py"
}

EXTENSION_HANDLERS = {
    ".csv": MODULES["csv"],
    ".json": MODULES["json"],
    ".txt": MODULES["txt"]
    # Extend here for .xml, .gz, etc.
}

# === SETUP DIRECTORIES ===
def setup_dirs():
    for d in [INPUT_DIR, RAW_DIR, CLEAN_DIR, MERGED_DIR, MODEL_DIR, CONTEXT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

# === STAGE 1: Move Input to Raw ===
def move_input_files():
    for file in INPUT_DIR.glob("*.*"):
        target = RAW_DIR / file.name
        shutil.move(str(file), str(target))
        print(f"📥 Moved {file.name} to raw directory.")

# === STAGE 2: Dispatch and Clean ===
def dispatch_and_clean():
    for file in RAW_DIR.glob("*.*"):
        ext = file.suffix.lower()
        handler = EXTENSION_HANDLERS.get(ext)
        if handler:
            print(f"🧹 Running {handler} on {file.name}...")
            subprocess.run(["python", f"scripts/{handler}", str(file)], check=True)
        else:
            print(f"⚠️ No handler for {file.name}. Skipping.")

# === STAGE 3: Merge ===
def merge_cleaned_data():
    print("🔗 Merging cleaned data...")
    subprocess.run(["python", "scripts/jsonmeld.py"], check=True)

# === STAGE 4: Train ===
def train_pipeline():
    print("🧠 Training pipeline...")
    subprocess.run(["python", "scripts/import os.py"], check=True)

# === MAIN PIPELINE ===
def main():
    print("🚀 FatAI Pipeline Control Module Starting...")
    setup_dirs()
    move_input_files()
    dispatch_and_clean()
    merge_cleaned_data()
    train_pipeline()
    print("✅ All tasks completed successfully.")

if __name__ == '__main__':
    main()
