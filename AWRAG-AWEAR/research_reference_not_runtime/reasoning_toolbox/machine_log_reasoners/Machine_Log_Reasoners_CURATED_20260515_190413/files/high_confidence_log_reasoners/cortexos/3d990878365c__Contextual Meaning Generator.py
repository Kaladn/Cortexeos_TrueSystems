import json
import os
import spacy
from transformers import AutoTokenizer
from nltk.corpus import wordnet
from pymongo import MongoClient

# Load NLP models
nlp = spacy.load("en_core_web_sm")  # Small but efficient
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["CortexBERT"]
collection = db["MeaningGraph"]

# Paths
INPUT_DIR = r"A:\Compression Engine\dictionary"
OUTPUT_DIR = r"A:\Compression Engine\meaning_graph"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Function to get synonyms & antonyms
def get_synonyms_antonyms(word):
    synonyms, antonyms = set(), set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())
            if lemma.antonyms():
                antonyms.add(lemma.antonyms()[0].name())
    return list(synonyms), list(antonyms)

# Function to extract prefixes, roots, and suffixes
def analyze_word_structure(word):
    doc = nlp(word)
    tokenized = tokenizer.tokenize(word)
    prefix, root, suffix = None, word, None
    
    if "-" in word:  # Handling hyphenated words
        parts = word.split("-")
        prefix, root = parts[0], "-".join(parts[1:])
    
    return {
        "tokenized": tokenized,
        "prefix": prefix,
        "root": root,
        "suffix": suffix
    }

# Process each file
json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]

print(f"🚀 Found {len(json_files)} JSON files. Processing...")

for file_name in json_files:
    input_path = os.path.join(INPUT_DIR, file_name)
    output_path = os.path.join(OUTPUT_DIR, file_name)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            dictionary = json.load(f)

        print(f"✅ Processing {file_name} ({len(dictionary)} words)...")

        processed_data = {}
        for word, details in dictionary.items():
            word_structure = analyze_word_structure(word)
            synonyms, antonyms = get_synonyms_antonyms(word)
            
            processed_data[word] = {
                "hex": details["hex"],
                "binary": details["binary"],
                "tokenized": word_structure["tokenized"],
                "prefix": word_structure["prefix"],
                "root": word_structure["root"],
                "suffix": word_structure["suffix"],
                "synonyms": synonyms,
                "antonyms": antonyms,
                "semantic_weight": len(synonyms) / 10,  # Scaled importance score
                "related_words": []  # Will be filled later
            }

            # Store in MongoDB
            collection.update_one({"word": word}, {"$set": processed_data[word]}, upsert=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=4, ensure_ascii=False)

        print(f"✅ Saved processed file: {output_path}")

    except Exception as e:
        print(f"⚠️ Error processing {file_name}: {e}")

print("🚀 Processing Complete! All files saved in:", OUTPUT_DIR)
