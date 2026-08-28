import os
import re
import json

# ✅ **Paths**
BASE_DIR = r"A:\Compression Engine"
INPUT_FOLDER = os.path.join(BASE_DIR, "input")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "processed")
DICTIONARY_FILE = os.path.join(BASE_DIR, "merged_dictionary.json")  # Must be a file

# ✅ Ensure Directories Exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ **Load Dictionary into Memory Once**
def load_symbolis_dictionary():
    if not os.path.exists(DICTIONARY_FILE):
        print(f"❌ ERROR: Dictionary file not found at {DICTIONARY_FILE}")
        return {}

    with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ **Preload Dictionary**
SYMBOLIS_DICTIONARY = load_symbolis_dictionary()

# ✅ **Helper Function: Clean & Match Words**
def clean_word(word):
    """Removes punctuation and converts word to lowercase for matching."""
    return re.sub(r"[^\w\s]", "", word).lower()

# ✅ **Convert Words to HEX Representation**
def convert_to_hex(text):
    def replace_match(match):
        word = match.group(0)
        cleaned = clean_word(word)  # Remove punctuation & make lowercase
        return SYMBOLIS_DICTIONARY.get(cleaned, {}).get("hex", word)  # Replace or keep original

    return re.sub(r"\b\w+\b", replace_match, text)  # Match words only

# ✅ **Process ALL `.txt` Files in Input Folder**
def process_text_files():
    print(f"🚀 Searching for text files in: {INPUT_FOLDER}")

    text_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".txt")]

    if not text_files:
        print("❌ No .txt files found in the input folder.")
        return

    for filename in text_files:
        input_path = os.path.join(INPUT_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(filename)[0]}_symbolis.txt")

        print(f"📂 Processing: {filename}...")

        # Read entire file into memory
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Convert text
        converted_text = convert_to_hex(text)

        # ✅ Remove excessive blank lines in final output
        converted_text = "\n".join([line for line in converted_text.split("\n") if line.strip()])

        # Write converted file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(converted_text)

        print(f"✅ Converted file saved: {output_path}")

    print("✅ **All text files processed successfully!**")

# ✅ **Run the Conversion**
if __name__ == "__main__":
    process_text_files()
