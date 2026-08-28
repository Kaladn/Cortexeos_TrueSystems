"""
Analyze Word Length Distribution
--------------------------------
Reads a text file containing a word list and calculates how many words exist
for each word length.
"""

import os
import collections

# File paths
INPUT_FILE = "A:/Symbolis/data/final_words_no_acronyms.txt"

def analyze_word_lengths():
    """Counts how many words exist for each length."""
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines() if line.strip()]

    # Count occurrences of each word length
    length_counts = collections.Counter(len(word) for word in words)

    # Sort and display results
    sorted_lengths = sorted(length_counts.items())

    print("📊 Word Length Distribution:")
    for length, count in sorted_lengths:
        print(f"Length {length}: {count} words")

if __name__ == "__main__":
    analyze_word_lengths()
