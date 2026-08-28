import json
import os

# Paths
SYMBOLIS_DICT_FILE = "C:/AI SYMBOLIS WORK/data_scraping/symbolis_dict.json"
INPUT_FILE = "C:/Users/mydyi/OneDrive/Documents/Desktop/epub/5/pg5.txt"
OUTPUT_FILE = "C:/AI SYMBOLIS WORK/output/pg5_symbolis.txt"

# Load Symbolis Dictionary
print("🔄 Loading Symbolis Dictionary...")
with open(SYMBOLIS_DICT_FILE, "r", encoding="utf-8") as f:
    symbolis_dict = json.load(f)

# Read input text file
print(f"📖 Reading input file: {INPUT_FILE}...")
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    text = f.read()

# Convert words
print("🔄 Converting words to Symbolis format...")
words = text.split()
converted_words = [symbolis_dict.get(word.lower(), word) for word in words]

# Save converted text
print(f"💾 Saving converted file to: {OUTPUT_FILE}...")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(" ".join(converted_words))

print("✅ Conversion complete!")


