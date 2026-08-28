import importlib.util
import logging
import os
import json
import inspect

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

logging.info("=== CortexOS Contract Enforcer Orchestrator V5 ===")

# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEURAL_MAP_FILE = os.path.join(BASE_DIR, "neural_map_updated.json")

# Load Contract Map
try:
    with open(NEURAL_MAP_FILE, 'r') as f:
        CONTRACT_MAP = json.load(f)
    logging.info("Loaded neural_map_updated.json successfully")
except Exception as e:
    logging.error(f"Failed to load neural_map_updated.json: {e}")
    CONTRACT_MAP = {}

# Auto-injected shared arguments (normalize here as we build up CortexOS full state)
GLOBAL_ARGS = {
    "vector_dimensions": 10,
    "trust_threshold": 0.85,
    "cube_shape": (64, 64, 64),
    "initial_mood": "neutral",
    "cycle_duration": 5.0,
    "global_sync_manager": None,  # dynamically assigned after GSM init
    "cortex_cube": None,
    "neuron_mapper": None,
    "bridge": None,
    "sync_manager": None,
    "resonance_monitor": None
}

# Module Patching for Path Issues
PATCH_MAP = {
    "context_engine": "phase1.context_engine",
    "cortex_vectorizer": "phase1.cortex_vectorizer",
    "neural_gatekeeper": "phase1.neural_gatekeeper",
    "neuroengine": "phase1.neuroengine",
    "phase_harmonics": "phase1.phase_harmonics",
    "resonance_field": "phase1.resonance_field",
    "chord_resonator": "phase2.chord_resonator",
    "resonance_reinforcer": "phase2.resonance_reinforcer",
    "swarm_resonance": "phase2.swarm_resonance",
    "topk_sparse_resonance": "phase2.topk_sparse_resonance",
    "cortex_cube_nvme": "phase3.cortex_cube_nvme",
    "knowledge_reinforcer": "phase3.knowledge_reinforcer",
    "lexicon_seeder": "phase3.lexicon_seeder",
    "memory_inserter": "phase3.memory_inserter",
    "cortex_core_hooks": "phase4.cortex_core_hooks",
    "data_ingestor": "phase4.data_ingestor",
    "trust_filter": "phase4.trust_filter",
    "cortex_inspector": "phase5.cortex_inspector_purified",
    "mirror_reflector": "phase5.mirror_reflector_purified",
    "self_repair": "phase5.self_repair_purified",
    "symbolic_translator": "phase5.symbolic_translator_purified",
    "mood_controller": "phase6.mood_controller_purified",
    "neuromodulation": "phase6.neuromodulation_purified",
    "global_sync_manager": "infrastructure.global_sync_manager",
    "neural_fabric": "infrastructure.neural_fabric",
    "resonance_monitor": "infrastructure.resonance_monitor",
}

MODULE_INSTANCES = {}

# Dynamic Loader & Injector
def load_module(name, class_name, constructor_args):
    path_patch = PATCH_MAP.get(name, name)
    try:
        module_path = os.path.join(BASE_DIR, *path_patch.split('.')) + ".py"
        spec = importlib.util.spec_from_file_location(name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        klass = getattr(module, class_name)

        # Reflect constructor args
        sig = inspect.signature(klass.__init__)
        kwargs = {}
        for param in list(sig.parameters.values())[1:]:
            pname = param.name
            if pname in constructor_args:
                kwargs[pname] = constructor_args[pname]
            elif pname in GLOBAL_ARGS and GLOBAL_ARGS[pname] is not None:
                kwargs[pname] = GLOBAL_ARGS[pname]
            elif param.default != inspect.Parameter.empty:
                kwargs[pname] = param.default
            else:
                kwargs[pname] = None

        instance = klass(**kwargs)
        logging.info(f"[LOADED] {name}")
        return instance
    except Exception as e:
        logging.error(f"[FAILED] {name}: {e}")
        return None

# Initialize Global Sync Manager first (forcefully because all others rely on it)
gsm_entry = CONTRACT_MAP.get("global_sync_manager", {})
GLOBAL_ARGS["global_sync_manager"] = load_module("global_sync_manager", gsm_entry.get("class", "GlobalSyncManager"), {})

# Loop through full contract map
for module_name, module_data in CONTRACT_MAP.items():
    if module_name == "global_sync_manager":
        continue  # already loaded above
    instance = load_module(module_name, module_data.get("class", ""), {})
    MODULE_INSTANCES[module_name] = instance

logging.info("=== Contract Enforcement V5 Bootstrap Complete ===")
