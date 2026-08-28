import os
from tqdm import tqdm  # Install with: pip install tqdm

# File paths
desktop = os.path.expanduser("~/Desktop")
input_file = os.path.join(desktop, "word_frequencies.txt")
output_file = os.path.join(desktop, "filtered_words.txt")
removed_file = os.path.join(desktop, "removed_words.txt")

# Common 2-letter words to keep
reserved_2_letter_words = {
    "is", "it", "in", "on", "to", "an", "as", "at", "be", "by", "do", "go",
    "he", "if", "me", "my", "no", "of", "or", "so", "up", "we"
}

# 🔄 Load entire file into RAM
print(f"🔄 Loading {input_file} into memory...")
with open(input_file, "r", encoding="utf-8") as infile:
    lines = infile.readlines()

# 🚀 Process words in memory with tqdm progress bar
filtered_words = []
removed_words = []

print(f"🔄 Processing {len(lines):,} words...")
for line in tqdm(lines, desc="Processing", unit="word"):
    parts = line.strip().split()
    if len(parts) != 2:
        continue  # Skip malformed lines

    word, count = parts[0], int(parts[1])

    # Apply filters
    if count < 4 or (len(word) <= 3 and word not in reserved_2_letter_words):
        removed_words.append(line.strip())  # Add to removed words list
    else:
        filtered_words.append(line.strip())  # Keep valid words

# ✅ Save results
print("✅ Writing filtered results...")
with open(output_file, "w", encoding="utf-8") as outfile:
    outfile.write("\n".join(filtered_words))

with open(removed_file, "w", encoding="utf-8") as dumpfile:
    dumpfile.write("\n".join(removed_words))

print(f"✅ Done! Check your Desktop for '{output_file}' and '{removed_file}'.")
