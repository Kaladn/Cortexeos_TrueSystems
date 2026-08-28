import os
import re
import json
import multiprocessing
import hashlib
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import Counter, defaultdict
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm
import schedule
import textblob
import tkinter as tk
from tkinter import messagebox, filedialog

# ✅ UI Setup for User Interaction
def setup_ui():
    root = tk.Tk()
    root.title("Symbolis Intelligence System - Setup Wizard")
    root.geometry("600x400")
    
    def select_drive():
        global BASE_DIR
        BASE_DIR = filedialog.askdirectory(title="Select Storage Location")
        if BASE_DIR:
            os.makedirs(BASE_DIR, exist_ok=True)
            messagebox.showinfo("Success", f"All data will reside in {BASE_DIR}")
    
    def select_dictionary():
        global DICTIONARY_STORAGE_PATH
        dictionary_path = filedialog.askopenfilename(title="Select Pre-Tokenized Dictionary File")
        DICTIONARY_STORAGE_PATH = os.path.join(BASE_DIR, "TokenizedDictionary.json")
        if os.path.exists(dictionary_path):
            with open(dictionary_path, "r", encoding="utf-8") as src, open(DICTIONARY_STORAGE_PATH, "w", encoding="utf-8") as dest:
                dest.write(src.read())
            messagebox.showinfo("Success", "Dictionary successfully copied and formatted!")
        else:
            messagebox.showerror("Error", "Dictionary file not found! Please check your input.")
    
    tk.Button(root, text="Select Storage Location", command=select_drive).pack(pady=10)
    tk.Button(root, text="Select Dictionary File", command=select_dictionary).pack(pady=10)
    tk.Button(root, text="Start Setup", command=root.destroy).pack(pady=20)
    root.mainloop()

setup_ui()

# ✅ MongoDB Connection
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "SymbolisDB"
TOKENIZED_DICTIONARY_COLLECTION = "TokenizedDictionary"
EXO_COLLECTION = "ExoAI_Neurons"
CITATIONS_COLLECTION = "Citations"
BLOCKED_SITES_COLLECTION = "BlockedSites"
CREDENTIALS_COLLECTION = "SiteCredentials"
SOCIAL_SEEK_COLLECTION = "SocialSeek"
PENDING_WORDS_COLLECTION = "PendingWords"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
tokenized_dictionary_collection = db[TOKENIZED_DICTIONARY_COLLECTION]
exo_collection = db[EXO_COLLECTION]
citations_collection = db[CITATIONS_COLLECTION]
blocked_sites_collection = db[BLOCKED_SITES_COLLECTION]
credentials_collection = db[CREDENTIALS_COLLECTION]
social_seek_collection = db[SOCIAL_SEEK_COLLECTION]
pending_words_collection = db[PENDING_WORDS_COLLECTION]

# ✅ Data Directories
RAW_DATA_DIR = os.path.join(BASE_DIR, "Symbolis_RawData")
PROCESSED_DIR = os.path.join(BASE_DIR, "Symbolis_Processed")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")

# ✅ Create Directories If Missing
for directory in [RAW_DATA_DIR, PROCESSED_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ✅ Load Dictionary into RAM for Instantaneous Conversions
tokenized_dict = {}
def load_dictionary():
    global tokenized_dict
    with open(DICTIONARY_STORAGE_PATH, "r", encoding="utf-8") as file:
        tokenized_dict = json.load(file)
    print("✅ Tokenized dictionary loaded into RAM.")

load_dictionary()

# ✅ Function to Store Credentials
def store_credentials():
    """User inputs credentials for websites requiring authentication."""
    root = tk.Tk()
    root.title("Add Login Credentials")
    root.geometry("400x300")
    
    tk.Label(root, text="Enter Website URL:").pack()
    site_entry = tk.Entry(root, width=40)
    site_entry.pack()
    
    tk.Label(root, text="Enter Username:").pack()
    user_entry = tk.Entry(root, width=40)
    user_entry.pack()
    
    tk.Label(root, text="Enter Password:").pack()
    pass_entry = tk.Entry(root, width=40, show='*')
    pass_entry.pack()
    
    def save_credentials():
        site = site_entry.get()
        username = user_entry.get()
        password = pass_entry.get()
        if site and username and password:
            credentials_collection.insert_one({
                "site": site,
                "username": username,
                "password": password,
                "timestamp": time.time()
            })
            messagebox.showinfo("Success", "Credentials stored successfully!")
            root.destroy()
        else:
            messagebox.showerror("Error", "All fields are required!")
    
    tk.Button(root, text="Save Credentials", command=save_credentials).pack(pady=10)
    root.mainloop()

store_credentials()

# ✅ Function to Retrieve Credentials
def get_site_credentials(url):
    """Fetch stored credentials for a specific website if available."""
    credentials = credentials_collection.find_one({"site": url})
    return credentials if credentials else None

# ✅ Use Pre-Tokenized Dictionary-Only Storage
def tokenize_with_predefined_dict(text):
    """Uses the pre-tokenized dictionary for tokenization and stores only tokens."""
    words = text.split()
    tokenized_text = []
    token_ids = []
    new_words = []
    
    for word in words:
        entry = tokenized_dict.get(word)
        if entry:
            tokenized_text.extend(entry["tokenized"])
            token_ids.extend(entry["token_ids"])
        else:
            new_words.append(word)
            tokenized_text.append(word)
            token_ids.append(-1)  # Unknown token placeholder
    
    if new_words:
        print(f"🚨 Human review required: New words detected - {new_words}")
        pending_words_collection.insert_one({
            "words": new_words,
            "timestamp": time.time()
        })
    
    return tokenized_text, token_ids

# ✅ Store Only Tokens in Database
def store_tokenized_data(source, text):
    """Processes and stores only tokenized representations, flags new words for human review."""
    tokenized_text, token_ids = tokenize_with_predefined_dict(text)
    data_entry = {
        "source": source,
        "tokenized_text": tokenized_text,
        "token_ids": token_ids,
        "timestamp": time.time()
    }
    exo_collection.insert_one(data_entry)
    print(f"✅ Stored tokenized data from {source}")

# ✅ Main Execution
def main():
    print("🚀 Symbolis Intelligence System is now running...")
    while True:
        schedule.run_pending()
        time.sleep(600)  # Check every 10 minutes for scheduled tasks

if __name__ == "__main__":
    main()
