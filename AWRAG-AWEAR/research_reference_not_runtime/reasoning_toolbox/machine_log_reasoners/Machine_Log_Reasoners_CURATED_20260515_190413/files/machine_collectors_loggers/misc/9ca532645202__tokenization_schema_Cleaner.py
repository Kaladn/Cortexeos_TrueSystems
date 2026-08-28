import os
import json
import tqdm
import re

def load_jsonl_from_directory(directory):
    """
    Load all JSONL files from the directory.
    """
    data = []
    for filename in os.listdir(directory):
        if filename.endswith(".jsonl"):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in tqdm.tqdm(file.readlines(), desc=f"Processing {filename}", unit="line"):
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Error decoding line in {filename}: {e}")
    return data

def generate_word_list(data):
    """
    Generate a list of unique words from JSON data.
    Filters out words that contain numbers.
    """
    word_list = set()
    for entry in tqdm.tqdm(data, desc="Processing entries", unit="entry"):
        completion = entry.get("completion", "")
        words = completion.split()  # Split by spaces (you can adjust based on your tokenization needs)
        
        # Filter out words containing numbers using regex
        for word in words:
            if not re.search(r'\d', word):  # This will exclude words containing any numbers
                word_list.add(word)
    return word_list

def main():
    # Get the directory where the script is located
    directory = os.path.dirname(os.path.realpath(__file__))
    
    # Load JSONL files from the directory
    print("Loading JSONL files...")
    data = load_jsonl_from_directory(directory)
    
    # Generate a word list
    print("\nGenerating word list...")
    word_list = generate_word_list(data)

    # Write the word list to a JSON file
    output_file = os.path.join(directory, "word_list.json")
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(list(word_list), file, ensure_ascii=False, indent=4)

    print(f"\nWord list has been saved to {output_file}")
    
if __name__ == "__main__":
    main()
