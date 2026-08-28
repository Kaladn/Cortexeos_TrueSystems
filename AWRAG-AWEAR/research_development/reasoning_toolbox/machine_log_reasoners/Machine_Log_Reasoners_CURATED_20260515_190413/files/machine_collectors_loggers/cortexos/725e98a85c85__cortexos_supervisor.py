# cortexos_supervisor.py
# === CortexOS Sovereign Bootstrap Header ===
import sys
import os

# Auto-detect CortexOS root directory
CORTEXOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Prepend root to sys.path for lawful module resolution
if CORTEXOS_ROOT not in sys.path:
    sys.path.insert(0, CORTEXOS_ROOT)

print(f"[BOOTSTRAP] CortexOS root path locked: {CORTEXOS_ROOT}")
# === End Bootstrap ===

from phase1.neuroengine import NeuroEngine
from phase1.resonance_field import ResonanceField
from phase1.phase_harmonics import PhaseHarmonics
from phase1.cortex_vectorizer import CortexVectorizer
from phase1.neural_gatekeeper import NeuralGatekeeper
from phase1.context_engine import ContextEngine

from phase2.swarm_resonance import SwarmResonance
from phase2.resonance_reinforcer import ResonanceReinforcer
from phase2.topk_sparse_resonance import TopKSparseResonance
from phase2.chord_resonator import ChordResonator

from phase3.knowledge_reinforcer import KnowledgeReinforcer
from phase3.memory_inserter import MemoryInserter
from phase3.lexicon_seeder import LexiconSeeder

from phase4.data_ingestor import DataIngestor
from phase4.trust_filter import TrustFilter
from phase4.cortex_core_hooks import CortexCoreHooks

from phase5.cortex_inspector import CortexInspector
from phase5.self_repair import SelfRepair
from phase5.mirror_reflector import MirrorReflector
from phase5.symbolic_translator import SymbolicTranslator

from phase6.mood_controller import MoodController
from phase6.neuromodulation import Neuromodulation

from infrastructure.global_sync_manager import GlobalSyncManager
from infrastructure.neural_fabric import NeuralFabric
from infrastructure.resonance_monitor import ResonanceMonitor

# 🔧 NVMe Cube + Contract Ledger
from infrastructure.cortex_cube_nvme import CortexCubeNVME
from infrastructure.neurogrid_contract_manager import NeurogridContractManager

class CortexOSSupervisor:
    def __init__(self):
        # 🔒 NVMe Hardware Binding
        print("[SUPERVISOR] NVMe binding sequence starting...")
        self.cube_storage = CortexCubeNVME()
        self.cube_storage.open()
        self.cube_storage.verify_signature()
        self.cube_storage.close()
        print("[SUPERVISOR] NVMe interface verified.\n")

        # 🔒 Neurogrid Contract Ledger Loading
        print("[SUPERVISOR] Loading Neurogrid Contract Manager...")
        self.contract_manager = NeurogridContractManager()
        self.contract_manager.open_device()
        self.contract_manager.load_contract_from_device()
        self.contract_manager.close_device()
        print("[SUPERVISOR] Neurogrid Contract Ledger loaded.\n")

        # Phase 1 Init
        self.vectorizer = CortexVectorizer()
        self.gatekeeper = NeuralGatekeeper()
        self.context_engine = ContextEngine()
        self.resonance_field = ResonanceField()
        self.neuroengine = NeuroEngine(self.resonance_field, self.context_engine, self.gatekeeper)
        self.phase_harmonics = PhaseHarmonics()

        # Phase 2 Init
        self.swarm_resonance = SwarmResonance()
        self.reinforcer = ResonanceReinforcer()
        self.topk = TopKSparseResonance()
        self.chord_resonator = ChordResonator()

        # Phase 3 Init (MemoryInserter now legally bound to Contract Manager)
        self.memory_inserter = MemoryInserter(self.cube_storage, self.contract_manager)
        self.knowledge_reinforcer = KnowledgeReinforcer()
        self.lexicon_seeder = LexiconSeeder()

        # Phase 4 Init
        allowed_keys = ["vector", "metadata"]
        self.trust_filter = TrustFilter(allowed_keys)
        self.ingestion_queue = []
        self.data_ingestor = DataIngestor(self.trust_filter, self.ingestion_queue)
        self.core_hooks = CortexCoreHooks(self.neuroengine, self.memory_inserter, self.knowledge_reinforcer)

        # Phase 5 Init
        self.inspector = CortexInspector(self.resonance_field, self.cube_storage)
        self.repair_rules = None
        self.self_repair = SelfRepair(self.inspector, self.repair_rules)
        self.reflector = MirrorReflector(self)
        self.symbolic_translator = SymbolicTranslator()

        # Phase 6 Init
        self.mood_controller = MoodController()
        self.neuromodulation = Neuromodulation()

        # Infrastructure Init
        self.sync_manager = GlobalSyncManager()
        self.neural_fabric = NeuralFabric()
        self.resonance_monitor = ResonanceMonitor(self.resonance_field)

    def lawful_ignite(self):
        print("CortexOS Sovereign Ignition: ONLINE")
        print("Cube operational. Neurogrid contract loaded. Awaiting lawful ingestion.")

