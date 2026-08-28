import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk
import re
import nltk
from collections import defaultdict
from nltk.tokenize import word_tokenize
from tika import parser  # For parsing PDFs and Word Docs
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

nltk.download('punkt')

def init_db(db_path="word_relationships.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            word TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY,
            word1_id INTEGER,
            word2_id INTEGER,
            frequency INTEGER DEFAULT 1,
            FOREIGN KEY(word1_id) REFERENCES words(id),
            FOREIGN KEY(word2_id) REFERENCES words(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            word_id INTEGER,
            source TEXT,
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
    """)
    conn.commit()
    conn.close()

def process_text(text, source, db_path="word_relationships.db"):
    words = word_tokenize(text.lower())
    words = [re.sub(r'[^a-zA-Z0-9-]', '', w) for w in words if w.isalnum() or '-' in w]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    word_ids = {}
    for i in range(len(words) - 1):
        word1, word2 = words[i], words[i+1]
        if word1 not in word_ids:
            cursor.execute("INSERT OR IGNORE INTO words (word) VALUES (?)", (word1,))
            cursor.execute("SELECT id FROM words WHERE word = ?", (word1,))
            word_ids[word1] = cursor.fetchone()[0]
        if word2 not in word_ids:
            cursor.execute("INSERT OR IGNORE INTO words (word) VALUES (?)", (word2,))
            cursor.execute("SELECT id FROM words WHERE word = ?", (word2,))
            word_ids[word2] = cursor.fetchone()[0]
        cursor.execute("INSERT OR IGNORE INTO relationships (word1_id, word2_id, frequency) VALUES (?, ?, 1)", 
                       (word_ids[word1], word_ids[word2]))
        cursor.execute("UPDATE relationships SET frequency = frequency + 1 WHERE word1_id = ? AND word2_id = ?", 
                       (word_ids[word1], word_ids[word2]))
        cursor.execute("INSERT OR IGNORE INTO sources (word_id, source) VALUES (?, ?)", 
                       (word_ids[word1], source))
    conn.commit()
    conn.close()

def parse_file(filepath):
    ext = os.path.splitext(filepath)[-1].lower()
    if ext in ['.txt', '.md', '.csv', '.json']:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext in ['.pdf', '.docx', '.odt']:
        return parser.from_file(filepath)['content']
    elif ext in ['.xml', '.html', '.htm']:
        with open(filepath, 'r', encoding='utf-8') as f:
            return BeautifulSoup(f.read(), 'html.parser').get_text()
    return ""

def load_files_from_folder():
    folder_path = filedialog.askdirectory()
    if not folder_path:
        return
    for root, _, files in os.walk(folder_path):
        for file in files:
            filepath = os.path.join(root, file)
            text = parse_file(filepath)
            if text:
                process_text(text, filepath)

def load_single_file():
    filepath = filedialog.askopenfilename()
    if not filepath:
        return
    text = parse_file(filepath)
    if text:
        process_text(text, filepath)

def show_word_relationships():
    def on_word_select(event):
        selected_word = word_list.get(word_list.curselection())
        conn = sqlite3.connect("word_relationships.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w2.word, r.frequency FROM relationships r
            JOIN words w1 ON r.word1_id = w1.id
            JOIN words w2 ON r.word2_id = w2.id
            WHERE w1.word = ?
            ORDER BY r.frequency DESC
        """, (selected_word,))
        results = cursor.fetchall()
        conn.close()
        result_box.delete(0, tk.END)
        for word, freq in results:
            result_box.insert(tk.END, f"{word} ({freq})")

    root = tk.Tk()
    root.title("Word Relationship Viewer")
    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    word_list = tk.Listbox(frame)
    word_list.pack(side=tk.LEFT, fill=tk.Y)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=word_list.yview)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y)
    word_list.config(yscrollcommand=scrollbar.set)
    result_box = tk.Listbox(root)
    result_box.pack(fill=tk.BOTH, expand=True)
    word_list.bind("<<ListboxSelect>>", on_word_select)
    conn = sqlite3.connect("word_relationships.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words ORDER BY word ASC")
    for word in cursor.fetchall():
        word_list.insert(tk.END, word[0])
    conn.close()
    root.mainloop()

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("Document Processor")
    tk.Button(root, text="Process Folder", command=load_files_from_folder).pack()
    tk.Button(root, text="Process Single File", command=load_single_file).pack()
    tk.Button(root, text="View Relationships", command=show_word_relationships).pack()
    root.mainloop()
