import nltk
import os
import re
import multiprocessing
from tqdm import tqdm
from joblib import Parallel, delayed
from langdetect import detect
from nltk.corpus import words
from transformers import pipeline

# Initialize NLTK
nltk.download("words")
nltk_words = set(words.words())

# File Paths
input_file = "C:/AI SYMBOLIS WORK/word_frequencies.txt"
output_file = "A:/WIKI SCRAPED/wiki_cleaned_words.txt"
flagged_file = "A:/WIKI SCRAPED/wiki_flagged_words.txt"

# Ensure output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Load RoBERTa Model Once
print("🔄 Loading AI Model (RoBERTa)...")
word_classifier = pipeline("fill-mask", model="roberta-base", device=-1)  # CPU-based

# Define Roman Numeral Pattern
ROMAN_NUMERAL_PATTERN = r"^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$"

# Function to Check If a Word is English
def is_english(word):
    """Check if a word is English using Dictionary & LangDetect."""
    if word.lower() in nltk_words:
        return True
    try:
        return detect(word) == "en"
    except:
        return False

# AI-Based Word Reasoning with RoBERTa
def ai_word_reasoning(word):
    """Uses AI to determine if this is likely a real word"""
    masked_sentence = f"This is a <mask> word."
    result = word_classifier(masked_sentence)
    return any(entry["token_str"] == word for entry in result)

# Worker Function for Parallel Processing
def process_word(word):
    """Filters and validates words"""
    word = word.strip()

    # Remove obvious junk (symbols, numbers, Roman numerals)
    if not re.match(r"^[a-zA-Z-]+$", word) or re.match(ROMAN_NUMERAL_PATTERN, word):
        return None, None

    # Check if it's an English word
    if is_english(word):
        return word, None

    # AI model verification (only when needed)
    if ai_word_reasoning(word):
        return word, None
    else:
        return None, word

if __name__ == "__main__":
    # Read Total Line Count for Progress Bar
    try:
        total_lines = sum(1 for _ in open(input_file, "r", encoding="utf-8", errors="ignore"))
        print(f"🔍 Processing {total_lines} words...")
    except Exception as e:
        print(f"🚨 Error reading input file: {e}")
        exit(1)

    # Read Input File
    with open(input_file, "r", encoding="utf-8", errors="ignore") as infile:
        words_list = [line.strip() for line in infile]

    # Define Parallel Processing
    cpu_count = max(2, multiprocessing.cpu_count() // 2)  # Use half available CPUs for stability
    results = Parallel(n_jobs=cpu_count)(
        delayed(process_word)(word) for word in tqdm(words_list, total=total_lines, desc="🛠 Processing Words", unit="word")
    )

    # Separate Cleaned and Flagged Words
    cleaned_words = []
    flagged_words = []
    
    # Save in Chunks of 1M
    SAVE_INTERVAL = 1_000_000
    count = 0

    try:
        with open(output_file, "w", encoding="utf-8", errors="ignore") as outfile, \
             open(flagged_file, "w", encoding="utf-8", errors="ignore") as f_out:
            
            for word, flagged in results:
                if word:
                    cleaned_words.append(word)
                if flagged:
                    flagged_words.append(flagged)

                # Flush every 1M words
                count += 1
                if count % SAVE_INTERVAL == 0:
                    outfile.write("\n".join(cleaned_words) + "\n")
                    f_out.write("\n".join(flagged_words) + "\n")
                    outfile.flush()
                    f_out.flush()
                    cleaned_words.clear()
                    flagged_words.clear()

        print(f"\n✅ English words saved to {output_file}")
        print(f"⚠️ Flagged words saved to {flagged_file}")
    
    except IOError as e:
        print(f"🚨 Error writing to file: {e}")
