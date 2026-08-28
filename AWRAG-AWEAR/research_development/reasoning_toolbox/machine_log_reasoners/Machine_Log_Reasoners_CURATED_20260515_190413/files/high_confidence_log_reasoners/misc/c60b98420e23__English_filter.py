import os
import json
import re
from collections import Counter

# Paths
TEXT_DIR = "C:/AI SYMBOLIS WORK/combined_texts"
OUTPUT_FILE = "C:/AI SYMBOLIS WORK/output/word_analysis.json"

# Regex pattern to extract words
WORD_PATTERN = re.compile(r"\b[a-zA-Z]+\b")

def analyze_file(file_name):
    """Analyze a single text file for word count, unique words, and frequency."""
    file_path = os.path.join(TEXT_DIR, file_name)
    
    if not file_name.endswith(".txt"):
        return None
    
    print(f"📂 Processing {file_name}...")
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().lower()
        words = WORD_PATTERN.findall(text)
        word_count = len(words)
        unique_words = set(words)
        word_freq = Counter(words)
    
    result = {
        "file": file_name,
        "total_words": word_count,
        "unique_words": len(unique_words),
        "word_frequency": word_freq.most_common(50)  # Top 50 words
    }
    
    return result

def process_single_file():
    """Run analysis on a single file from the directory."""
    files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]
    if not files:
        print("❌ No text files found in directory.")
        return
    
    file_name = files[0]  # Pick the first file
    analysis = analyze_file(file_name)
    
    if analysis:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        print(f"✅ Analysis complete! Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_single_file()
