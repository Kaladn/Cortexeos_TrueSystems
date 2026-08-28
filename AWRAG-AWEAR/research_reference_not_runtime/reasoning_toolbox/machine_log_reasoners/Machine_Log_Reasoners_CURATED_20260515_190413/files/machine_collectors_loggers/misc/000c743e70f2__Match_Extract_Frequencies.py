import os
import pandas as pd

# ✅ Define CSV file directory
csv_folder = r"C:\Users\mydyi\OneDrive\Documents\Desktop\TOKENIZED CSV FILES"

# ✅ Define file paths
csv_files = {
    "encodings": os.path.join(csv_folder, "encodings.csv"),
    "token_ids": os.path.join(csv_folder, "token_ids.csv"),
    "tokens": os.path.join(csv_folder, "tokens.csv"),
    "words": os.path.join(csv_folder, "words.csv")
}

# ✅ Check if files exist before loading
missing_files = []
for name, path in csv_files.items():
    if not os.path.exists(path):
        print(f"❌ ERROR: File not found: {path}")
        missing_files.append(name)
    else:
        print(f"✅ Found: {path}")

# 🚨 Exit if any files are missing
if missing_files:
    print(f"\n🚨 Script stopped. Missing files: {', '.join(missing_files)}")
    exit()

# ✅ Load CSV files into Pandas DataFrames
encodings_df = pd.read_csv(csv_files["encodings"])
token_ids_df = pd.read_csv(csv_files["token_ids"])
tokens_df = pd.read_csv(csv_files["tokens"])
words_df = pd.read_csv(csv_files["words"])

# ✅ Display the first few rows of each DataFrame to confirm correct loading
print("\n📌 Encodings CSV Preview:")
print(encodings_df.head())

print("\n📌 Tokens CSV Preview:")
print(tokens_df.head())

print("\n📌 Token IDs CSV Preview:")
print(token_ids_df.head())

print("\n📌 Words CSV Preview:")
print(words_df.head())

# 🔥 Example Processing: Count Word Frequencies 🔥
# If words.csv contains a column "word", count occurrences of each unique word
if "word" in words_df.columns:
    word_counts = words_df["word"].value_counts().reset_index()
    word_counts.columns = ["Word", "Frequency"]
    print("\n📊 Word Frequency Analysis:")
    print(word_counts.head(10))  # Show top 10 most frequent words
else:
    print("\n⚠️ WARNING: 'word' column not found in words.csv")

print("\n🚀 Script Completed Successfully!")
