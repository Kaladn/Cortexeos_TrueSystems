import os
import json
import multiprocessing
import fasttext
from tqdm import tqdm
from collections import Counter

# Paths
INPUT_FILES = ["data/mesh_words.txt", "data/wiki_words.txt", "data/scientific_terms.txt"]
DICTIONARY_FILE = "data/master_dictionary.json"

# Load FastText for language detection
fasttext.util.download_model('en', if_exists='ignore')
model = fasttext.load_model("cc.en.300.bin")

def is_english(word):
    """Checks if a word is English using FastText"""
    return model.predict(word)[0][0] == "__label__en"

def process_file(file_path):
    """Extracts words, filters out non-English, and returns cleaned set"""
    words = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word and is_english(word):
                words.add(word)
    return words

def build_lexicon():
    """Processes input sources and merges dictionaries"""
    all_words = set()
    for file in tqdm(INPUT_FILES, desc="Processing Sources"):
        all_words.update(process_file(file))

    # Save to JSON
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(all_words), f, indent=2)

    print(f"✅ Master dictionary created: {len(all_words)} words.")

if __name__ == "__main__":
    build_lexicon()
