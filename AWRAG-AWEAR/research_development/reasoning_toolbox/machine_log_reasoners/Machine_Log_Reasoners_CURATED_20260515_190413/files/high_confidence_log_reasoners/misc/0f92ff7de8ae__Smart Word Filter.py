import nltk
import re
import multiprocessing
from tqdm import tqdm
from joblib import Parallel, delayed
from langdetect import detect
from nltk.corpus import words
from transformers import pipeline

# Download necessary NLTK words
nltk.download("words")
nltk_words = set(words.words())

# File Paths
input_file = "C:/AI SYMBOLIS WORK/word_frequencies.txt"
output_file = "A:/WIKI SCRAPED/wiki_cleaned_words.txt"
flagged_file = "A:/WIKI SCRAPED/wiki_flagged_words.txt"

# Load RoBERTa Model (Initialize Once!)
print("🔄 Loading AI Model (RoBERTa)...")
word_classifier = pipeline("fill-mask", model="roberta-base", device=-1)  # CPU-based

# Roman Numeral Pattern
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

# AI-Based Word Reasoning with RoBERTa (Batch Processing)
def ai_word_reasoning(words):
    """Uses AI to determine if this is likely a real word"""
    masked_sentence = [f"This is a {word} word." for word in words]
    results = word_classifier(masked_sentence)
    return [any(entry["token_str"] == word for entry in result) for word, result in zip(words, results)]

# Worker Function for Parallel Processing
def process_batch(start, end, words_list):
    """Process a batch of words"""
    batch = words_list[start:end]
    cleaned = []
    flagged = []
    
    for word in batch:
        # Remove obvious junk (symbols, numbers, Roman numerals)
        if not re.match(r"^[a-zA-Z-]+$", word) or re.match(ROMAN_NUMERAL_PATTERN, word):
            continue

        # Check if it's an English word
        if is_english(word):
            cleaned.append(word)
        else:
            # AI model verification (only when needed)
            if ai_word_reasoning([word])[0]:
                cleaned.append(word)
            else:
                flagged.append(word)
    
    return cleaned, flagged

if __name__ == "__main__":
    # Read Total Line Count for Progress Bar
    total_lines = sum(1 for _ in open(input_file, "r", encoding="utf-8", errors="ignore"))

    print(f"🔍 Processing {total_lines} words...")

    # Read Input File
    with open(input_file, "r", encoding="utf-8", errors="ignore") as infile:
        words_list = [line.strip() for line in infile]

    # Define Parallel Processing (Split into batches)
    cpu_count = multiprocessing.cpu_count()
    batch_size = len(words_list) // cpu_count  # Split words into batches for parallel processing

    # Parallel processing of batches
    results = Parallel(n_jobs=cpu_count)(delayed(process_batch)(i * batch_size, (i + 1) * batch_size, words_list) for i in range(cpu_count))

    # Flatten results
    cleaned_words = []
    flagged_words = []
    for cleaned, flagged in results:
        cleaned_words.extend(cleaned)
        flagged_words.extend(flagged)

    # Save in Chunks of 1M
    SAVE_INTERVAL = 1_000_000
    count = 0

    with open(output_file, "w", encoding="utf-8", errors="ignore") as outfile, \
         open(flagged_file, "w", encoding="utf-8", errors="ignore") as f_out:
        
        for word in cleaned_words:
            outfile.write(word + "\n")

            # Flush every 1M words
            count += 1
            if count % SAVE_INTERVAL == 0:
                outfile.flush()

        for word in flagged_words:
            f_out.write(word + "\n")
        
            if count % SAVE_INTERVAL == 0:
                f_out.flush()

    print(f"\n✅ English words saved to {output_file}")
    print(f"⚠️ Flagged words saved to {flagged_file}")


