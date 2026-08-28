import os
import json
import re
from tqdm import tqdm
from collections import defaultdict

# === CONFIGURATION ===
RAW_FILE = "E:\split_conversations\pretrain_ready.txt"  # Full preprocessed chat log
OUTPUT_DIR = "ml_packages"
CHUNK_SIZE = 100  # Number of lines per package

# Pattern definitions
CODE_BLOCK = re.compile(r"```[a-zA-Z]*[\s\S]*?```", re.MULTILINE)
SIM_RESULT = re.compile(r"(simulation result|output|log|trace|result:)\s*.*", re.IGNORECASE)
KEYWORDS = [
    "security", "deployment", "roundtable", "training", "surveillance",
    "symbol", "policy", "vote", "command", "emergency", "injection",
    "defense", "AI role", "module", "inference", "sub-context", "thread"
]

# === HELPER FUNCTIONS ===
def safe_filename(name):
    return re.sub(r'[^\w\-_]', '_', name.strip().lower())[:48]

def extract_blocks(lines):
    packages = defaultdict(list)
    current_chunk = []
    current_tags = set()

    for idx, line in enumerate(tqdm(lines, desc="Scanning for blocks")):
        if any(kw in line.lower() for kw in KEYWORDS):
            current_tags.update(kw for kw in KEYWORDS if kw in line.lower())
        if CODE_BLOCK.search(line):
            current_tags.add("code")
        if SIM_RESULT.search(line):
            current_tags.add("simulation")

        current_chunk.append(line.strip())

        if len(current_chunk) >= CHUNK_SIZE:
            key = "+".join(sorted(current_tags)) or "general"
            packages[key].append("\n".join(current_chunk))
            current_chunk = []
            current_tags = set()

    # Handle any remaining lines
    if current_chunk:
        key = "+".join(sorted(current_tags)) or "general"
        packages[key].append("\n".join(current_chunk))

    return packages

# === MAIN PIPELINE ===
def extract_ml_packages():
    if not os.path.exists(RAW_FILE):
        raise FileNotFoundError(f"Input file not found: {RAW_FILE}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    packages = extract_blocks(lines)

    for tag_group, chunks in packages.items():
        fname = safe_filename(tag_group)
        path = os.path.join(OUTPUT_DIR, f"pkg__{fname}.txt")
        with open(path, 'w', encoding='utf-8') as out:
            out.write("\n\n---\n\n".join(chunks))

    print(f"\n✅ Extracted {len(packages)} ML training packages to: {OUTPUT_DIR}\n")

if __name__ == '__main__':
    extract_ml_packages()