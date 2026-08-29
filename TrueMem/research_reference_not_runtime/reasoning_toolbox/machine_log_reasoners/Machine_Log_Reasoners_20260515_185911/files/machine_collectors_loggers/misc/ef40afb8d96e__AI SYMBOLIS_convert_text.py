import json
import os

# Load the dictionary
dictionary_path = "dictionary.json"
with open(dictionary_path, "r", encoding="utf-8") as f:
    dictionary = json.load(f)

# Get user input for file path
input_file = input("📂 Enter the full path of the file to convert: ").strip()

# Check if file exists
if not os.path.isfile(input_file):
    print(f"❌ Error: File '{input_file}' not found.")
    exit()

# Generate output file path (same folder, with '_converted' added)
file_dir, file_name = os.path.split(input_file)
file_name_no_ext, file_ext = os.path.splitext(file_name)
output_file = os.path.join(file_dir, f"{file_name_no_ext}_converted{file_ext}")

# Read the input file
with open(input_file, "r", encoding="utf-8") as f:
    story_text = f.read()

# Convert the story
words = story_text.split()
converted_words = [dictionary.get(word, word) for word in words]  # Keep original word if not found
converted_story = " ".join(converted_words)

# Save the output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write(converted_story)

print(f"✅ Story successfully converted! Saved as: {output_file}")

