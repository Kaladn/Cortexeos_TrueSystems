import os
import shutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Base directory (adjust this if your path differs)
BASE_DIR = r"C:\Users\Blame\Desktop\cortexos_organized"

# New clean folders
FOLDERS = {
    "core_modules": ["neural_gatekeeper", "cortex_vectorizer", "phase_harmonics", "resonance_field", "chord_resonator",
                     "resonance_reinforcer", "swarm_resonance", "topk_sparse_resonance", "cortex_cube_nvme",
                     "knowledge_reinforcer", "lexicon_seeder", "memory_inserter", "data_ingestor", "trust_filter",
                     "cortex_inspector", "self_repair", "mirror_reflector", "symbolic_translator",
                     "execution_monitor", "mood_controller", "neuromodulation", "temporal_coherence",
                     "global_sync_manager", "neural_fabric", "resonance_monitor", "context_engine", "neuroengine"],
    "contracts": ["neural_map.json"],
    "orchestrators": ["V8", "V7", "V6", "V5", "V4", "V3", "V2", "V1"],
    "nvme_cube": ["cube_nvme_storage.dat"],
    "archive": []  # Everything else
}

# Create target folders if not exist
for folder in FOLDERS.keys():
    path = os.path.join(BASE_DIR, folder)
    os.makedirs(path, exist_ok=True)

# Walk directory and move files
for root, dirs, files in os.walk(BASE_DIR):
    for file in files:
        full_path = os.path.join(root, file)

        # Prevent moving files already in new clean folders
        if any(folder in full_path for folder in FOLDERS.keys()):
            continue

        moved = False

        # Classify files
        filename_lower = file.lower()

        # Contract files
        if filename_lower == "neural_map.json":
            shutil.move(full_path, os.path.join(BASE_DIR, "contracts", file))
            logging.info(f"Moved contract file: {file}")
            moved = True

        # NVMe Cube file
        elif filename_lower.startswith("cube_nvme") or filename_lower.endswith(".dat"):
            shutil.move(full_path, os.path.join(BASE_DIR, "nvme_cube", file))
            logging.info(f"Moved NVMe file: {file}")
            moved = True

        # Orchestrators
        elif any(ver.lower() in filename_lower for ver in FOLDERS["orchestrators"]):
            shutil.move(full_path, os.path.join(BASE_DIR, "orchestrators", file))
            logging.info(f"Moved orchestrator: {file}")
            moved = True

        # Core modules
        else:
            module_name = file.replace(".py", "").lower()
            if module_name in [mod.lower() for mod in FOLDERS["core_modules"]]:
                shutil.move(full_path, os.path.join(BASE_DIR, "core_modules", file))
                logging.info(f"Moved core module: {file}")
                moved = True

        # Archive fallback
        if not moved:
            shutil.move(full_path, os.path.join(BASE_DIR, "archive", file))
            logging.warning(f"Archived unclassified file: {file}")

logging.info("=== Cleanroom Restructure Complete ===")
