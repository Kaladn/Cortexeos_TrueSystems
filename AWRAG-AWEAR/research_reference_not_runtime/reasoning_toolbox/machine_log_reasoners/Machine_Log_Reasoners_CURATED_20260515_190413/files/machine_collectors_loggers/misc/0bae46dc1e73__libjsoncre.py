import os
import json
import re

# ✅ Paths
BASE_DIR = "A:/Symbolis_TXT_Conversion"
INCOMING_DIR = os.path.join(BASE_DIR, "incoming_files")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
DICTIONARY_DIR = os.path.join(BASE_DIR, "json_dictionary")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ✅ Ensure Directories Exist
for directory in [INCOMING_DIR, PROCESSED_DIR, DICTIONARY_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ✅ Load A-Z Symbolis Dictionary
symbolis_dict = {}
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    json_path = os.path.join(DICTIONARY_DIR, f"{letter}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            symbolis_dict.update(json.load(f))

# ✅ Function to Convert Text Using Symbolis Dictionary
def convert_text(file_path, reverse=False):
    """Converts words in a text file to symbols or reverses the process."""
    file_name = os.path.basename(file_path)
    output_file = os.path.join(PROCESSED_DIR, file_name)
    log_file = os.path.join(LOGS_DIR, f"unmatched_{file_name}.txt")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    words = re.findall(r"\b\w+\b", text)
    unmatched_words = set()

    converted_text = []
    for word in text.split():  # Keeps spacing intact
        stripped_word = re.sub(r'\W+', '', word)  # Remove punctuation for matching
        match = symbolis_dict.get(stripped_word.lower(), None)

        if match:
            converted_text.append(match if not reverse else stripped_word)
        else:
            converted_text.append(word)  # Keep original
            unmatched_words.add(stripped_word)

    # ✅ Save Converted Text
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(" ".join(converted_text))

    # ✅ Log Unmatched Words
    if unmatched_words:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(unmatched_words))

    print(f"✅ Processed: {file_name} -> {output_file}")

# ✅ Main Loop - Process New Files
def process_incoming_files(reverse=False):
    """Processes all text files in the incoming directory."""
    for file in os.listdir(INCOMING_DIR):
        if file.endswith(".txt"):
            file_path = os.path.join(INCOMING_DIR, file)
            convert_text(file_path, reverse)
            os.rename(file_path, os.path.join(PROCESSED_DIR, file))  # Move original to processed
            print(f"🔥 Conversion Complete for: {file}")

# ✅ Run the Conversion
if __name__ == "__main__":
    process_incoming_files()
