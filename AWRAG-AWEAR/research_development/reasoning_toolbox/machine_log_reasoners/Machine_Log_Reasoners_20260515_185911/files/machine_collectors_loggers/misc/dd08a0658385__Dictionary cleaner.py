import os
import pandas as pd
from collections import Counter

# Ask user for the directory
TEXT_DIR = input("📂 Enter the directory containing text files: ").strip()

# Check if the directory exists
if not os.path.isdir(TEXT_DIR):
    print(f"❌ Directory does not exist: {TEXT_DIR}")
    input("🔴 Press ENTER to exit.")
    exit(1)

# Scan for .txt files recursively
text_files = [os.path.join(root, f) 
              for root, _, files in os.walk(TEXT_DIR) 
              for f in files if f.endswith(".txt")]

if not text_files:
    print("❌ No text files found.")
    input("🔴 Press ENTER to exit.")
    exit(1)

print(f"✅ Found {len(text_files)} text files. Processing...")

# Count words
word_counts = Counter()
for file in text_files:
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            words = [word.lower() for word in line.split() if word.isalpha()]
            word_counts.update(words)

if not word_counts:
    print("⚠️ No words found.")
    input("🔴 Press ENTER to exit.")
    exit(1)

# Save to Excel
OUTPUT_FILE = os.path.join(TEXT_DIR, "word_frequencies.xlsx")
df = pd.DataFrame(word_counts.items(), columns=["Word", "Count"]).sort_values(by="Count", ascending=False)
df.to_excel(OUTPUT_FILE, index=False)

print(f"✅ Results saved to: {OUTPUT_FILE}")
input("✅ Press ENTER to exit.")  
