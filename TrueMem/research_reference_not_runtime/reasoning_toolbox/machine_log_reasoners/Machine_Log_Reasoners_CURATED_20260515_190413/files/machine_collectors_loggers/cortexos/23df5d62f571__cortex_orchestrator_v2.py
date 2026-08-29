"""
CortexOS Control Kernel — Bootstrapper V2: Loader + Control Injection
"""

import importlib.util
import sys
import os
import traceback
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIG: Your actual codebase root ===
CORTEX_ROOT = r"C:\Users\Blame\Desktop\cortexos_organized"

# === AUTO-INJECTED ARGUMENTS PER MODULE ===
INJECTION_ARGS = {
    "ChordResonator": {
        "chord_map_path": os.path.join(CORTEX_ROOT, "config", "neural_map.json"),
        "neuron_mapper": None  # Placeholder for neuron_mapper instance injection
    },
    "CortexCubeNVMe": {
        "file_path": os.path.join(CORTEX_ROOT, "cube_nvme_storage.dat")
    },
    "LexiconSeeder": {
        "lexicon_path": os.path.join(CORTEX_ROOT, "config", "lexicon.json")
    }
}

# === MODULE MAP: {ClassName: (RelativeFilePath, ClassNameInFile)} ===
MODULES = {
    "DataIngestor": ("data_ingestor.py", "DataIngestor"),
    "TrustFilter": ("trust_filter.py", "TrustFilter"),
    "NeuronMapper": ("CORTEXOS MD files\\neuron_mapper.py", "NeuronMapper"),
    "ContextEngine": ("context_engine.py", "ContextEngine"),
    "PhaseHarmonics": ("phase_harmonics.py", "PhaseHarmonics"),
    "ResonanceFieldMonitor": ("resonance_field.py", "ResonanceFieldMonitor"),
    "ChordResonator": ("chord_resonator.py", "ChordResonator"),
    "ResonanceReinforcer": ("resonance_reinforcer.py", "ResonanceReinforcer"),
    "SwarmResonance": ("swarm_resonance.py", "SwarmResonance"),
    "TopKSparseResonance": ("topk_sparse_resonance.py", "TopKSparseResonance"),
    "CortexCubeNVMe": ("cortex_cube_nvme.py", "CortexCubeNVMe"),
    "MemoryInserter": ("memory_inserter.py", "MemoryInserter"),
    "KnowledgeReinforcer": ("knowledge_reinforcer.py", "KnowledgeReinforcer"),
    "LexiconSeeder": ("lexicon_seeder.py", "LexiconSeeder"),
    "MoodController": ("phase6\\mood_controller.py", "MoodController"),
    "Neuromodulator": ("phase6\\neuromodulation.py", "Neuromodulator"),
    "GlobalSyncManager": ("global_sync_manager.py", "GlobalSyncManager"),
    "CortexCoreHooks": ("cortex_core_hooks.py", "CortexCoreHooks")
}

# === REGISTRY ===
loaded_modules = {}

# === UNIVERSAL DYNAMIC IMPORT FUNCTION ===
def dynamic_import(file_path, class_name):
    try:
        spec = importlib.util.spec_from_file_location(class_name, file_path)
        if spec is None:
            raise ImportError(f"Cannot create spec for {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[class_name] = module
        spec.loader.exec_module(module)
        return getattr(module, class_name)
    except Exception as e:
        logging.error(f"Failed to import {file_path} -> {class_name}: {e}")
        traceback.print_exc()
        return None

# === BOOTSTRAP LOADER ===
def bootstrap_modules():
    logging.info("=== CortexOS Bootstrapper V2 ===")

    for module_alias, (relative_path, class_name) in MODULES.items():
        full_path = os.path.join(CORTEX_ROOT, relative_path)
        if not os.path.exists(full_path):
            logging.warning(f"Module file not found: {full_path}")
            loaded_modules[module_alias] = None
            continue

        klass = dynamic_import(full_path, class_name)
        if klass is None:
            loaded_modules[module_alias] = None
            continue

        try:
            # Handle injected constructor arguments if needed
            if module_alias in INJECTION_ARGS:
                injected_args = INJECTION_ARGS[module_alias]
                # Inject NeuronMapper if required
                if 'neuron_mapper' in injected_args and injected_args['neuron_mapper'] is None:
                    injected_args['neuron_mapper'] = loaded_modules.get("NeuronMapper")
                instance = klass(**injected_args)
            else:
                instance = klass()

            loaded_modules[module_alias] = instance
            logging.info(f"Loaded: {module_alias} [{class_name}]")

        except Exception as e:
            logging.error(f"Failed to instantiate {module_alias}: {e}")
            traceback.print_exc()
            loaded_modules[module_alias] = None

    logging.info("=== Bootstrap Complete ===\n")

# === EXECUTION ===
if __name__ == "__main__":
    bootstrap_modules()

    logging.info("=== CortexOS Operational Modules ===")
    for name, instance in loaded_modules.items():
        status = "LOADED" if instance else "FAILED"
        print(f"{name.ljust(20)} --> {status}")
