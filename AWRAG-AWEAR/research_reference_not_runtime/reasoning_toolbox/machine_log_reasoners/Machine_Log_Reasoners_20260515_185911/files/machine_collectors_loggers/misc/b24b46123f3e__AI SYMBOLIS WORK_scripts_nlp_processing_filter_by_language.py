import json
from langdetect import detect
import os

INPUT_FILE = "data_scraping/wordlist.json"
OUTPUT_FOLDER = "data_scraping/languages"
BATCH_SIZE = 100000  # Process in chunks

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Open and process in chunks
def process_words():
    language_dict = {}

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = []
        for line in f:  # Process line by line
            words.extend(json.loads(line.strip()))  # Avoid loading full JSON

    print(f"📝 Total Words Loaded: {len(words)}")

    # Process words in chunks
    for i in range(0, len(words), BATCH_SIZE):
        batch = words[i:i+BATCH_SIZE]
        for word in batch:
            try:
                lang = detect(word)
                if lang not in language_dict:
                    language_dict[lang] = []
                language_dict[lang].append(word)
            except:
                continue  # Skip words that cause errors

    # Save each language separately
    for lang, words in language_dict.items():
        lang_file = os.path.join(OUTPUT_FOLDER, f"{lang}.json")
        with open(lang_file, "w", encoding="utf-8") as f:
            json.dump(words, f, indent=2)
        print(f"✅ Saved {len(words)} words to {lang_file}")

if __name__ == "__main__":
    process_words()
