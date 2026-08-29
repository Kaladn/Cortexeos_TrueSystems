import os
import json
import re
import hashlib
import sys
from tqdm import tqdm
from joblib import Parallel, delayed

# ✅ Ask User for File/Folder Input
def get_input_path():
    """Prompts the user for a file or directory path."""
    while True:
        path = input("🔍 Enter the path of the file or folder to process: ").strip()
        if os.path.exists(path):
            return path
        print("❌ Invalid path. Please enter a valid file or folder.")


# ✅ Paths
DEFAULT_JSON_STORAGE_DIR = "A:/Json-Neuron-Storage"
LOG_FILE = os.path.join(DEFAULT_JSON_STORAGE_DIR, "failed_batches.log")

# ✅ Configurations
BATCH_SIZE = 550000  # Process & categorize 550K words per batch
NUM_WORKERS = 6  # Use 6 parallel workers
NEURON_DB = {}  # In-Memory JSON Neuron DB

# ✅ Ensure Directories Exist
os.makedirs(DEFAULT_JSON_STORAGE_DIR, exist_ok=True)

# ✅ Subword Tokenization (Faster Processing)
def tokenize_word(word):
    """Tokenizes large words for efficient lookup & storage."""
    if len(word) < 6:
        return [word]  # Skip tokenization for small words
    return re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+', word) or [word]

# ✅ Unique Symbol Generator
def generate_symbol(word):
    """Creates a unique symbol using hashed encoding."""
    return f"S{abs(hash(word)) % 10**8}"

# ✅ Improved Categorization Function
CATEGORY_MAP = {
    "medical": {"virus", "cardio", "neuro", "therapy", "surgery", "diagnosis", "anatomy"},
    "scientific": {"quantum", "physics", "gravity", "chemistry", "biology", "genetics"},
    "historical": {"dynasty", "revolution", "empire", "medieval", "renaissance"},
    "legal": {"judge", "court", "law", "trial", "justice", "legislation", "verdict"},
    "psychology": {"behavior", "cognitive", "emotion", "therapy", "judgmental", "mental"},
    "educational": {"education", "university", "learning", "research", "academic"}
}

def categorize_word(word):
    """Assigns a category based on keyword detection."""
    for category, keywords in CATEGORY_MAP.items():
        if any(term in word for term in keywords):
            return category  # Assign first matching category
    return "general"  # Default fallback

# ✅ Logging Function for Skipped Batches
def log_skipped_batch(batch_number, reason):
    """Logs any skipped batch into a file with UTF-8 encoding."""
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"Batch {batch_number} skipped: {reason}\n")
    print(f"⚠️ Warning: Batch {batch_number} skipped. Reason: {reason}")

# ✅ NLP Processing Function (JSON Mode)
def process_word(word):
    """Processes a word into JSON neuron format."""
    word = word.strip().lower()
    if not word.isalpha():  # Skip numbers, symbols, etc.
        return None

    tokens = tokenize_word(word)
    symbol = generate_symbol(word)
    category = categorize_word(word)

    word_data = {
        "symbol": symbol,
        "tokens": tokens,
        "category": category,
        "metadata": {
            "length": len(word),
            "num_tokens": len(tokens),
            "vowel_ratio": sum(1 for c in word if c in "aeiou") / max(len(word), 1),
            "complexity_score": len(set(word)) / len(word)
        }
    }

    # **Store word only if it's valid**
    if word and word_data:
        NEURON_DB[word] = word_data
        return word
    return None

# ✅ NLP Processor (Batch Processing in RAM)
def process_words(input_path):
    """Loads words into RAM, processes, and dumps to JSON."""
    all_files = []

    # **Check if input is a file or directory**
    if os.path.isfile(input_path):
        all_files.append(input_path)
    elif os.path.isdir(input_path):
        all_files = [os.path.join(input_path, file) for file in os.listdir(input_path) if file.endswith(".txt")]
    
    total_words = []

    # **Load Words Into RAM**
    for file in tqdm(all_files, desc="📂 Loading Words Into RAM"):
        with open(file, "r", encoding="utf-8") as f:
            words = f.read().splitlines()

            # **Verify first and last word in each file**
            if words:
                print(f"✅ File: {file} → First: {words[0]} | Last: {words[-1]}")
            
            total_words.extend(words)

    print(f"🚀 Total Words Loaded: {len(total_words)}")

    # **Process words in 550K batches**
    for i in range(0, len(total_words), BATCH_SIZE):
        batch = total_words[i:i + BATCH_SIZE]
        batch_number = (i // BATCH_SIZE) + 1
        print(f"🚀 Processing Batch {batch_number}: {len(batch)} words...")

        # **Parallel Processing**
        results = Parallel(n_jobs=NUM_WORKERS, backend="loky")(delayed(process_word)(word) for word in batch)

        # **Filter out None values (invalid words)**
        results = {word: NEURON_DB.get(word) for word in results if word in NEURON_DB}

        if results:
            # **Save JSON Neuron File**
            batch_filename = f"batch_{batch_number}.json"
            batch_path = os.path.join(DEFAULT_JSON_STORAGE_DIR, batch_filename)
            with open(batch_path, "w", encoding="utf-8") as json_file:
                json.dump(results, json_file, indent=4)

            print(f"✅ JSON Saved: {batch_filename}")
            NEURON_DB.clear()  # Clear RAM to process the next batch
        else:
            log_skipped_batch(batch_number, "No valid words found")

    print("✅ **Hybrid JSON Processing Complete!**")

# ✅ Run the JSON-Based NLP Pipeline
if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]  # Allow passing file/folder as a command-line argument
    else:
        input_path = get_input_path()  # Prompt user for file or folder path
    
    print(f"🚀 Processing Words & Storing in JSON from: {input_path}")
    process_words(input_path)
    print("✅ **JSON NLP Processing Complete!**")
