import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import time
import numpy as np
import glob
import json
from tqdm import tqdm
from collections import deque

from CernIntakeAdapter import CernIntakeAdapter  # Dynamic import
from lawful_event_extractor import LawfulEventExtractor    # To be replaced
from resonance_engine import ResonanceEngine              # To be replaced
from reporting_layer import ReportingLayer                # To be replaced

# === CONFIGURATION ===
DATA_DIR = r"C:\Users\Blame\Desktop\CERN DATA"
WINDOW_SIZE_MINUTES = 5  # Adjust for event windows if needed
LOG_FILE = "cortexos_atlas_pipeline.log"
BATCH_SIZE = 10000  # Process in batches for memory efficiency

# === PERFORMANCE AUDIT START ===
total_start = time.perf_counter()

# === STAGE 1: INGESTION ===
ingest_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Loading ATLAS voxelized shower dataset...\n")
intake = CernIntakeAdapter(DATA_DIR)  # Use directory instead of file list
intake.load_data()  # Handles multiple CSVs
intake.window_slicer(window_minutes=WINDOW_SIZE_MINUTES)  # Optional, adjust logic
lawful_events = intake.lawful_records()  # Define "lawful" for particle events
total_events = intake.get_total_events()  # Get total from adapter
with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Total lawful event windows extracted: {total_events}\n")
ingest_end = time.perf_counter()

# === STAGE 2: LAWFUL EVENT EXTRACTION ===
parse_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Extracting lawful cognition features...\n")
event_extractor = LawfulEventExtractor()  # Adapt for voxel energy
parsed_events = []

with tqdm(total=total_events, desc="Lawful Event Extraction", unit="events") as pbar:
    for i in range(0, total_events, BATCH_SIZE):
        batch = lawful_events[i:i + BATCH_SIZE]
        for event in batch:
            parsed = event_extractor.extract(event)  # Extract voxel energies
            parsed_events.append(parsed)
            pbar.update(1)
        if i % 100000 == 0:  # Log every 100,000 events
            with open(LOG_FILE, "a") as log:
                log.write(f"[CortexOS] Processed {i} events\n")

with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Total events parsed for resonance: {len(parsed_events)}\n")
parse_end = time.perf_counter()

# === STAGE 3: RESONANCE ANALYSIS ===
resonance_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Building resonance proximity chains...\n")
schema_data = intake.schema_map()  # Adapt for voxel schema from binning.xml
resonance_engine = ResonanceEngine(schema_data=schema_data)
resonance_output = resonance_engine.process(parsed_events)
resonance_end = time.perf_counter()

# === STAGE 4: REPORTING & QUERY LAYER ===
report_start = time.perf_counter()
report = ReportingLayer(resonance_output)
report.summary()
report.sovereign_query_summary()
report.plot_query_summary()
report.export_to_json()
report.plot_chain_strength()
report_end = time.perf_counter()

# === VOXEL ENERGY JITTER CALCULATION ===
def calculate_voxel_energy_jitter(data, window=5):
    energies = [np.mean([v.get("energy", 0) for v in event.values() if isinstance(v, dict) and "energy" in v])
                for event in data if any(isinstance(v, dict) and "energy" in v for v in event.values())]
    if len(energies) < window:
        return 0
    jitter = deque(maxlen=window)
    adjusted_jitter = []

    for i in range(len(energies) - window + 1):
        window_data = energies[i:i + window]
        jitter.append(np.std(window_data))
        # Use file index (0-14) as layer proxy from 15 CSV files
        layer_impact = min(1.0, max(0.0, (i % 15 - 7.5) / 7.5))  # Normalize across 15 layers
        adjusted_jitter.append(jitter[-1] * (1 - layer_impact))
    return np.mean(adjusted_jitter) if adjusted_jitter else 0

jitter_value = calculate_voxel_energy_jitter(parsed_events)
with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Voxel Energy Jitter: {jitter_value:.2f}\n")

# === TIMING REPORT ===
with open(LOG_FILE, "a") as log:
    log.write("\n=== CORTEXOS TIMING REPORT ===\n")
    log.write(f"Ingestion time: {ingest_end - ingest_start:.2f} sec\n")
    log.write(f"Parsing time: {parse_end - parse_start:.2f} sec\n")
    log.write(f"Resonance processing time: {resonance_end - resonance_start:.2f} sec\n")
    log.write(f"Reporting time: {report_end - report_start:.2f} sec\n")
    log.write(f"Total lawful cognition time: {total_end - total_start:.2f} sec\n")

# === PERFORMANCE AUDIT END ===
total_end = time.perf_counter()