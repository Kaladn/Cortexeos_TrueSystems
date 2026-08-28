import json

# Paths
SYMBOLIS_DICT_FILE = "C:/AI SYMBOLIS WORK/data_scraping/symbolis_dict.json"
INPUT_FILE = "C:/AI SYMBOLIS WORK/output/pg5_symbolis.txt"
NEW_WORDS_FILE = "C:/AI SYMBOLIS WORK/output/missing_words.txt"

# Load Symbolis Dictionary
print("🔄 Loading Symbolis Dictionary...")
with open(SYMBOLIS_DICT_FILE, "r", encoding="utf-8") as f:
    symbolis_dict = json.load(f)

# Read the converted text file
print(f"📖 Scanning file: {INPUT_FILE} for unmapped words...")
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    words = f.read().split()

# Identify unmapped words
unmapped_words = [word for word in words if word not in symbolis_dict]

if unmapped_words:
    print(f"❌ Found {len(unmapped_words)} unmapped words. Saving to {NEW_WORDS_FILE}...")
    with open(NEW_WORDS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(set(unmapped_words)))  # Remove duplicates before saving
    print("✅ Missing words saved! Add them to the Symbolis dictionary.")
else:
    print("✅ No unmapped words found!")
