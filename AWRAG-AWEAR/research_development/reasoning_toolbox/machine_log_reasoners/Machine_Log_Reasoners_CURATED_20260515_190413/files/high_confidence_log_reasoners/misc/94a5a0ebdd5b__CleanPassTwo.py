import os
import re
from tqdm import tqdm

# Directories
input_dir = "C:\\Users\\mydyi\\Desktop\\clean_pass_two"
output_dir = "C:\\Users\\mydyi\\Desktop\\clean_pass_three"
os.makedirs(output_dir, exist_ok=True)

# Regex Patterns
hyphen_pattern = re.compile(r'\b\w*-{1,}\w*\b')  # Detects words with hyphens
number_pattern = re.compile(r'\b\w+\s+\d+\b')  # Detects words followed by numbers

# File Processing
files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
unique_words = set()

print(f"🔄 Processing {len(files)} files...")
for file in tqdm(files, desc="Cleaning Files", unit="file"):
    input_path = os.path.join(input_dir, file)
    output_path = os.path.join(output_dir, file)
    
    with open(input_path, "r", encoding="utf-8") as infile:
        lines = infile.readlines()
    
    cleaned_words = set()
    for line in lines:
        line = line.strip()
        if hyphen_pattern.search(line) or number_pattern.search(line):
            continue  # Skip if it contains hyphens or numbers
        cleaned_words.add(line)  # Store unique words only
    
    # If cleaned words exist, write to output
    if cleaned_words:
        with open(output_path, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(sorted(cleaned_words)) + "\n")
    else:
        os.remove(output_path)  # Auto-delete empty files

print(f"✅ Done! Cleaned files are in '{output_dir}'.")
