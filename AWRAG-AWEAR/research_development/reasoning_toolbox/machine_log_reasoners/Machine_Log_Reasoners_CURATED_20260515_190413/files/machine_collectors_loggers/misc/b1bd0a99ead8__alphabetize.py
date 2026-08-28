import os
from tqdm import tqdm

# Directory containing the A-Z sorted files
input_dir = r"C:\Users\mydyi\Desktop\tqmd"

# Get list of all files in the directory
files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

# Process each file
print("🔄 Sorting words alphabetically within each file...")
for file in tqdm(files, desc="Sorting Files", unit="file"):
    file_path = os.path.join(input_dir, file)

    # Load words into RAM
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Sort alphabetically (ignoring case)
    sorted_lines = sorted(lines, key=lambda x: x.split()[0].lower())

    # Write back the sorted content
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(sorted_lines)

print("\n✅ Done! All words are now sorted alphabetically within their respective files.")
