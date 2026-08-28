"""
Remove Acronyms (All Uppercase Words)
-------------------------------------
Reads a text file containing a word list and removes any word that is
fully uppercase (acronyms). Saves a cleaned version of the file.
"""

import os

# File paths
INPUT_FILE = "A:/Symbolis/data/final_words.txt"
OUTPUT_FILE = "A:/Symbolis/data/final_words_no_acronyms.txt"

def is_acronym(word):
    """Checks if a word is an acronym (all uppercase)."""
    return word.isupper() and len(word) > 1  # Ensures single-letter words like 'I' remain

def clean_acronym_list():
    """Removes acronyms from the word list."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines()]

    # Remove acronyms (all-uppercase words)
    cleaned_words = [word for word in words if not is_acronym(word)]

    # Save cleaned words to new file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_words))

    print(f"✅ Successfully removed acronyms. Final list saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_acronym_list()
