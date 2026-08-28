import os
import re
import spacy
import tqdm
import glob
from collections import Counter

from bs4 import BeautifulSoup

# Load SpaCy NLP Model
nlp = spacy.load("en_core_web_sm")
nlp.max_length = 50000000 # Increase processing limit

# Directories
INPUT_DIR = "/home/lee/Desktop/First Word Alpha Parsed Data - Copy"
OUTPUT_DIR = "/home/lee/Desktop/Lexicon_Data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PURE_WORDS_FILE = os.path.join(OUTPUT_DIR, "Unique_Words_Pure.txt")
WORDS_WITH_COUNTS_FILE = os.path.join(OUTPUT_DIR, "Unique_Words_With_Counts.txt")
CONTEXTUAL_FILE = os.path.join(OUTPUT_DIR, "Word_Context_Before_After.txt")

# Allowed file extensions
ALLOWED_EXTENSIONS = {".txt", ".html", ".xml", ".json"}

def extract_words_from_text(text):
    """Tokenizes text, removes punctuation, and returns cleaned words"""
    text = re.sub(r'[^a-zA-Z\s]', '', text) # Remove special characters & numbers
    doc = nlp(text.lower()) # Process text with SpaCy
    words = [token.text for token in doc if token.is_alpha] # Keep only words
    return words

def read_file(file_path):
    """Reads text from multiple file types, handling encoding issues."""
    try:
        ext = os.path.splitext(file_path)[-1].lower()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
            # Process HTML/XML files
            if ext in {".html", ".xml"}:
                soup = BeautifulSoup(content, "html.parser")
                content = soup.get_text(separator=" ")

            return content
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return ""

def process_text_files():
    """Processes text files, extracts words, and builds unique lists"""
    word_counter = Counter()
    context_data = []

    file_list = glob.glob(f"{INPUT_DIR}/*") # Get all files
    file_list = [f for f in file_list if os.path.splitext(f)[-1].lower() in ALLOWED_EXTENSIONS]

    print(f"📂 Processing {len(file_list)} files...")

    for file_path in tqdm.tqdm(file_list, desc="Processing Files", unit="file"):
        text = read_file(file_path)
        
        if text:
            words = extract_words_from_text(text)
            word_counter.update(words) # Count occurrences
            
            # Store context: word before & after
            for i in range(1, len(words) - 1):
                context_data.append(f"{words[i-1]} {words[i]} {words[i+1]}")

    # Save results
    save_results(word_counter, context_data)

def save_results(word_counter, context_data):
    """Saves processed data to output files"""
    sorted_words = sorted(word_counter.items())

    # Save pure words
    with open(PURE_WORDS_FILE, "w", encoding="utf-8") as f:
        for word, _ in sorted_words:
            f.write(f"{word}\n")

    # Save words with counts
    with open(WORDS_WITH_COUNTS_FILE, "w", encoding="utf-8") as f:
        for word, count in sorted_words:
            f.write(f"{word} {count}\n")

    # Save contextual data
    with open(CONTEXTUAL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(context_data))

    print(f"\n✅ Processing Completed! Total Words: {len(sorted_words)}")
    print(f"🔹 Pure words saved to: {PURE_WORDS_FILE}")
    print(f"🔹 Words with counts saved to: {WORDS_WITH_COUNTS_FILE}")
    print(f"🔹 Word context saved to: {CONTEXTUAL_FILE}")

if __name__ == "__main__":
    process_text_files()