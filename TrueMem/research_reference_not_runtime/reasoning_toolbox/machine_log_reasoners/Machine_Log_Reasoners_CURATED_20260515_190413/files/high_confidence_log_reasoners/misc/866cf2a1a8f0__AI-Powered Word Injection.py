import os
import re
import requests
import nltk
from tqdm import tqdm
from bs4 import BeautifulSoup
from transformers import pipeline

# 📌 File Paths
ALPHA_FOLDER = "C:/AI SYMBOLIS WORK/alphabetized_words"
MISSING_WORDS_FILE = "C:/AI SYMBOLIS WORK/missing_words.txt"
NEW_WORDS_FILE = "C:/AI SYMBOLIS WORK/newly_added_words.txt"

# 🛠 AI Setup (RoBERTa + BERT)
print("🔄 Loading AI Models (RoBERTa & BERT)...")
roberta_model = pipeline("fill-mask", model="roberta-base")
bert_model = pipeline("fill-mask", model="bert-base-uncased")

# 🏛️ Alternative Scientific Sources
SCIENTIFIC_WORD_SOURCES = [
    "https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists",
    "https://pubmed.ncbi.nlm.nih.gov/",
]

# 🔍 Function to Check if a Word Exists in Current Dataset
def is_word_in_dataset(word):
    first_letter = word[0].upper()
    file_path = os.path.join(ALPHA_FOLDER, f"{first_letter}.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return word in f.read().splitlines()
    return False

# 🤖 AI-Powered Word Reasoning (Fixing the `[MASK]` Issue)
def ai_validate_word(word):
    """Uses AI to determine if a word is likely real by inserting it into a sentence."""
    masked_sentence = f"The meaning of {word} is <mask>."
    try:
        roberta_prediction = any(entry["token_str"] == word for entry in roberta_model(masked_sentence))
        bert_prediction = any(entry["token_str"] == word for entry in bert_model(masked_sentence))
        return roberta_prediction or bert_prediction
    except:
        return False

# 🔗 Web Scraper for Scientific Words (New Sources)
def scrape_scientific_words():
    new_words = set()
    for url in SCIENTIFIC_WORD_SOURCES:
        print(f"🔍 Scraping: {url}")
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, "html.parser")
            words = re.findall(r"\b[a-zA-Z]{6,}\b", soup.text)  # Only long words (scientific terms)
            for word in words:
                word = word.lower()
                if not is_word_in_dataset(word) and ai_validate_word(word):
                    new_words.add(word)
        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")
    
    return new_words

# 🚀 Run the Word Injection Process
print("🔬 Extracting missing words from scientific sources...")
missing_words = scrape_scientific_words()

# 📌 Save New Words
with open(MISSING_WORDS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(missing_words)))

# 🛠 Patch Missing Words into Alphabetized Files
print("🛠 Injecting missing words into alphabetized files...")
for word in missing_words:
    first_letter = word[0].upper()
    file_path = os.path.join(ALPHA_FOLDER, f"{first_letter}.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{word}\n")

with open(NEW_WORDS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(missing_words)))

print(f"\n✅ Added {len(missing_words)} new words to Symbolis!")
print(f"📝 Missing words saved to: {MISSING_WORDS_FILE}")
print(f"📂 Newly added words saved to: {NEW_WORDS_FILE}")
