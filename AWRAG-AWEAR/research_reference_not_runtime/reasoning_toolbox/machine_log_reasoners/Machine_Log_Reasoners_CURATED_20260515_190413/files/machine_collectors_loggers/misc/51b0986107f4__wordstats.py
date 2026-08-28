import os

# File Paths
ALPHA_DIR = "A:/WIKI SCRAPED/WORD_ANALYSIS/FINAL_ALPHA"  # Alphabetized word dataset
STATS_FILE = "A:/WIKI SCRAPED/WORD_ANALYSIS/word_statistics.txt"

# Initialize counters
word_counts = {}
total_words = 0
total_size = 0  # In bytes

# Process A-Z files
for filename in sorted(os.listdir(ALPHA_DIR)):
    if filename.endswith(".txt"):
        file_path = os.path.join(ALPHA_DIR, filename)
        file_size = os.path.getsize(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
            count = len(words)
            word_counts[filename] = count
            total_words += count
            total_size += file_size

# Convert size to MB
total_size_mb = total_size / (1024 * 1024)

# Save to file
with open(STATS_FILE, "w", encoding="utf-8") as f:
    f.write("📊 **Word Count Per Letter:**\n")
    for letter, count in word_counts.items():
        f.write(f"{letter}: {count:,} words\n")
    f.write("\n")
    f.write(f"✅ **Total Words in Dataset:** {total_words:,}\n")
    f.write(f"💾 **Total Dataset Size:** {total_size_mb:.2f} MB\n")

# Print summary
print("\n✅ **Word Count Analysis Complete!**")
print(f"📊 Total Words: {total_words:,}")
print(f"💾 Total Size: {total_size_mb:.2f} MB")
print(f"📂 Statistics saved to: {STATS_FILE}")
