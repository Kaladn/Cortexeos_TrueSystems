import os
import json
import multiprocessing
import requests
import re
import hashlib
import time
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm
from collections import Counter
import lxml

# ✅ MongoDB Connection
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "SymbolisDB"
COLLECTION_NAME = "ScrapedData"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# ✅ Data Directories
BASE_DIR = "C:/AI SYMBOLIS WORK/Data"
RAW_DATA_DIR = os.path.join(BASE_DIR, "Symbolis_RawData")
PROCESSED_DIR = os.path.join(BASE_DIR, "Symbolis_Processed")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")

# ✅ Create Directories If Missing
for directory in [RAW_DATA_DIR, PROCESSED_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ✅ Academic & Gov Sources
TARGET_SITES = [
    "https://www.ncbi.nlm.nih.gov/",
    "https://arxiv.org/",
    "https://catalog.data.gov/dataset",
    "https://data.nasa.gov/",
    "https://patents.google.com/",
    "https://www.sec.gov/edgar.shtml"
]

# ✅ Neurologic Hashing for Pointer System
def generate_pointer(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]

# ✅ Extract Citations
def extract_citations(text):
    citations = re.findall(r'\((.*?)\)', text)
    return [c for c in citations if len(c) > 5]

# ✅ Word Frequency Tracker
def track_new_words(text):
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return Counter(words)

# ✅ Extract & Follow Links
def get_internal_links(soup, base_url):
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith("/"):
            href = base_url + href
        if base_url in href:
            links.add(href)
    return list(links)

# ✅ Scraping Function (Deep Recursive)
def scrape_website(url, depth=3, visited=set()):
    if depth == 0 or url in visited:
        return
    visited.add(url)
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text_content = " ".join(paragraphs)
        
        if text_content:
            citations = extract_citations(text_content)
            word_freq = track_new_words(text_content)
            data = {
                "url": url,
                "pointer": generate_pointer(url),
                "content": text_content,
                "citations": citations,
                "word_frequencies": dict(word_freq),
                "metadata": {
                    "length": len(text_content),
                    "timestamp": time.time(),
                    "new_words": len(word_freq),
                    "total_words": sum(word_freq.values()),
                }
            }
            collection.insert_one(data)
            print(f"✅ Scraped & Stored: {url} - {len(text_content)} chars")
        else:
            print(f"⚠️ No text found: {url}")
        
        # Follow & Scrape Internal Links
        for link in get_internal_links(soup, url):
            scrape_website(link, depth-1, visited)
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

# ✅ Multi-Threaded Scraping Execution
def scrape_all_sites():
    with multiprocessing.Pool(processes=6) as pool:
        pool.map(scrape_website, TARGET_SITES)
    print("🔥 **All sites scraped & stored!**")

# ✅ Process Raw Data & Categorize
def process_text_files():
    text_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".txt")]
    if not text_files:
        print("⚠️ No text files found. Generating sample files...")
        for i in range(3):
            sample_path = os.path.join(RAW_DATA_DIR, f"sample_{i+1}.txt")
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write(f"Sample text data {i+1}")
        return process_text_files()
    
    for file in tqdm(text_files, desc="🚀 Processing Text Files"):
        file_path = os.path.join(RAW_DATA_DIR, file)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if content:
            citations = extract_citations(content)
            word_freq = track_new_words(content)
            doc = {
                "filename": file,
                "content": content,
                "pointer": generate_pointer(file),
                "citations": citations,
                "word_frequencies": dict(word_freq),
                "metadata": {
                    "length": len(content),
                    "timestamp": time.time(),
                    "new_words": len(word_freq),
                    "total_words": sum(word_freq.values()),
                }
            }
            collection.insert_one(doc)
            processed_path = os.path.join(PROCESSED_DIR, file)
            if os.path.exists(processed_path):
                os.remove(processed_path)
            os.rename(file_path, processed_path)
    print("✅ **Text Processing Complete!**")

# ✅ Run Full Symbolis Intelligence Pipeline
def symbolis_intelligence_engine():
    print("🚀 Starting GOD-TIER Symbolis Data Scraper...")
    scrape_all_sites()
    process_text_files()
    print("🔥 **Symbolis Intelligence System Fully Operational!** 🔥")

if __name__ == "__main__":
    symbolis_intelligence_engine()