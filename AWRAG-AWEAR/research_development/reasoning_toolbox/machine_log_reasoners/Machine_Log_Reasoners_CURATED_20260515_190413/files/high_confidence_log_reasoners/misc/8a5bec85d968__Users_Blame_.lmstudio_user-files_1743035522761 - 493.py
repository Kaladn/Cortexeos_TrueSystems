# === FatAI Pipeline Orchestration: control.py ===
import os
import shutil
import time
import importlib
from pathlib import Path

# === CONFIGURATION ===
ROOT_DIR = Path(__file__).resolve().parent
INPUT_DROP = ROOT_DIR / "input_drop"
MODULES_DIR = ROOT_DIR / "system_modules"
PROCESSED_DIR = ROOT_DIR / "processed_data"
LOG_DIR = ROOT_DIR / "logs"
MODEL_DIR = ROOT_DIR / "models"
CONTEXT_DIR = ROOT_DIR / "context_stats"

# === STEP MODULES (PHASE 1) ===
STEP_MODULES = [
    "json_utils.json_checker",
    "json_utils.json_converter",
    "cleaners.json_precleaner",
    "cleaners.json_word_cleaner",
    "cleaners.tokenization_cleaner",
    "json_utils.json_word_grabber"
]

# === HELPER: Run module.main(input_path, output_path) ===
def run_module(module_name, input_path, output_path):
    print(f"🚀 Running: {module_name}")
    module = importlib.import_module(f"system_modules.{module_name}")
    if hasattr(module, "main"):
        module.main(input_path, output_path)
    else:
        print(f"⚠️  Skipping {module_name}: No main() function found.")

# === ORCHESTRATE ===
def orchestrate_pipeline():
    input_path = INPUT_DROP
    output_path = PROCESSED_DIR

    # Ensure dirs exist
    for path in [INPUT_DROP, PROCESSED_DIR, LOG_DIR, MODEL_DIR, CONTEXT_DIR]:
        path.mkdir(exist_ok=True)

    files = list(input_path.glob("*"))
    if not files:
        print("📭 No input files found. Drop something into input_drop.")
        return

    # Run each module in order
    for step in STEP_MODULES:
        run_module(step, input_path, output_path)
        # Move processed files to temp
        for file in input_path.glob("*"):
            shutil.move(str(file), output_path / file.name)
        # Swap roles
        input_path, output_path = output_path, input_path

    print("✅ Phase 1 Complete — Ready for next stage (trainer, stats, etc.)")

if __name__ == '__main__':
    orchestrate_pipeline()
