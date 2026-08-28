import os
import re
import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk
from collections import defaultdict

# Function to select file or directory
def select_path():
    path = filedialog.askopenfilename(title="Select a File") or filedialog.askdirectory(title="Select a Directory")
    return path

# Function to clean text and extract words
def extract_words(text):
    text = re.sub(r'[^a-zA-Z\s-]', '', text)  # Keep letters and hyphens
    words = text.lower().split()
    return words

# Function to process file(s) and build word relationships
def process_text_files(path):
    word_freq = defaultdict(int)
    word_neighbors = defaultdict(lambda: defaultdict(int))
    
    if os.path.isdir(path):
        files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.txt')]
    else:
        files = [path]
    
    for file in files:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            words = extract_words(f.read())
            for i, word in enumerate(words):
                word_freq[word] += 1
                if i > 0:
                    word_neighbors[word][words[i-1]] += 1  # Previous word
                if i < len(words) - 1:
                    word_neighbors[word][words[i+1]] += 1  # Next word
    
    return word_freq, word_neighbors

# Function to save data into SQLite
def save_to_db(word_freq, word_neighbors):
    conn = sqlite3.connect("word_data.db")
    cur = conn.cursor()
    
    cur.execute("DROP TABLE IF EXISTS words")
    cur.execute("DROP TABLE IF EXISTS neighbors")
    
    cur.execute("""
        CREATE TABLE words (
            word TEXT PRIMARY KEY,
            frequency INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE neighbors (
            word TEXT,
            neighbor TEXT,
            count INTEGER,
            FOREIGN KEY(word) REFERENCES words(word)
        )
    """)
    
    for word, freq in word_freq.items():
        cur.execute("INSERT INTO words (word, frequency) VALUES (?, ?)", (word, freq))
    
    for word, neighbors in word_neighbors.items():
        for neighbor, count in neighbors.items():
            cur.execute("INSERT INTO neighbors (word, neighbor, count) VALUES (?, ?, ?)", (word, neighbor, count))
    
    conn.commit()
    conn.close()

# Function to create GUI for browsing word relationships
def create_gui():
    conn = sqlite3.connect("word_data.db")
    cur = conn.cursor()
    
    def on_word_select(event):
        selected_word = word_listbox.get(word_listbox.curselection())
        cur.execute("SELECT neighbor, count FROM neighbors WHERE word = ? ORDER BY count DESC LIMIT 10", (selected_word,))
        results = cur.fetchall()
        
        neighbor_listbox.delete(0, tk.END)
        for neighbor, count in results:
            neighbor_listbox.insert(tk.END, f"{neighbor} ({count})")
    
    root = tk.Tk()
    root.title("Word Relationship Viewer")
    
    word_listbox = tk.Listbox(root, height=20, width=30)
    word_listbox.grid(row=0, column=0, padx=10, pady=10)
    scrollbar = tk.Scrollbar(root, command=word_listbox.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    word_listbox.config(yscrollcommand=scrollbar.set)
    
    neighbor_listbox = tk.Listbox(root, height=20, width=50)
    neighbor_listbox.grid(row=0, column=2, padx=10, pady=10)
    
    word_listbox.bind("<<ListboxSelect>>", on_word_select)
    
    cur.execute("SELECT word FROM words ORDER BY frequency DESC LIMIT 500")
    words = cur.fetchall()
    for word in words:
        word_listbox.insert(tk.END, word[0])
    
    root.mainloop()

# Run the script
if __name__ == "__main__":
    path = select_path()
    word_freq, word_neighbors = process_text_files(path)
    save_to_db(word_freq, word_neighbors)
    create_gui()
