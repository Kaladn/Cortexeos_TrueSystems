import os
import csv
import spacy
from tqdm import tqdm

# Force CPU for spaCy (if GPU exists, disable it)
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Load spaCy English NLP model in CPU mode
print("🔄 Loading spaCy model (CPU-only)...")
nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])  # Keep it light
print("✅ spaCy model loaded!")

# Input & Output Files
INPUT_FILE = r"C:\Users\mydyi\Desktop\words.csv"
OUTPUT_FILE = r"C:\Users\mydyi\Desktop\cleaned_words.txt"

# Read CSV file line-by-line (efficient RAM usage)
word_set = set()

print(f"🔄 Streaming words from '{INPUT_FILE}' (low RAM mode)...")
with open(INPUT_FILE, "r", encoding="utf-8") as infile:
    reader = csv.reader(infile)
    next(reader, None)  # Skip header

    for row in tqdm(reader, desc="Processing Words", unit="word"):
        if len(row) < 2:
            continue  # Skip malformed rows

        word = row[1].strip().lower()  # Extract word & normalize case

        # Filtering rules (NO memory overhead)
        if (
            len(word) < 4 or  # Skip words shorter than 4 letters
            "-" in word or  # Skip hyphenated words
            any(char.isdigit() for char in word)  # Skip words with numbers
        ):
            continue

        # Check English Validity (CPU-efficient)
        doc = nlp(word)
        if doc and doc[0].has_vector and doc[0].vector_norm > 0:  # Must be English
            word_set.add(word)  # Add to deduplicated set

# Save cleaned words **efficiently**
print(f"✅ Cleaning complete. Saving {len(word_set)} words to '{OUTPUT_FILE}'...")
with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
    outfile.write("\n".join(sorted(word_set)) + "\n")

print("🎉 Done! Your optimized English word list is ready.")
