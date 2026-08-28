import os
import json
import shutil
from tqdm import tqdm

# Get the user's desktop path
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

# Define source directory (Modify this to your dataset folder)
source_directory = input("Enter the directory containing your JSON files: ")

# Define output directory (It will be named 'Cleaned_Output' on Desktop)
output_directory = os.path.join(desktop_path, "Cleaned_Output")

# Create output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Define garbage words (Replace with an automated filter if needed)
garbage_words = {"xfx", "xhzih", "xtrac", "wyrzdzia"}  # Modify as needed

# Get all JSON files in the directory
json_files = [f for f in os.listdir(source_directory) if f.endswith(".json")]

print(f"🔍 Found {len(json_files)} JSON files. Starting cleanup...")

for json_file in tqdm(json_files, desc="Processing Files", unit="file"):
    file_path = os.path.join(source_directory, json_file)
    
    # Load JSON data
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = {}
    removed_entries = {}

    # Process each word entry
    for word, details in data.items():
        if word in garbage_words:
            # Preserve only essential data
            removed_entries[word] = {
                "hex": details["hex"],
                "binary": details["binary"],
                "font_symbol": details["font_symbol"],
                "tone_signature": details["tone_signature"]
            }
        else:
            # Keep valid words with full details
            cleaned_data[word] = details

    # Define output filenames
    cleaned_file_path = os.path.join(output_directory, f"cleaned_{json_file}")
    removed_file_path = os.path.join(output_directory, f"removed_{json_file}")

    # Save cleaned dataset
    with open(cleaned_file_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=4, ensure_ascii=False)

    # Save removed words for review
    with open(removed_file_path, "w", encoding="utf-8") as f:
        json.dump(removed_entries, f, indent=4, ensure_ascii=False)

print(f"\n✅ Cleanup complete! All cleaned files are saved in: {output_directory}")
print(f"🗑️ Removed words are also saved for review.")
