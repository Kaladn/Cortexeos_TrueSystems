import os
import json

# Path to store the updated dictionary
DICTIONARY_FILE = "data_scraping/wordlist.json"

def load_existing_words():
    """Load existing words from dictionary."""
    if os.path.exists(DICTIONARY_FILE):
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))  # Load existing words as a set for fast lookup
            except json.JSONDecodeError:
                return set()
    return set()

def save_updated_words(word_list):
    """Save updated word list to JSON."""
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(word_list)), f, indent=2)
    print(f"\n✅ Dictionary updated! Total words: {len(word_list)}")

def extract_words_from_file(file_path):
    """Extract words from a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().lower()  # Convert to lowercase
        words = set(word.strip(".,!?()[]{}:;\"'") for word in text.split())  # Clean and tokenize
        print(f"📄 Processed {file_path} | Words found: {len(words)}")
        return words
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return set()

def process_single_file():
    """Ask user for a single file path and process it."""
    file_path = input("📂 Enter full file path: ").strip()
    
    if not os.path.isfile(file_path):
        print(f"❌ Error: File '{file_path}' not found.")
        return
    
    existing_words = load_existing_words()
    new_words = extract_words_from_file(file_path)
    
    combined_words = existing_words.union(new_words)
    save_updated_words(combined_words)

def process_directory():
    """Ask user for a directory and process all .txt files recursively."""
    dir_path = input("📂 Enter directory path: ").strip()

    if not os.path.isdir(dir_path):
        print(f"❌ Error: Directory '{dir_path}' not found.")
        return
    
    existing_words = load_existing_words()
    new_words = set()

    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                new_words.update(extract_words_from_file(file_path))

    combined_words = existing_words.union(new_words)
    save_updated_words(combined_words)

def main():
    print("\n📂 Text File Scanner")
    print("1️⃣ Process a single file")
    print("2️⃣ Process an entire directory (recursive scan)")
    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        process_single_file()
    elif choice == "2":
        process_directory()
    else:
        print("❌ Invalid choice. Please enter 1 or 2.")

if __name__ == "__main__":
    main()
