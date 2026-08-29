import faiss
import numpy as np
import os
from tqdm import tqdm  # ✅ Import progress meter
from sentence_transformers import SentenceTransformer

# Paths
INPUT_DIR = r"C:\Users\mydyi\OneDrive\Documents\Desktop\Symbolis Mainport\Large Databases-Compressed\ChatGPT Historical Data\split_conversations"
OUTPUT_INDEX = r"C:\Users\mydyi\OneDrive\Documents\Desktop\Symbolis Mainport\Large Databases-Compressed\ChatGPT_Historical_Index"

# Load AI Model for Embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")  # ✅ You can use a different model

# ✅ Load and Process Text Files with Progress Bar
all_texts = []
file_list = sorted(os.listdir(INPUT_DIR))

print(f"📂 Found {len(file_list)} files. Processing with FAISS...")

for file_name in tqdm(file_list, desc="📖 Reading Files", unit="file"):
    file_path = os.path.join(INPUT_DIR, file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        all_texts.extend(f.readlines())  # ✅ Add lines to the dataset

# ✅ Convert Text to Embeddings with Progress Bar
print("🔄 Generating Embeddings...")
embeddings = np.array([model.encode(text) for text in tqdm(all_texts, desc="✨ Converting to Embeddings", unit="line")])

# ✅ Build FAISS Index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
print("📡 Indexing Embeddings into FAISS...")
index.add(embeddings)

# ✅ Save FAISS Index
faiss.write_index(index, OUTPUT_INDEX)
print(f"✅ FAISS Index Created & Saved at {OUTPUT_INDEX}")
