import os
import langid
from tqdm import tqdm  # ✅ Progress bar
import subprocess  # ✅ Runs CortexBERT training script

# ✅ Ask for user input
file_path = input("📂 Enter the full path of the word list file: ").strip()

# ✅ Verify file exists
if not os.path.exists(file_path):
    print(f"❌ Error: File '{file_path}' not found.")
    exit(1)

# ✅ Define output file (same directory, "_cleaned" appended)
output_file = file_path.replace(".txt", "_cleaned.txt")

print(f"\n🚀 Loading file into memory: {file_path}")

# ✅ Load entire file into memory
with open(file_path, "r", encoding="utf-8") as f:
    word_list = f.read().splitlines()  # Load and split all words into a list

total_words = len(word_list)  # Count total words
cleaned_words = []
kept_count = 0
discarded_count = 0

print("🔍 Filtering non-English words...")

# ✅ Process words with a progress bar
for word in tqdm(word_list, total=total_words, desc="⏳ Processing Words", unit="word"):
    if langid.classify(word)[0] == "en":  # Only keep English words
        cleaned_words.append(word)
        kept_count += 1
    else:
        discarded_count += 1

# ✅ Save cleaned word list
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned_words))  # Write all cleaned words at once

# ✅ Summary Output
print("\n✅ Cleaning complete!")
print(f"📊 Total Words Processed: {total_words}")
print(f"✅ English Words Kept: {kept_count}")
print(f"❌ Non-English Words Discarded: {discarded_count}")
print(f"📁 Cleaned word list saved to: {output_file}")

# ✅ Automatically Start Training CortexBERT
print("\n🚀 Starting CortexBERT Training...")

try:
    subprocess.run([
        "C:/Users/mydyi/AppData/Local/Programs/Python/Python313/python.exe",
        "A:/CortexBERT/main.py",
        "--config", "A:/CortexBERT/configs/config.yaml",
        "--train"
    ], check=True)
    print("✅ Training started successfully!")
except subprocess.CalledProcessError as e:
    print(f"❌ Training failed: {e}")
