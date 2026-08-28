
# cortexos_supervisor.py
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
from phase3.cortex_cube_nvme import CortexCubeNVME
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

class CortexOSSupervisor:
    def __init__(self):
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

        # Phase 3 Init
        self.cube_storage = CortexCubeNVME()
        self.memory_inserter = MemoryInserter(self.cube_storage)
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
        self.repair_rules = None  # Assume lawful rules externally loaded later
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
        print("Cube operational. Awaiting lawful ingestion.")

