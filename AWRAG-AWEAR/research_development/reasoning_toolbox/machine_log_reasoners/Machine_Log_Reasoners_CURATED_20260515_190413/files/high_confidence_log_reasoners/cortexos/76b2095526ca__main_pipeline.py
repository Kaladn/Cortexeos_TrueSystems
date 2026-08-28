import pandas as pd
import yaml
import time
from tqdm import tqdm
import psutil
import os
from intake_autopsy import IntakeAutopsy
from lawful_event_extractor import LawfulEventExtractor
from schemacon_builder import SchemaConBuilder
from resonance_engine import ResonanceEngine
from classifier_interface import ClassifierInterface
from evaluation_wrapper import EvaluationWrapper

# Utility for lawful phase timing
def phase_timer(label, func, *args, **kwargs):
    print(f"\n[CORTEXOS] Starting {label}...")
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    print(f"[CORTEXOS] {label} completed in {elapsed:.2f} sec.")
    return result

# Utility for memory monitoring
def report_memory():
    mem = psutil.virtual_memory()
    print(f"[MEMORY USAGE] {mem.used / 1e9:.2f} GB used / {mem.total / 1e9:.2f} GB total")

# Load config (filesystem-safe)
def load_config():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    print("[CORTEXOS] Config loaded.")
    return config

# Launch pipeline
if __name__ == "__main__":
    overall_start = time.time()

    config = load_config()
    report_memory()

    # Intake Autopsy
    intake = phase_timer("Intake Autopsy", IntakeAutopsy, "data")
    phase_timer("Load Data", intake.load_data)
    phase_timer("Validate Schema", intake.validate_fields)
    phase_timer("Summarize Structure", intake.summarize_structure)
    report_memory()

    # Lawful Event Extraction for TRAINING DATA
    extractor_train = LawfulEventExtractor(intake.train, config)
    print("[CORTEXOS] Extracting lawful events for TRAIN...")
    lawful_train = extractor_train.execute_full_extraction()

    print(f"[MOTION INITIATION] Detected: {lawful_train['motion_initiation'].sum()} events (TRAIN)")
    print(f"[THERMAL CONTACT] Detected: {lawful_train['thermal_contact'].sum()} events (TRAIN)")
    print(f"[PROXIMITY CONTACT] Detected: {lawful_train['proximity_contact'].sum()} events (TRAIN)")
    report_memory()

    # SchemaCon Builder on Training Data
    schema_builder = SchemaConBuilder(lawful_train)
    schema_builder.generate_schema_fields()
    schema_builder.validate_schema_integrity()

    # Resonance Engine for Training Data
    resonance_engine_train = ResonanceEngine(lawful_train)
    clouds_train = {}
    for sequence_id, group in lawful_train.groupby("sequence_id"):
        group = group.reset_index(drop=True)
        events = group['lawful_event'].tolist()
        cloud = resonance_engine_train.generate_context_window(events)
        clouds_train[sequence_id] = cloud
    resonance_engine_train.resonance_clouds = clouds_train
    scores_train = resonance_engine_train.score_resonance_strength()

    # Train classifier on lawful cognition structure
    classifier = ClassifierInterface(scores_train, lawful_train)

    # -----------------------------------------------------
    # Lawful Inference Phase (TEST DATA ONLY)
    # -----------------------------------------------------

    # Extract lawful events for TEST DATA
    extractor_test = LawfulEventExtractor(intake.test, config)
    print("[CORTEXOS] Extracting lawful events for TEST...")
    lawful_test = extractor_test.execute_full_extraction()

    # Resonance Engine for Test
    resonance_engine_test = ResonanceEngine(lawful_test)
    clouds_test = {}
    for sequence_id, group in lawful_test.groupby("sequence_id"):
        group = group.reset_index(drop=True)
        events = group['lawful_event'].tolist()
        cloud = resonance_engine_test.generate_context_window(events)
        clouds_test[sequence_id] = cloud
    resonance_engine_test.resonance_clouds = clouds_test
    scores_test = resonance_engine_test.score_resonance_strength()

    # Attach test resonance scores to classifier
    classifier.resonance_scores = scores_test

    # Evaluation + Submission for Kaggle
    test_ids = intake.test['sequence_id'].unique()
    wrapper = EvaluationWrapper(classifier, test_ids)
    wrapper.generate_submission()

    total_time = time.time() - overall_start
    print("\n========================")
    print(f"✅ [CORTEXOS SUBMISSION COMPLETE] Total lawful cognition time: {total_time:.2f} sec.")
    report_memory()
