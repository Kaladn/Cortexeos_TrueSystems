import os
import re
import json
import spacy
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Paths
INPUT_FILE = r"C:\Users\mydyi\Desktop\word_frequencies.txt"
OUTPUT_DIR = r"C:\Users\mydyi\Desktop\clean_pass_final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex Patterns
hyphen_pattern = re.compile(r'\b\w*-{1,}\w*\b')  # Detects words with hyphens
number_pattern = re.compile(r'\b\w*\d+\w*\b')  # Detects words with numbers
repetitive_pattern = re.compile(r'\b([a-zA-Z])\1{2,}\b')  # Words like 'aaa', 'bbbb'
prefix_pattern = re.compile(r'^(aa|bb|cc|dd|ee|ff|gg|hh|ii|jj|kk|ll|mm|nn|oo|pp|qq|rr|ss|tt|uu|vv|ww|xx|yy|zz)')  # Remove nonsense prefixes

# NLP Models
print("🔄 Loading spaCy & Transformers...")
nlp = spacy.load("en_core_web_sm")
tokenizer = AutoTokenizer.from_pretrained("roberta-base")
model = AutoModelForSequenceClassification.from_pretrained("textattack/roberta-base-imdb").to("cpu")

# Load & Filter Words
cleaned_words = {}
total_words = 0
print(f"🔄 Streaming words from '{INPUT_FILE}'...")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in tqdm(f, desc="Processing Words", unit="word"):
        parts = line.strip().split()
        if len(parts) < 2:
            continue  # Skip bad lines
        
        word, count = " ".join(parts[:-1]), parts[-1]
        if not count.isdigit():
            continue  # Skip lines without proper counts

        count = int(count)
        if count < 4:
            continue  # Skip rare words

        # Apply Filtering Rules
        if (
            hyphen_pattern.search(word) or
            number_pattern.search(word) or
            repetitive_pattern.search(word) or
            prefix_pattern.search(word)
        ):
            continue  # Remove junk words

        # Check Language Validity
        doc = nlp(word)
        if not doc.has_vector or doc.vector_norm == 0:
            continue  # Drop if no valid vector (likely non-English)

        # Run Transformer Model for Additional Check
        inputs = tokenizer(word, return_tensors="pt", truncation=True, padding=True).to("cpu")
        outputs = model(**inputs)
        prediction = torch.argmax(outputs.logits, dim=1).item()
        if prediction != 1:
            continue  # Drop non-English words

        # Determine Segment Key (for structured storage)
        segment_key = word[:2] if len(word) > 1 else word
        if segment_key not in cleaned_words:
            cleaned_words[segment_key] = []
        
        cleaned_words[segment_key].append(word)
        total_words += 1

print(f"✅ Cleaning complete! {total_words} words remaining.")

# Save Cleaned & Segmented Words
print("🔄 Saving cleaned words...")
for segment, words in tqdm(cleaned_words.items(), desc="Saving Segments", unit="segment"):
    output_path = os.path.join(OUTPUT_DIR, f"segment_{segment}.txt")
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(sorted(words)) + "\n")

print(f"🎉 Done! Cleaned words are saved in '{OUTPUT_DIR}'.")
