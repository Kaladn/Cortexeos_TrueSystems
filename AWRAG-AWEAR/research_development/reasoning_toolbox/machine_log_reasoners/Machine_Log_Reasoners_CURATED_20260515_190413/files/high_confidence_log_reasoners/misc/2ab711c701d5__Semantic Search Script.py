import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# CONFIGURATION
TEXT_FOLDER = "C:\\Users\\mydyi\\Desktop\\split_conversations"
INDEX_FILE = "faiss_index.bin"
SEARCH_RESULTS_FOLDER = "C:\\Users\\mydyi\\Desktop\\Conversation splitter\\search_results"
os.makedirs(SEARCH_RESULTS_FOLDER, exist_ok=True)

# LOAD SBERT MODEL
print("[1/4] Loading SBERT Model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# LOAD TEXT FILES
print(f"[2/4] Loading text files from: {TEXT_FOLDER}")
text_files = [os.path.join(TEXT_FOLDER, f) for f in os.listdir(TEXT_FOLDER) if f.endswith(".txt")]

if not text_files:
    print("⚠ No text files found! Check your directory.")
    exit()

documents = []
file_sources = []
for file in tqdm(text_files, desc="Processing Files"):
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        documents.extend(lines)
        file_sources.extend([file] * len(lines))

# CHECK IF FAISS INDEX EXISTS
if os.path.exists(INDEX_FILE):
    print("[3/4] Loading existing FAISS Index...")
    index = faiss.read_index(INDEX_FILE)
else:
    print("[3/4] Encoding chat messages...")
    embeddings = model.encode(documents, show_progress_bar=True)
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(np.array(embeddings, dtype=np.float32))
    faiss.write_index(index, INDEX_FILE)

# SEARCH FUNCTION
def search(query, top_k=5):
    print(f"\n🔍 Searching for: {query}")
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding, dtype=np.float32), top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx >= len(documents):
            continue
        results.append({
            "rank": i + 1,
            "text": documents[idx].strip(),
            "source": file_sources[idx]
        })
    
    return results

# GET USER QUERY
query = input("\nEnter search query: ")
results = search(query)

# DISPLAY RESULTS
print("\n🔹 Search Results:")
for res in results:
    print(f"- {res['text']} (Source: {res['source']})")

# SAVE RESULTS TO FILE
output_file = os.path.join(SEARCH_RESULTS_FOLDER, "search_log.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4)

print(f"\n📁 Search results saved to: {output_file}")
