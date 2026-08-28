import os
import re
import json
import requests
from transformers import pipeline
from bs4 import BeautifulSoup

# Paths
DICTIONARY_FILE = "data/master_dictionary.json"
MISSING_WORDS_FILE = "data/missing_words.txt"

# Load AI Models
roberta_model = pipeline("fill-mask", model="roberta-base")
bert_model = pipeline("fill-mask", model="bert-base-uncased")

def ai_validate_word(word):
    """Uses AI models to validate if a word is real."""
    masked_sentence = f"The meaning of {word} is <mask>."
    try:
        roberta_prediction = any(entry["token_str"] == word for entry in roberta_model(masked_sentence))
        bert_prediction = any(entry["token_str"] == word for entry in bert_model(masked_sentence))
        return roberta_prediction or bert_prediction
    except:
        return False

def scrape_words_from_web():
    """Extracts scientific terms from external sources"""
    url = "https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        print("❌ Failed to retrieve words.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    words = re.findall(r"\b[a-zA-Z]{6,}\b", soup.text)  # Extracts only long words
    return [word.lower() for word in words]

def process_missing_words():
    """Processes missing words with AI verification"""
    missing_words = scrape_words_from_web()
    valid_words = [word for word in missing_words if ai_validate_word(word)]

    # Save newly validated words
    with open(MISSING_WORDS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(valid_words)))

    print(f"✅ Added {len(valid_words)} new words to the dictionary.")

if __name__ == "__main__":
    process_missing_words()
