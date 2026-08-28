import os
import json
import re
from collections import Counter

# Paths
TEXT_DIR = "C:/AI SYMBOLIS WORK/combined_texts"
OUTPUT_DIR = "C:/AI SYMBOLIS WORK/output/word_analysis"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex pattern to extract words
WORD_PATTERN = re.compile(r"\b[a-zA-Z]+\b")

def analyze_file(file_name):
    """Analyze a single text file for word count, unique words, and frequency."""
    file_path = os.path.join(TEXT_DIR, file_name)
    output_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file_name)[0]}.json")
    
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
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Analysis complete! Results saved to {output_path}")

def process_all_files():
    """Run analysis on all files in the directory."""
    files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]
    if not files:
        print("❌ No text files found in directory.")
        return
    
    for file_name in files:
        analyze_file(file_name)

if __name__ == "__main__":
    process_all_files()
