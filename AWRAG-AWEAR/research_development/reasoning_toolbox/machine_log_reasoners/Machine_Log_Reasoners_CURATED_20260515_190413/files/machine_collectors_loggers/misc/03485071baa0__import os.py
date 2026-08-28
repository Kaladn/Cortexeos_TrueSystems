import os
from tqdm import tqdm

# Path to input file
input_file = r"C:\Users\mydyi\Desktop\word_frequencies.txt"

# Create the "tqmd" directory on Desktop
output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "tqmd")
os.makedirs(output_dir, exist_ok=True)

# **LOAD FULL FILE INTO RAM**
print("🚀 Loading file into memory...")
try:
    with open(input_file, "r", encoding="utf-8") as file:
        lines = file.readlines()  # Read entire file into RAM
except FileNotFoundError:
    print(f"❌ Error: File not found at {input_file}")
    exit(1)

total_words = len(lines)  # Total lines for progress bar

# Check if file is empty
if total_words == 0:
    print("❌ Error: The file is empty. Exiting.")
    exit(1)

print(f"✅ Loaded {total_words} words into RAM.")

# **Initialize RAM storage for each letter**
word_buckets = {chr(i): [] for i in range(65, 91)}  # A-Z

# **PROCESSING PHASE - SORTING INTO BUCKETS**
print("⚡ Sorting words into A-Z files...")
for line in tqdm(lines, total=total_words, desc="Sorting Words", unit="word"):
    parts = line.strip().split()
    if len(parts) < 2:
        continue  
    word, frequency = parts[0], parts[1]  
    first_letter = word[0].upper()  

    if "A" <= first_letter <= "Z":  
        word_buckets[first_letter].append(f"{word} {frequency}")

# **WRITING PHASE - BULK WRITING TO DISK**
print("💾 Writing sorted words to files...")
for letter, words in tqdm(word_buckets.items(), desc="Writing Files", unit="file"):
    if words:
        output_path = os.path.join(output_dir, f"{letter}.txt")
        with open(output_path, "w", encoding="utf-8") as out_file:
            out_file.write("\n".join(words))

print(f"\n✅ ALL DONE! {total_words} words processed in record time. Files are in: {output_dir}")
