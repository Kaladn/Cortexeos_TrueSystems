"""
Remove Words with Numbers
-------------------------
Reads a text file containing a word list and removes any word that contains
numbers. Saves a cleaned version of the file.
"""

import os

# File paths
INPUT_FILE = "A:/Symbolis/data/cleaned_words.txt"
OUTPUT_FILE = "A:/Symbolis/data/final_words.txt"

def contains_numbers(word):
    """Checks if a word contains any numbers."""
    return any(char.isdigit() for char in word)

def clean_number_list():
    """Removes words containing numbers from the word list."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines()]

    # Remove words containing numbers
    cleaned_words = [word for word in words if not contains_numbers(word)]

    # Save cleaned words to new file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_words))

    print(f"✅ Successfully removed words with numbers. Final list saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_number_list()
