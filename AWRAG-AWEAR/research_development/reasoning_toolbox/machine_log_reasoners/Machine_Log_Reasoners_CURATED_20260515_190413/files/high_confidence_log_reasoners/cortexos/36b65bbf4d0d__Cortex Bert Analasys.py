import os
import json
import sqlite3
import re
from collections import Counter
import multiprocessing
from transformers import pipeline

# Load CortexBERT's NNLP Pipeline
cortexbert_nnlp = pipeline("feature-extraction", model="CortexBERT")

# Define file paths (Modify this to your directory)
DATA_DIR = r"C:\Users\mydyi\OneDrive\Documents\Desktop\Symbolis Mainport\Large Databases-Compressed\05b6e602532b3d075340cbcc28a8c83e4d269fb9a6179f9cc2c87c077f3584ee-2025-02-24-00-40-41-097942c19e8841ec9f1af4fe76aade1a"
REPORT_FILE = os.path.join(DATA_DIR, "chat_analysis_report.txt")
DB_FILE = os.path.join(DATA_DIR, "chat_analysis.db")

# Function to load and parse large JSON files efficiently
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

# Step 1: Extract structured conversation from conversations.json
def extract_conversations():
    json_file = os.path.join(DATA_DIR, "conversations.json")
    if not os.path.exists(json_file):
        return []
    
    data = load_json(json_file)
    messages = []
    for conversation in data:
        for message in conversation.get("messages", []):
            messages.append({
                "role": message.get("role", "unknown"),
                "text": message.get("content", "")
            })
    return messages

# Step 2: Process text using CortexBERT NNLP

def process_text(text):
    return cortexbert_nnlp(text)  # Extracts deep linguistic features

# Step 3: Parallel processing for conversation analysis
def process_conversations(messages):
    print("🔄 Processing conversations with CortexBERT NNLP...")
    with multiprocessing.Pool(processes=4) as pool:
        embeddings = pool.map(process_text, [msg["text"] for msg in messages])
    
    return embeddings

# Step 4: Save structured data in SQLite
def save_to_database(messages):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            message TEXT
        )
    """)
    
    cursor.executemany("INSERT INTO chat (role, message) VALUES (?, ?)", [(m["role"], m["text"]) for m in messages])
    
    conn.commit()
    conn.close()
    print(f"✅ Chat stored in SQLite database: {DB_FILE}")

# Step 5: Generate Report
def generate_report(messages):
    word_counts = Counter()
    for entry in messages:
        words = re.findall(r'\w+', entry["text"].lower())
        word_counts.update(words)
    
    most_common_words = word_counts.most_common(50)
    
    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write("===== Chat Analysis Report =====\n")
        file.write(f"Total Messages: {len(messages)}\n\n")
        file.write("===== Most Common Words =====\n")
        for word, count in most_common_words:
            file.write(f"{word}: {count}\n")
    
    print(f"📄 Report saved: {REPORT_FILE}")

# Main Execution
if __name__ == "__main__":
    chat_messages = extract_conversations()
    if not chat_messages:
        print("⚠ No conversations found!")
    else:
        embeddings = process_conversations(chat_messages)
        save_to_database(chat_messages)
        generate_report(chat_messages)
    print("🚀 CortexBERT Chat Analysis Complete!")
