import json
import os
import nltk
from collections import defaultdict, Counter
from nltk.corpus import words
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import SnowballStemmer

# Download necessary NLTK data
nltk.download('words', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

# Load NLTK's verified word list
verified_word_list = set(words.words())

# Initialize stemmer for morpheme extraction
stemmer = SnowballStemmer("english")

# Define directories
BASE_DIR = os.getcwd()
LEXICON_SOURCE_DIR = os.path.join(BASE_DIR, "Active_Lexicon")
VERIFIED_TRUTH_DIR = os.path.join(BASE_DIR, "Verified_Truth")
UNCONFIRMED_DATA_DIR = os.path.join(BASE_DIR, "Unconfirmed_Data")

# Ensure directories exist
os.makedirs(VERIFIED_TRUTH_DIR, exist_ok=True)
os.makedirs(UNCONFIRMED_DATA_DIR, exist_ok=True)

def verify_word(word):
    """
    Check if the word exists in the NLTK corpus.
    Returns True if verified, False otherwise.
    """
    return word.lower() in verified_word_list

def process_lexicon_files():
    """
    Process each JSON file in Active_Lexicon, filtering words into Verified_Truth or Unconfirmed_Data.
    """
    source_files = [f for f in os.listdir(LEXICON_SOURCE_DIR) if f.endswith(".json")]
    total_words = 0
    verified_words = 0
    unverified_words = 0
    
    for filename in source_files:
        input_file = os.path.join(LEXICON_SOURCE_DIR, filename)
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lexicon = json.load(f)
        except Exception as e:
            print(f"Error: Could not open file {input_file}: {str(e)}")
            continue
        
        if not lexicon:
            print(f"Warning: Empty lexicon in {input_file}")
            continue
        
        verified_data = {}
        unverified_data = {}
        
        for word, entry in lexicon.items():
            total_words += 1
            if verify_word(word):
                verified_data[word] = entry
                verified_words += 1
            else:
                unverified_data[word] = entry
                unverified_words += 1
        
        # Save verified words
        verified_output_file = os.path.join(VERIFIED_TRUTH_DIR, filename)
        with open(verified_output_file, 'w', encoding='utf-8') as f:
            json.dump(verified_data, f, indent=4)
        print(f"Verified data saved to {verified_output_file}")
        
        # Save unverified words
        unverified_output_file = os.path.join(UNCONFIRMED_DATA_DIR, filename)
        with open(unverified_output_file, 'w', encoding='utf-8') as f:
            json.dump(unverified_data, f, indent=4)
        print(f"Unverified data saved to {unverified_output_file}")
    
    # Print final stats
    print("\n--- Truth Engine Report ---")
    print(f"Total files processed: {len(source_files)}")
    print(f"Verified words: {verified_words}")
    print(f"Unverified words: {unverified_words}")
    if total_words > 0:
        print(f"Verification success rate: {verified_words / total_words * 100:.2f}%")
    else:
        print("No words processed.")

if __name__ == "__main__":
    process_lexicon_files()
