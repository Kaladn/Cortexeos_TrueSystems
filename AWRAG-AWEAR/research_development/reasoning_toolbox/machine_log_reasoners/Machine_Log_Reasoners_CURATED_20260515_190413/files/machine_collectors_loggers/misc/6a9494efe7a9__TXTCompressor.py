import os
import re

# ✅ **Embedded Full Symbolis Dictionary**
SYMBOLIS_DICTIONARY = {
    "arterioplasty": {"hex": "0x97F9FFFF8F"},
    "aidroos": {"hex": "0x093400008A"},
    "afslutningen": {"hex": "0x8575FFFEE2"},
    "appear--socrates": {"hex": "0x3919FFFE74"},
    "apparatwangen": {"hex": "0xB212000217"},
    "afterwards--twenty": {"hex": "0x8F15FFFD74"},
    "adigranth": {"hex": "0xC931FFFD65"},
    "avoided--liberum": {"hex": "0x330BFFFD2C"},
    "anohi": {"hex": "0x45A1FFFC94"},
    "atopen": {"hex": "0x572E00039F"},
    "avonbeg": {"hex": "0xB659FFFC3F"},
    "abrasions": {"hex": "0x10E9FFFBF3"},
    "alids": {"hex": "0x1747FFFBD8"},
    "arsyversy": {"hex": "0xACE8000446"},
    "alienigma": {"hex": "0x61AE0004F5"},
    "ascapede": {"hex": "0x663C0005A9"},
    "ambassador--general": {"hex": "0x3DE1FFFA09"},
    "air-groves": {"hex": "0x494A000610"},
    "allotriophagia": {"hex": "0x9395FFF9EE"},
    # ✅ Add your full dictionary here!
}

# ✅ **Paths**
BASE_DIR = r"A:\Compression Engine"
INPUT_FOLDER = os.path.join(BASE_DIR, "input")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "processed")

# ✅ Ensure Directories Exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ **Helper Function: Clean & Match Words**
def clean_word(word):
    """Removes punctuation and converts word to lowercase for matching."""
    return re.sub(r"[^\w\s]", "", word).lower()

# ✅ **Convert Words to HEX Representation**
def convert_to_hex(text):
    def replace_match(match):
        word = match.group(0)
        cleaned = clean_word(word)  # Remove punctuation & make lowercase

        # Replace if found in dictionary, else keep original
        return SYMBOLIS_DICTIONARY.get(cleaned, {}).get("hex", word)

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

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Convert text
        converted_text = convert_to_hex(text)

        # ✅ Remove excessive blank lines in final output
        converted_text = "\n".join([line for line in converted_text.split("\n") if line.strip()])

        # Save converted file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(converted_text)

        print(f"✅ Converted file saved: {output_path}")

# ✅ **Run the Conversion**
if __name__ == "__main__":
    process_text_files()
    print("✅ **All text files processed successfully!**")
