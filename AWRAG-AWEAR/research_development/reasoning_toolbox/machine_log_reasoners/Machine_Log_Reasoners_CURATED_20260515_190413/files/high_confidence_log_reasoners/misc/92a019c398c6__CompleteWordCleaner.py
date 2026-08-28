import os
import re
import spacy
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Paths
INPUT_DIR = r"C:\Users\mydyi\Desktop\clean_pass_final_2"  # Input folder
OUTPUT_DIR = r"C:\Users\mydyi\Desktop\clean_pass_final_3"  # Output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Regex Patterns
hyphen_pattern = re.compile(r'\b\w*-{1,}\w*\b')  # Detects words with hyphens
number_pattern = re.compile(r'\b\w*\d+\w*\b')  # Detects words with numbers
repetitive_pattern = re.compile(r'\b([a-zA-Z])\1{2,}\b')  # Words like 'aaa', 'bbb'
prefix_pattern = re.compile(r'^(aa|bb|cc|dd|ee|ff|gg|hh|ii|jj|kk|ll|mm|nn|oo|pp|qq|rr|ss|tt|uu|vv|ww|xx|yy|zz)')  # Remove bad prefixes

# Load NLP Models
print("🔄 Loading spaCy & Transformers...")
nlp = spacy.load("en_core_web_sm")
tokenizer = AutoTokenizer.from_pretrained("roberta-base")
model = AutoModelForSequenceClassification.from_pretrained("textattack/roberta-base-imdb").to("cpu")

# Get List of Files (Ensure it Only Processes One at a Time)
files = [f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))]
print(f"🔄 Processing {len(files)} files... (One at a Time)")

# Process **ONE FILE AT A TIME (Line-by-Line Processing)**
for file in tqdm(files, desc="Processing Files", unit="file"):
    input_path = os.path.join(INPUT_DIR, file)
    output_path = os.path.join(OUTPUT_DIR, file)

    with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
        for line in infile:
            word = line.strip().split()[0]  # Extract only the word (ignores frequency count)

            # Apply Filtering Rules (Skip Bad Words)
            if (
                hyphen_pattern.search(word) or
                number_pattern.search(word) or
                repetitive_pattern.search(word) or
                prefix_pattern.search(word)
            ):
                continue  # Skip junk words

            # Check If English Using spaCy
            doc = nlp(word)
            if not doc.has_vector or doc.vector_norm == 0:
                continue  # Drop if no valid vector (likely non-English)

            # Use Transformer Model for Extra Check
            inputs = tokenizer(word, return_tensors="pt", truncation=True, padding=True).to("cpu")
            outputs = model(**inputs)
            prediction = torch.argmax(outputs.logits, dim=1).item()
            if prediction != 1:
                continue  # Drop if RoBERTa says it's non-English

            outfile.write(word + "\n")  # Write directly to file (No RAM Overload)

print(f"🎉 Done! Cleaned words are saved in '{OUTPUT_DIR}'.")
