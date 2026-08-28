import os
from tqdm import tqdm  # Install with: pip install tqdm

# File paths
desktop = os.path.expanduser("~/Desktop")
input_file = os.path.join(desktop, "filtered_words.txt")
output_folder = os.path.join(desktop, "clean_pass_one")

# Settings
lines_per_chunk = 1_000_000  # Adjust if needed (1M lines per file)

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# 🔄 Load entire file into RAM
print(f"🔄 Loading '{input_file}' into memory...")
with open(input_file, "r", encoding="utf-8") as infile:
    words = infile.readlines()

# 🚀 Alphabetizing the words
print(f"🔄 Sorting {len(words):,} words alphabetically...")
words.sort()

# 🚀 Writing sorted chunks with tqdm progress
print(f"🔄 Splitting and writing sorted words into '{output_folder}/'...")
chunk_count = 0
for i in tqdm(range(0, len(words), lines_per_chunk), desc="Writing", unit="chunk"):
    chunk_count += 1
    output_file = os.path.join(output_folder, f"sorted_part_{chunk_count}.txt")

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.writelines(words[i:i + lines_per_chunk])

    print(f"✅ Created: {output_file}")

print(f"🎉 Done! All sorted files are in '{output_folder}/'.")
