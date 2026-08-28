import time
from tqdm import tqdm
import os

from starlink_intake_adapter import StarlinkIntakeAdapter
from lawful_event_extractor import LawfulEventExtractor
from resonance_engine import ResonanceEngine
from reporting_layer import ReportingLayer

# === CONFIGURATION ===

DATA_FOLDER_PATH = r'C:\Users\Blame\cortexos_kaggle_bfrb_project\data'
WINDOW_SIZE_MINUTES = 5

# === PERFORMANCE AUDIT START ===
total_start = time.perf_counter()

# === STAGE 1: AUTOMATIC FILE SELECTION ===
print("[CortexOS] Scanning for latest dataset...")
files = [f for f in os.listdir(DATA_FOLDER_PATH) if f.endswith('.csv')]
latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(DATA_FOLDER_PATH, x)))
DATA_FILE_PATH = os.path.join(DATA_FOLDER_PATH, latest_file)
print(f"[CortexOS] Using dataset: {latest_file}")

# === STAGE 2: INGESTION ===
ingest_start = time.perf_counter()
print("[CortexOS] Loading dataset...")
intake = StarlinkIntakeAdapter(DATA_FILE_PATH)
intake.load_data()
intake.window_slicer(window_minutes=WINDOW_SIZE_MINUTES)
lawful_events = intake.lawful_records()
print(f"[CortexOS] Total lawful event windows extracted: {len(lawful_events)}")
ingest_end = time.perf_counter()

# === STAGE 3: LAWFUL EVENT EXTRACTION ===
parse_start = time.perf_counter()
print("[CortexOS] Extracting lawful cognition features...")
event_extractor = LawfulEventExtractor()
parsed_events = [event_extractor.extract(event) for event in tqdm(lawful_events, desc="Lawful Event Extraction")]
print(f"[CortexOS] Total events parsed for resonance: {len(parsed_events)}")
parse_end = time.perf_counter()

# === STAGE 4: RESONANCE ANALYSIS ===
resonance_start = time.perf_counter()
print("[CortexOS] Building resonance proximity chains...")
schema_data = intake.schema_map()
resonance_engine = ResonanceEngine(schema_data=schema_data)
resonance_output = resonance_engine.process(parsed_events)
resonance_end = time.perf_counter()

# === STAGE 5: REPORTING & QUERY LAYER ===
report_start = time.perf_counter()
report = ReportingLayer(resonance_output)
report.summary()
report.sovereign_query_summary()
report.plot_query_summary()
report.export_to_json()
report.plot_chain_strength()
report_end = time.perf_counter()

# === PERFORMANCE AUDIT END ===
total_end = time.perf_counter()

print("\n=== CORTEXOS TIMING REPORT ===")
print(f"Ingestion time: {ingest_end - ingest_start:.2f} sec")
print(f"Parsing time: {parse_end - parse_start:.2f} sec")
print(f"Resonance processing time: {resonance_end - resonance_start:.2f} sec")
print(f"Reporting time: {report_end - report_start:.2f} sec")
print(f"Total lawful cognition time: {total_end - total_start:.2f} sec")