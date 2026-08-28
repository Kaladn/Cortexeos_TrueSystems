import os
import json

# Paths
DICTIONARY_FILE = "data_scraping/wordlist.json"

def load_dictionary():
    """Load existing words from the dictionary file."""
    if os.path.exists(DICTIONARY_FILE):
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))  # Load dictionary as a set for quick lookups
            except json.JSONDecodeError:
                return set()
    return set()

def save_dictionary(words):
    """Save updated dictionary back to the JSON file."""
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(words), f, indent=2)
    print(f"✅ Dictionary updated! Total words: {len(words)}")

def extract_words_from_file(file_path):
    """Extract words from a single text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        words = text.lower().split()
        words = {word.strip(".,!?()[]{}:;\"'") for word in words}  # Clean punctuation
        return words
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return set()

def scan_directory(directory):
    """Scan all .txt files in a directory and extract words."""
    words = set()
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                print(f"📂 Processing {file_path}...")
                words.update(extract_words_from_file(file_path))
    return words

def main():
    """User chooses to process a single file or entire directory."""
    dictionary = load_dictionary()

    print("📂 Choose Input Mode:")
    print("1. Single File")
    print("2. Entire Directory")
    choice = input("Enter choice (1/2): ")

    if choice == "1":
        file_path = input("📄 Enter full file path: ").strip()
        if os.path.exists(file_path) and file_path.endswith(".txt"):
            new_words = extract_words_from_file(file_path)
            dictionary.update(new_words)
            print(f"📝 {len(new_words)} new words found.")
        else:
            print("❌ Invalid file path or file type.")

    elif choice == "2":
        directory = input("📁 Enter directory path: ").strip()
        if os.path.exists(directory):
            new_words = scan_directory(directory)
            dictionary.update(new_words)
            print(f"📝 {len(new_words)} new words found from all .txt files.")
        else:
            print("❌ Directory not found.")

    else:
        print("❌ Invalid choice. Exiting.")
        return

    save_dictionary(dictionary)

if __name__ == "__main__":
    main()
