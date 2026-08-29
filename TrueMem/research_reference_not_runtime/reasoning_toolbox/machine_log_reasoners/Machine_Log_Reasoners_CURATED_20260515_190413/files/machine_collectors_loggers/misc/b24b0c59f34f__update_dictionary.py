import os
import json

# Paths
WORDLIST_TXT = "data_scraping/wordlist.txt"  # Your large .txt file with words
DICTIONARY_JSON = "data_scraping/wordlist.json"  # Existing dictionary

def load_existing_words():
    """Load the current word dictionary"""
    if os.path.exists(DICTIONARY_JSON):
        with open(DICTIONARY_JSON, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))  # Load as a set for fast lookup
            except json.JSONDecodeError:
                return set()  # Return empty if file is corrupt
    return set()

def update_dictionary():
    """Add new words from TXT to dictionary, avoiding duplicates"""
    existing_words = load_existing_words()

    with open(WORDLIST_TXT, "r", encoding="utf-8") as f:
        new_words = set(f.read().splitlines())  # Read words, remove duplicates

    added_words = new_words - existing_words  # Only keep new words

    if added_words:
        print(f"📝 {len(added_words)} new words found. Adding to dictionary...")
        updated_words = existing_words.union(added_words)  # Merge sets
        
        # Save back to JSON
        with open(DICTIONARY_JSON, "w", encoding="utf-8") as f:
            json.dump(sorted(list(updated_words)), f, indent=2)
        
        print(f"✅ Dictionary updated! Total words: {len(updated_words)}")
    else:
        print("✅ No new words found. Dictionary is already up-to-date.")

if __name__ == "__main__":
    update_dictionary()
