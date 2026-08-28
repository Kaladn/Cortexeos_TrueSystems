import json
import time
import fasttext
import fasttext.util
import multiprocessing
from tqdm import tqdm

# File Paths
INPUT_FILE = "data_scraping/wordlist.json"
OUTPUT_FILE = "data_scraping/english_words.json"

# Processing Settings
BATCH_SIZE = 500000  # Increased batch size to 500K
WAIT_TIME = 0.01  # Reduced wait time to 10ms
CPU_CORES = max(2, multiprocessing.cpu_count() - 2)  # Use all but 2 cores

# Load FastText Language Model (MUCH FASTER)
fasttext.util.download_model('en', if_exists='ignore')
model = fasttext.load_model("cc.en.300.bin")  # English model

def is_english(word):
    """FastText-based English detection."""
    return model.predict(word)[0][0] == "__label__en"

def process_batch(batch):
    """Filters a batch for English words."""
    return [word for word in batch if is_english(word)]

def process_words():
    """Processes words in parallel using multiprocessing."""
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = json.load(f)

    total_words = len(words)
    english_words = []
    
    print(f"🚀 Filtering English Words from {total_words:,} words using {CPU_CORES} cores...")

    try:
        with multiprocessing.Pool(CPU_CORES) as pool:
            for i in tqdm(range(0, total_words, BATCH_SIZE), desc="Processing"):
                batch = words[i:i + BATCH_SIZE]
                result = pool.apply_async(process_batch, (batch,))
                english_words.extend(result.get())  # Collect results
                
                time.sleep(WAIT_TIME)  # Prevent system overload

    except KeyboardInterrupt:
        print("\n⛔ Process interrupted by user. Saving partial results...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(english_words, f, indent=2)

    print(f"\n✅ English words saved to {OUTPUT_FILE} ({len(english_words):,} words)")

if __name__ == "__main__":
    process_words()
