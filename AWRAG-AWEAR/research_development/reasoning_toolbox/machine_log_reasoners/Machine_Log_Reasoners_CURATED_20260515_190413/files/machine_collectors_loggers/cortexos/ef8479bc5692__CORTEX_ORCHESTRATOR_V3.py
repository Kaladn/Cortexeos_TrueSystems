"""
CortexOS Control Kernel — Orchestrator V3: Full Execution Kernel
"""

import importlib.util
import sys
import os
import traceback
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIG ROOT ===
CORTEX_ROOT = r"C:\Users\Blame\Desktop\cortexos_organized"

# === INJECTION ARGS ===
INJECTION_ARGS = {
    "ChordResonator": {
        "chord_map_path": os.path.join(CORTEX_ROOT, "config", "neural_map.json"),
        "neuron_mapper": None
    },
    "CortexCubeNVMe": {
        "file_path": os.path.join(CORTEX_ROOT, "cube_nvme_storage.dat")
    },
    "LexiconSeeder": {
        "lexicon_path": os.path.join(CORTEX_ROOT, "config", "lexicon.json")
    }
}

# === MODULE MAP ===
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

# === UNIVERSAL IMPORT FUNCTION ===
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
        logging.error(f"Failed import {file_path} -> {class_name}: {e}")
        traceback.print_exc()
        return None

# === BOOTSTRAP LOADER ===
def bootstrap_modules():
    logging.info("=== CortexOS Orchestrator V3 Bootstrap ===")

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
            # Inject args if needed
            if module_alias in INJECTION_ARGS:
                injected_args = INJECTION_ARGS[module_alias]
                if 'neuron_mapper' in injected_args and injected_args['neuron_mapper'] is None:
                    injected_args['neuron_mapper'] = loaded_modules.get("NeuronMapper")
                instance = klass(**injected_args)
            else:
                instance = klass()

            loaded_modules[module_alias] = instance
            logging.info(f"Loaded: {module_alias}")

        except Exception as e:
            logging.error(f"Failed instantiating {module_alias}: {e}")
            traceback.print_exc()
            loaded_modules[module_alias] = None

    logging.info("=== Bootstrap Complete ===\n")

# === SIMPLE EXECUTION PIPELINE ===
def execute_pipeline():
    logging.info("=== CortexOS Execution Pipeline Start ===")

    try:
        ingestor = loaded_modules.get("DataIngestor")
        trust_filter = loaded_modules.get("TrustFilter")
        context_engine = loaded_modules.get("ContextEngine")
        phase_harmonics = loaded_modules.get("PhaseHarmonics")
        res_field = loaded_modules.get("ResonanceFieldMonitor")
        reinforcer = loaded_modules.get("ResonanceReinforcer")
        knowledge = loaded_modules.get("KnowledgeReinforcer")
        global_sync = loaded_modules.get("GlobalSyncManager")
        core_hooks = loaded_modules.get("CortexCoreHooks")

        input_data = {
            "neuron_ids": ["n1", "n2", "n3"],
            "voxel_field": {"v1": 0.5, "v2": 0.8}
        }

        if ingestor and trust_filter:
            processed = ingestor.ingest(input_data)
            processed = trust_filter.filter_data(processed)
        else:
            processed = input_data

        if context_engine and phase_harmonics and res_field:
            context = context_engine.process_context(processed)
            harmonics = phase_harmonics.initialize_harmonics(context)
            res_field.monitor_field(harmonics)

        if reinforcer:
            reinforcer.reinforce_chords(["mock_chord_A", "mock_chord_B"])

        if knowledge:
            knowledge.reinforce_knowledge(["mock_chord_A"])

        if global_sync:
            global_sync.sync_clock()

        if core_hooks:
            core_hooks.log_operation({"phase": "execution_pipeline"})

        logging.info("=== CortexOS Execution Pipeline Complete ===\n")

    except Exception as e:
        logging.error(f"Pipeline execution error: {e}")
        traceback.print_exc()

# === RUNNER ===
if __name__ == "__main__":
    bootstrap_modules()
    execute_pipeline()

    logging.info("=== CortexOS Module Summary ===")
    for name, instance in loaded_modules.items():
        status = "LOADED" if instance else "FAILED"
        print(f"{name.ljust(20)} --> {status}")
