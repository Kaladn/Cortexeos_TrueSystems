import os
import numpy as np
from tqdm import tqdm

# **📂 Paths**
BASE_DIR = "A:/WIKI SCRAPED/EXTRACTED"
INPUT_FILE = os.path.join(BASE_DIR, "mesh_english_words.txt")
SORTED_FILE = os.path.join(BASE_DIR, "mesh_sorted_words.txt")
ALPHA_SORTED_FOLDER = os.path.join(BASE_DIR, "ALPHA_SORTED")
CATEGORIZED_FOLDER = os.path.join(BASE_DIR, "CATEGORIZED")

# **✅ Ensure Directories Exist**
os.makedirs(ALPHA_SORTED_FOLDER, exist_ok=True)
os.makedirs(CATEGORIZED_FOLDER, exist_ok=True)

# **🔄 Read & Load Words into RAM (Optimized)**
def load_words():
    """Load words into memory up to a safe limit."""
    words = []
    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        for line in tqdm(infile, desc="🔄 Loading words into RAM", unit="word"):
            word = line.strip()
            if word:
                words.append(word)
    return words

# **⚡ Sort Words in RAM**
def sort_words(words):
    """Sort words quickly using NumPy."""
    print("⚡ Sorting words in RAM...")
    words = np.array(words, dtype="object")
    words.sort()
    return words

# **💾 Save Sorted Words**
def save_sorted_words(words):
    """Save sorted words to the master sorted file."""
    print("💾 Saving sorted words...")
    with open(SORTED_FILE, "w", encoding="utf-8") as outfile:
        for word in tqdm(words, desc="📝 Writing sorted words", unit="word"):
            outfile.write(word + "\n")

# **📂 Organize Words into A-Z Folders**
def split_into_alphabet_files(words):
    """Split words into separate files based on first letter."""
    file_map = {chr(i): open(os.path.join(ALPHA_SORTED_FOLDER, f"{chr(i)}.txt"), "w", encoding="utf-8") for i in range(65, 91)}  # A-Z
    file_map["other"] = open(os.path.join(ALPHA_SORTED_FOLDER, "other.txt"), "w", encoding="utf-8")

    for word in tqdm(words, desc="📂 Splitting words into A-Z files", unit="word"):
        first_letter = word[0].upper()
        if first_letter in file_map:
            file_map[first_letter].write(word + "\n")
        else:
            file_map["other"].write(word + "\n")

    # Close all files
    for f in file_map.values():
        f.close()

# **📂 Categorize Words by Length & Medical Terms**
def categorize_words(words):
    """Save words into categorized lists."""
    medical_terms = []
    long_words = []
    short_words = []
    uncommon_words = []

    for word in tqdm(words, desc="📂 Categorizing words", unit="word"):
        if len(word) > 15:
            long_words.append(word)
        elif len(word) <= 5:
            short_words.append(word)
        if word.startswith(("neuro", "derm", "cardio", "ophth", "gastro", "hyper", "hypo", "therap", "pharm")):
            medical_terms.append(word)
        if len(word) > 8 and word[-3:] in ("ium", "oid", "ase", "gen", "osis", "pathy"):
            uncommon_words.append(word)

    # **💾 Save Categorized Files**
    with open(os.path.join(CATEGORIZED_FOLDER, "medical_terms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(medical_terms) + "\n")

    with open(os.path.join(CATEGORIZED_FOLDER, "long_words.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(long_words) + "\n")

    with open(os.path.join(CATEGORIZED_FOLDER, "short_words.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(short_words) + "\n")

    with open(os.path.join(CATEGORIZED_FOLDER, "uncommon_words.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(uncommon_words) + "\n")

    print("✅ Categorization complete!")

# **🚀 Main Execution**
if __name__ == "__main__":
    words = load_words()
    sorted_words = sort_words(words)
    save_sorted_words(sorted_words)
    split_into_alphabet_files(sorted_words)
    categorize_words(sorted_words)

    print("\n✅ **ALL PROCESSING COMPLETE!**")
