import os
import re
from tqdm import tqdm

# Directory where A-Z word files are stored
input_dir = r"C:\Users\mydyi\Desktop\tqmd"
output_dir = r"C:\Users\mydyi\Desktop\tqmd_cleaned"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Function to properly clean words while keeping hyphenated ones
def clean_word(word):
    word = re.sub(r'[0-9]', '', word)  # Remove numbers
    word = re.sub(r'[^\w-]', '', word)  # Remove all punctuation except hyphens
    word = word.strip().lower()  # Convert to lowercase for consistency
    return word if word else None  # Return None if empty after cleaning

# Process all A-Z files
print("🧹 Cleaning and fixing word lists while keeping hyphenated words...")

for file in tqdm(os.listdir(input_dir), desc="Processing Files", unit="file"):
    if not file.endswith(".txt"):
        continue

    input_path = os.path.join(input_dir, file)
    output_path = os.path.join(output_dir, file)

    cleaned_words = set()  # Use a set to prevent duplicates

    with open(input_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f]

    for word in words:
        cleaned = clean_word(word)
        if cleaned:
            cleaned_words.add(cleaned)

    # Write cleaned words back, sorted alphabetically
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(cleaned_words)))

print("\n✅ Cleaning complete! Files are in:", output_dir)
