import hashlib
import json
import os

# File paths
WORDLIST_FILE = "C:/Users/mydyi/OneDrive/Documents/Desktop/DATA BACKUP/wordlist.txt"
DICTIONARY_FILE = "C:/Users/mydyi/OneDrive/Documents/Desktop/DATA BACKUP/dictionary.json"

def generate_symbol(word):
    """Generate a unique symbol for a given word using a hash."""
    hash_object = hashlib.md5(word.encode())  # MD5 Hash
    hex_symbol = hash_object.hexdigest()[:6]  # Take first 6 characters
    return hex_symbol.upper()

def process_wordlist():
    """Load words from wordlist.txt, generate symbols, and store in dictionary.json."""
    if not os.path.exists(WORDLIST_FILE):
        print(f"❌ Error: {WORDLIST_FILE} not found!")
        return

    with open(WORDLIST_FILE, "r", encoding="utf-8") as file:
        words = [line.strip() for line in file if line.strip()]  # Read lines and remove empty lines

    dictionary = {}

    for word in words:
        dictionary[word] = generate_symbol(word)

    # Save to dictionary.json
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as file:
        json.dump(dictionary, file, indent=4)

    print(f"✅ Successfully processed {len(words)} words and saved to dictionary.json!")

if __name__ == "__main__":
    process_wordlist()

