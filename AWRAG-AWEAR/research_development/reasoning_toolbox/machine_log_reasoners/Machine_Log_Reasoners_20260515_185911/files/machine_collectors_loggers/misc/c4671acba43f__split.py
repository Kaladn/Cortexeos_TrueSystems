import os
import re

# Input and output paths
INPUT_TEXT_FILE = "C:/AI SYMBOLIS WORK/output/pubmed_texts/supp2025.txt"
OUTPUT_WORDS_FILE = "C:/AI SYMBOLIS WORK/output/pubmed_texts/words_supp2025.txt"

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_WORDS_FILE), exist_ok=True)

def extract_words(input_file, output_file):
    """Extract words only from the input file and save them to a new file."""
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Extract words only (removing numbers, punctuation, and special characters)
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    
    # Save words to output file
    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(words))
    
    print(f"✅ Extracted words saved: {output_file}")

# Run the extraction
extract_words(INPUT_TEXT_FILE, OUTPUT_WORDS_FILE)
