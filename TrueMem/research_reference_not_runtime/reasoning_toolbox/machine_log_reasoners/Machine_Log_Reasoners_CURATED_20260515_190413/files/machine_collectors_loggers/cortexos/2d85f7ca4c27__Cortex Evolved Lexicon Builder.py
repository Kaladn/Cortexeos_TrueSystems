import os
import re
import requests
import pymongo
from tqdm import tqdm

# MongoDB Connection
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "word_database"
COLLECTION_NAME = "words"

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
words_collection = db[COLLECTION_NAME]

# ✅ Ensure Index for Fast Lookups
words_collection.create_index("word", unique=True)

# 🏥 Load External Datasets (Medical, Scientific, Historical, Educational)
def load_external_sources():
    sources = {
        "medical": "A:/WIKI SCRAPED/EXTRACTED/mesh_english_words.txt",
        "scientific": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
        "historical": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
        "educational": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english.txt"
    }

    word_sets = {category: set() for category in sources}

    for category, source in sources.items():
        if source.startswith("http"):
            response = requests.get(source)
            if response.status_code == 200:
                word_sets[category].update(response.text.split())
        elif os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                word_sets[category].update(line.strip().lower() for line in f)

    return word_sets

# 📝 Process and Insert Words into MongoDB
def process_and_store_words():
    CLEANED_WORDS_DIR = "A:/WIKI SCRAPED/WORD_ANALYSIS/FINAL_ALPHA"
    external_data = load_external_sources()
    
    all_words = []
    
    # 📂 Process A-Z Word Files
    for file in tqdm(os.listdir(CLEANED_WORDS_DIR), desc="📂 Processing Word Files"):
        if not file.endswith(".txt"):
            continue
        file_path = os.path.join(CLEANED_WORDS_DIR, file)

        with open(file_path, "r", encoding="utf-8") as f:
            for word in f:
                word = word.strip().lower()
                if not word or not word.isalpha():
                    continue
                
                # 🔎 Determine Category
                category = "general"
                citations = ""
                for cat, words_set in external_data.items():
                    if word in words_set:
                        category = cat
                        citations = f"{cat}_dataset"
                
                # 🛠 Structure the Word Document for MongoDB
                word_entry = {
                    "word": word,
                    "symbol": "NA",
                    "neuron": "Pending",
                    "category": category,
                    "citations": citations
                }
                
                all_words.append(word_entry)

    # 🚀 **Bulk Insert Words into MongoDB**
    if all_words:
        words_collection.insert_many(all_words, ordered=False)
        print(f"✅ Inserted {len(all_words)} words into MongoDB!")

# 🔥 Run the Pipeline
if __name__ == "__main__":
    print("🚀 Processing Words and Storing in MongoDB...")
    process_and_store_words()
    print("✅ **Word Processing Complete!**")
