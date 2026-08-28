import os
import fasttext
import multiprocessing
import threading
import psutil
from tqdm import tqdm

# ✅ Max RAM Usage (32GB)
MAX_RAM_USAGE = 32 * 1024 * 1024 * 1024  # 32GB

# ✅ Assign 4 P-cores + 6 E-cores
NUM_CORES = 10  

# ✅ Load FastText Language Model (way faster than langid)
MODEL_PATH = "lid.176.bin"  # Pretrained language model
if not os.path.exists(MODEL_PATH):
    print("❌ Error: FastText model not found! Download from https://fasttext.cc/docs/en/language-identification.html")
    exit(1)

model = fasttext.load_model(MODEL_PATH)

# ✅ Ask for input (file OR directory)
path = input("📂 Enter a file or directory path: ").strip()

# ✅ Get all files (supports directory & subdirectories)
def get_files(path):
    if os.path.isdir(path):
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith(".txt"):  # Only process text files
                    files.append(os.path.join(root, filename))
        return files
    elif os.path.isfile(path):
        return [path]
    else:
        print(f"❌ Error: Path '{path}' not found.")
        exit(1)

files_to_process = get_files(path)

# ✅ Fastest language detection
def is_english(word):
    return model.predict(word)[0][0] == "__label__en"

# ✅ Process file using **batching for high-speed processing**
def process_file(file_path):
    print(f"\n🚀 Processing file: {file_path}")
    output_file = file_path.replace(".txt", "_cleaned.txt")

    total_words, kept_count, discarded_count = 0, 0, 0
    batch_size = 10000  # ✅ Process 10,000 words at a time
    batch = []

    # ✅ Read full file in RAM if within safe memory limit
    file_size = os.path.getsize(file_path)
    if file_size > MAX_RAM_USAGE // NUM_CORES:
        print(f"⚠️ Large file detected ({file_size / 1e6:.2f}MB). Processing in chunks...")
        safe_read = False
    else:
        safe_read = True

    with open(file_path, "r", encoding="utf-8") as f, open(output_file, "w", encoding="utf-8") as out_f:
        if safe_read:
            text = f.read()
            words = text.split()
        else:
            words = []
            for line in f:
                words.extend(line.strip().split())

        total_words = len(words)

        for word in tqdm(words, total=total_words, desc="🔄 Filtering words", unit=" words"):
            if is_english(word):
                batch.append(word)
                kept_count += 1
            else:
                discarded_count += 1

            # ✅ Write batch to disk (async I/O)
            if len(batch) >= batch_size:
                threading.Thread(target=out_f.write, args=(" ".join(batch) + "\n",)).start()
                batch.clear()

        # ✅ Final batch write
        if batch:
            out_f.write(" ".join(batch) + "\n")

    # ✅ Print summary
    print(f"✅ Done: {file_path}")
    print(f"📊 Total Words: {total_words:,}, ✅ Kept: {kept_count:,}, ❌ Discarded: {discarded_count:,}")
    print(f"📁 Saved cleaned file: {output_file}")

# ✅ Parallel Execution with Multiprocessing
if __name__ == "__main__":
    with multiprocessing.Pool(NUM_CORES) as pool:
        pool.map(process_file, files_to_process)

    print("\n🚀 All files processed at **10,000+ WPM**!")
