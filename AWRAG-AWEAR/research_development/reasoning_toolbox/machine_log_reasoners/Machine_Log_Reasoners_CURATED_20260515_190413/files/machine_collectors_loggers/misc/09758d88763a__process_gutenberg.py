import os
import json

# 🔹 Define paths
GUTENBERG_DIR = r"C:\Users\mydyi\OneDrive\Documents\Desktop\txt-files.tar\txt-files.tar\cache\epub"
DICTIONARY_PATH = "data/dictionary.json"

def extract_words_from_txt(file_path):
    """Extract words from a text file, clean, and return unique words."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            print(f"⚠️ Warning: Empty file -> {file_path}")
            return set()

        words = set(text.lower().split())  # Convert to lowercase & remove duplicates
        words = {word.strip(".,!?()[]{}:;\"'") for word in words}  # Remove punctuation
        return words
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
        return set()

def load_dictionary():
    """Load the existing dictionary JSON file."""
    if os.path.exists(DICTIONARY_PATH):
        with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_dictionary(words):
    """Save updated words to dictionary.json."""
    with open(DICTIONARY_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(list(words)), f, indent=2)
    print(f"✅ Dictionary updated! Total words: {len(words)}")

def process_gutenberg():
    """Recursively scan the Gutenberg directory and extract words from all .txt files."""
    dictionary = load_dictionary()
    new_words = set()
    file_count = 0

    print(f"🔍 Scanning Gutenberg text files in: {GUTENBERG_DIR}")

    for root, _, files in os.walk(GUTENBERG_DIR):
        for file in files:
            if file.endswith(".txt"):
                file_count += 1
                file_path = os.path.join(root, file)
                print(f"📖 Processing: {file_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    first_lines = [next(f, '').strip() for _ in range(5)]
                print(f"📜 First few lines of {file}:\n", "\n".join(first_lines), "\n---")

                words = extract_words_from_txt(file_path)
                new_words.update(words)

    print(f"🔢 Found {file_count} text files to process.")

    # Add only new words
    added_words = new_words - dictionary
    dictionary.update(added_words)

    print(f"\n📝 {len(added_words)} new words found. Adding to dictionary...")
    save_dictionary(dictionary)

if __name__ == "__main__":
    process_gutenberg()

