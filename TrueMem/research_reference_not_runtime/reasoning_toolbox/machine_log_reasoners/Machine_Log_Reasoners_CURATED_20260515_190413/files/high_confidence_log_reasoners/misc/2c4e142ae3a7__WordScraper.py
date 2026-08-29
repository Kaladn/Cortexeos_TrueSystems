import os
import json
import re
import requests
import chardet
from bs4 import BeautifulSoup
from transformers import pipeline
from tqdm import tqdm

# Setup AI models
roberta_model = pipeline("fill-mask", model="roberta-base")
bert_model = pipeline("fill-mask", model="bert-base-uncased")

# Universal file reader
def read_any_file(file_path):
    """Attempt to read any file with auto-detection of encoding and file type."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding']

        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()

        if file_path.endswith(('.html', '.xml', '.htm')):
            content = BeautifulSoup(content, 'html.parser').get_text()

        return content
    except Exception as e:
        print(f"❌ Failed to read {file_path}: {e}")
        return ""

# AI validation
def ai_validate_word(word):
    """Uses AI models to validate if a word is real."""
    masked_sentence = f"The meaning of {word} is <mask>."
    try:
        roberta_prediction = any(entry["token_str"].lower() == word.lower() for entry in roberta_model(masked_sentence))
        bert_prediction = any(entry["token_str"].lower() == word.lower() for entry in bert_model(masked_sentence))
        return roberta_prediction or bert_prediction
    except Exception as e:
        print(f"❌ AI validation error for {word}: {e}")
        return False

# Process entire directory
def scrape_directory(directory):
    all_text = ""
    files = [os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]

    for file_path in tqdm(files, desc="📂 Reading Files"):
        file_content = read_any_file(file_path)
        all_text += "\n" + file_content

    print(f"✅ Collected data from {len(files)} files.")
    return all_text

if __name__ == "__main__":
    dir_path = input("Enter the directory path to scrape: ")
    content = scrape_directory(dir_path)
    print(f"\nFirst 1000 characters collected:\n{content[:1000]}")
