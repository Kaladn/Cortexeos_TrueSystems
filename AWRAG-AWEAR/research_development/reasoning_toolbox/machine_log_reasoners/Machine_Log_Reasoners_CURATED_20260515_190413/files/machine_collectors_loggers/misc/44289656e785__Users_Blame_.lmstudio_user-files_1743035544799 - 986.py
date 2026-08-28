import json
import os
import re
from tqdm import tqdm

# Function to load JSONL or JSON files from current directory
def load_json_data(directory):
    data = []
    for file_name in os.listdir(directory):
        if file_name.endswith(".jsonl") or file_name.endswith(".json"):
            file_path = os.path.join(directory, file_name)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                if file_name.endswith(".jsonl"):
                    for line in file:
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                else:
                    try:
                        data.extend(json.load(file))
                    except json.JSONDecodeError:
                        continue
    return data

# Function to clean and process a single word
def clean_word(word):
    word = word.strip().lower()
    if not word:
        return None
    if any(char.isdigit() for char in word):
        return None
    word = re.sub(r'[^a-zA-Z\-]', '', word)  # Remove anything that’s not a letter or dash
    if len(word) < 2:
        return None
    return word

# Function to generate the unique cleaned word list
def generate_word_list(data):
    word_set = set()
    for entry in tqdm(data, desc="Extracting words"):
        completion = entry.get("completion", "")
        words = re.findall(r'\\b\\w+\\b', completion.lower())
        for word in words:
            cleaned = clean_word(word)
            if cleaned:
                word_set.add(cleaned)
    return sorted(list(word_set))

# Save word list to JSON
def save_word_list(word_list, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(word_list, f, indent=4)

# Main script execution
def main():
    directory = os.getcwd()
    print(f"Loading JSON/JSONL data from {directory}...")
    data = load_json_data(directory)

    print("Generating and cleaning word list...")
    word_list = generate_word_list(data)

    print(f"Saving cleaned word list with {len(word_list)} words...")
    save_word_list(word_list, os.path.join(directory, "cleaned_word_list.json"))
    print("✅ Done!")

if __name__ == "__main__":
    main()
