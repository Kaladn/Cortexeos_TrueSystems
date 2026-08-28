"""
Add Capital Letters for Each Alphabet Letter
--------------------------------------------
Reads a cleaned word list and ensures that at least one word with a capital 
letter exists for each starting letter (A-Z). If missing, a single letter (A-Z) is added.
"""

import os
import string

# File paths
INPUT_FILE = "A:/Symbolis/data/final_words_no_acronyms.txt"
OUTPUT_FILE = "A:/Symbolis/data/final_words_with_capitals.txt"

def add_capital_letters():
    """Adds a single capital letter for each alphabet letter at the beginning of the list."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines()]

    # Find existing first letters
    existing_first_letters = {word[0].upper() for word in words if word}

    # Ensure each letter A-Z is present at least once
    missing_letters = [letter for letter in string.ascii_uppercase if letter not in existing_first_letters]

    # Prepend missing capital letters to the word list
    final_words = missing_letters + words

    # Save final list with capital letters
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_words))

    print(f"✅ Successfully added missing capital letters. Final list saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    add_capital_letters()
