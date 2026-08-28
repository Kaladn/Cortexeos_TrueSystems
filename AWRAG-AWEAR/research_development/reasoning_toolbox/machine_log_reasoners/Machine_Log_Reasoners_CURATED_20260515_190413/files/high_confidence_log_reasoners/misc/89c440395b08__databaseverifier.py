import os
import re
import requests
from tqdm import tqdm

# File Paths
CLEANED_WORDS_DIR = "A:/WIKI SCRAPED/WORD_ANALYSIS/FINAL_ALPHA"  # Alphabetized clean dataset
MERGED_TERMS_FILE = "A:/WIKI SCRAPED/WORD_ANALYSIS/merged_terms.txt"

# Reference Dictionaries (Load from external sources if available)
medical_terms = set()
scientific_terms = set()
historical_terms = set()
educational_terms = set()

# Load External Medical Dictionary (Example: MeSH)
MESH_FILE = "A:/WIKI SCRAPED/EXTRACTED/mesh_english_words.txt"
if os.path.exists(MESH_FILE):
    with open(MESH_FILE, "r", encoding="utf-8") as f:
        medical_terms.update(line.strip().lower() for line in f)

# Load Other Scientific, Historical, and Educational Data
EXTERNAL_SOURCES = {
    "scientific": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
    "historical": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
    "educational": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english.txt"
}

for category, url in EXTERNAL_SOURCES.items():
    response = requests.get(url)
    if response.status_code == 200:
        words = set(response.text.split())
        if category == "scientific":
            scientific_terms.update(words)
        elif category == "historical":
            historical_terms.update(words)
        elif category == "educational":
            educational_terms.update(words)

# Word Classification Counters
merged_words = set()

# Process Cleaned Words from A-Z Directory
for letter_file in tqdm(os.listdir(CLEANED_WORDS_DIR), desc="📂 Processing Word Files"):
    if not letter_file.endswith(".txt"):  # Skip non-txt files
        continue
    file_path = os.path.join(CLEANED_WORDS_DIR, letter_file)
    with open(file_path, "r", encoding="utf-8") as f:
        for word in f:
            word = word.strip().lower()
            if word and word.isalpha():  # Only consider pure alphabetic words
                merged_words.add(word)

# Add missing words from external sources
merged_words.update(medical_terms)
merged_words.update(scientific_terms)
merged_words.update(historical_terms)
merged_words.update(educational_terms)

# Save Merged Data
with open(MERGED_TERMS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(merged_words)))

# Summary Report
print("✅ Cross-Reference and Merge Complete!")
print(f"📊 Total Unique Words: {len(merged_words)}")
