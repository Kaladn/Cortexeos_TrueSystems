import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# **CONFIGURATION - Make sure paths are correct**
TEXT_DIR = r"C:\Users\mydyi\Desktop\split_conversations"
FAISS_INDEX_PATH = r"C:\Users\mydyi\Desktop\Conversation splitter\faiss_index.bin"
MESSAGES_PKL_PATH = r"C:\Users\mydyi\Desktop\Conversation splitter\faiss_index_messages.pkl"

# **LOAD SBERT MODEL**
print("🔄 Loading SBERT Model...")
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# **COLLECT ALL TEXT FILES**
messages = []
file_list = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]
print(f"📂 Found {len(file_list)} text files.")

for file_name in file_list:
    with open(os.path.join(TEXT_DIR, file_name), "r", encoding="utf-8") as f:
        messages.extend(f.readlines())  # Read line by line

# **CHECK IF DATA EXISTS**
if not messages:
    print("❌ ERROR: No text data found.")
    exit()

print(f"📜 Loaded {len(messages)} messages.")

# **CONVERT MESSAGES TO EMBEDDINGS**
print("🔄 Encoding messages into embeddings...")
embeddings = MODEL.encode(messages, convert_to_numpy=True)

# **CREATE FAISS INDEX**
dimension = embeddings.shape[1]
faiss_index = faiss.IndexFlatL2(dimension)
faiss_index.add(embeddings)

# **SAVE FAISS INDEX**
print("💾 Saving FAISS index...")
faiss.write_index(faiss_index, FAISS_INDEX_PATH)

# **SAVE MESSAGES**
print("💾 Saving message data...")
with open(MESSAGES_PKL_PATH, "wb") as f:
    pickle.dump(messages, f)

print("✅ FAISS index and messages successfully rebuilt!")
