import time
import numpy as np
from collections import deque
import json

from starlink_intake_adapter import StarlinkIntakeAdapter
from lawful_event_extractor import LawfulEventExtractor
from resonance_engine import ResonanceEngine
from reporting_layer import ReportingLayer

# === CONFIGURATION ===
STARLINK_FILE_PATH = r'C:\Users\Blame\Desktop\cortexos_kaggle_bfrb_project (2)\cortexos_kaggle_bfrb_project\data\starlink.csv'
WINDOW_SIZE_MINUTES = 5
LOG_FILE = "cortexos_pipeline.log"

# === PERFORMANCE AUDIT START ===
total_start = time.perf_counter()

# === STAGE 1: INGESTION ===
ingest_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Loading Starlink sovereign dataset...\n")
intake = StarlinkIntakeAdapter(STARLINK_FILE_PATH)
intake.load_data()
intake.window_slicer(window_minutes=WINDOW_SIZE_MINUTES)
lawful_events = intake.lawful_records()
with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Total lawful event windows extracted: {len(lawful_events)}\n")
ingest_end = time.perf_counter()

# === STAGE 2: LAWFUL EVENT EXTRACTION ===
parse_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Extracting lawful cognition features...\n")
event_extractor = LawfulEventExtractor()
parsed_events = []

for event in lawful_events:
    parsed = event_extractor.extract(event)
    parsed_events.append(parsed)

with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Total events parsed for resonance: {len(parsed_events)}\n")
parse_end = time.perf_counter()

# === STAGE 3: RESONANCE ANALYSIS ===
resonance_start = time.perf_counter()
with open(LOG_FILE, "a") as log:
    log.write("[CortexOS] Building resonance proximity chains...\n")
schema_data = intake.schema_map()
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

# === ELEVATION-ADJUSTED JITTER CALCULATION ===
def calculate_elevation_adjusted_jitter(data, window=5):
    latencies = [event.get("latency_loss_index", 0) for event in data if "latency_loss_index" in event]
    elevations = [event.get("elevation_deg", 70) for event in data if "elevation_deg" in event]
    if len(latencies) < window or len(elevations) < window:
        return 0
    jitter = deque(maxlen=window)
    adjusted_jitter = []

    for i in range(len(latencies) - window + 1):
        window_data = latencies[i:i + window]
        jitter.append(np.std(window_data))
        elevation_impact = min(1.0, max(0.0, (elevations[i + window//2] - 70) / 10))
        adjusted_jitter.append(jitter[-1] * (1 - elevation_impact))
    return np.mean(adjusted_jitter) if adjusted_jitter else 0

jitter_value = calculate_elevation_adjusted_jitter(parsed_events)
with open(LOG_FILE, "a") as log:
    log.write(f"[CortexOS] Elevation-Adjusted Jitter: {jitter_value:.2f}\n")

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