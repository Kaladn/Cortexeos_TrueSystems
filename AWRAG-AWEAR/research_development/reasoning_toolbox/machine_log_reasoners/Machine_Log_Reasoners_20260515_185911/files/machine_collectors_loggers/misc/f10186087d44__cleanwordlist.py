"""
Remove Words with Punctuation
-----------------------------
Reads a text file containing a word list and removes any word that contains
punctuation. Saves a cleaned version of the file.
"""

import os
import string

# File paths
INPUT_FILE = "A:/Symbolis/data/words.txt"
OUTPUT_FILE = "A:/Symbolis/data/cleaned_words.txt"

def contains_punctuation(word):
    """Checks if a word contains any punctuation."""
    return any(char in string.punctuation for char in word)

def clean_word_list():
    """Removes words containing punctuation from the word list."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines()]

    # Remove words containing punctuation
    cleaned_words = [word for word in words if not contains_punctuation(word)]

    # Save cleaned words to new file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_words))

    print(f"✅ Successfully removed words with punctuation. Cleaned list saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_word_list()
