import os
import json
import hashlib
import re
from datetime import datetime
from pymongo import MongoClient
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import spacy
from spacy.tokens import Doc
import PyPDF2  # For PDFs
from docx import Document  # For Word docs
import pytesseract  # For OCR on images
from PIL import Image  # To handle image files

# MongoDB Setup
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "ExoAI"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
neurons_collection = db["Neurons"]  # Citations and content
dictionary_collection = db["Dictionary"]  # Tokenized dictionary
pending_words_collection = db["PendingWords"]  # New words for review

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load Dictionary into RAM (10M+ words)
tokenized_dict = {}
def load_dictionary():
    global tokenized_dict
    # Assuming dictionary is in MongoDB; adjust if it’s a JSON file
    dictionary_data = dictionary_collection.find()
    for entry in dictionary_data:
        tokenized_dict[entry["word"]] = {
            "tokenized": entry["tokenized"],
            "token_ids": entry["token_ids"]
        }
    logging.info(f"Loaded {len(tokenized_dict)} words into RAM.")

# Custom Spacy Tokenizer Using Your Dictionary
class CustomTokenizer:
    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, text):
        words = re.findall(r'\w+', text.lower())
        tokens = []
        for word in words:
            entry = tokenized_dict.get(word)
            if entry:
                tokens.extend(entry["tokenized"])
            else:
                tokens.append(word)  # Fallback for unknown words
        return Doc(self.vocab, words=tokens)

nlp = spacy.blank("en")  # Blank English model
nlp.tokenizer = CustomTokenizer(nlp.vocab)
load_dictionary()  # Load dictionary before using tokenizer

# Tokenize and Track New Words
def tokenize_text(text):
    doc = nlp(text)
    tokenized_text = [token.text for token in doc]
    token_ids = []
    new_words = []
    
    for word in re.findall(r'\w+', text.lower()):  # Original words for ID lookup
        entry = tokenized_dict.get(word)
        if entry:
            token_ids.extend(entry["token_ids"])
        else:
            new_words.append(word)
            token_ids.append(-1)  # Placeholder for unknown
    
    if new_words:
        pending_words_collection.insert_one({
            "words": new_words,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        logging.info(f"New words detected for review: {new_words}")
    
    return tokenized_text, token_ids

# Web Scraping for Brain Data
def scrape_website(url, credentials=None):
    try:
        if credentials:
            response = requests.get(url, auth=(credentials["username"], credentials["password"]))
        else:
            response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        
        # Tokenize with custom dictionary
        tokenized_text, token_ids = tokenize_text(text)
        
        # Extract citation data
        title = soup.title.string if soup.title else url
        author = soup.find("meta", {"name": "author"})["content"] if soup.find("meta", {"name": "author"}) else "Unknown"
        year = datetime.now().year  # Fallback; could scrape meta tags
        
        return {
            "title": title,
            "author": author,
            "year": str(year),
            "source": url,
            "text": text,
            "tokenized_text": tokenized_text,
            "token_ids": token_ids
        }
    except Exception as e:
        logging.error(f"Scraping failed for {url}: {e}")
        return None

# Read Local Files (Text, PDF, Word, Images with Text Layers)
def read_local_file(file_path):
    try:
        text = ""
        file_name = os.path.basename(file_path)
        title = file_name.rsplit(".", 1)[0]  # Remove extension
        author = "Local Author"  # Could infer later
        year = datetime.now().year  # Fallback
        
        ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
        
        if ext == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        
        elif ext == "pdf":
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + " "
        
        elif ext in ["docx", "doc"]:
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + " "
        
        elif ext in ["png", "jpg", "jpeg", "tiff"]:  # OCR for images
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
        
        else:
            logging.warning(f"Unsupported file type: {file_path}")
            return None
        
        if not text.strip():
            logging.warning(f"No text extracted from {file_path}")
            return None
        
        # Tokenize with custom dictionary
        tokenized_text, token_ids = tokenize_text(text)
        
        return {
            "title": title,
            "author": author,
            "year": str(year),
            "source": f"file://{file_path}",
            "text": text,
            "tokenized_text": tokenized_text,
            "token_ids": token_ids
        }
    except Exception as e:
        logging.error(f"Failed to process local file {file_path}: {e}")
        return None

# Generate Digital Signature
def generate_signature(data, sub_context):
    note = sum(ord(char) for char in data["title"]) % 128
    velocity = (len(data["author"]) * 10) % 128
    time = int(data["year"]) % 128
    sub_context_tone = sum(ord(char) for char in sub_context) % 128
    signature = f"{note}-{velocity}-{time}-{sub_context_tone}"
    unique_key = f"{data['title']}-{data['author']}-{data['year']}-{sub_context}"
    return signature, unique_key

# Generate Security Mark
def generate_security_mark(user_id, neuron_data):
    data_string = str(user_id) + json.dumps(neuron_data)
    return hashlib.sha256(data_string.encode()).hexdigest()

# Store Neuron in the Brain
def store_neuron(data, sub_context, user_id="admin", plane="web", context="general"):
    signature, unique_key = generate_signature(data, sub_context)
    security_mark = generate_security_mark(user_id, data)
    
    existing = neurons_collection.find_one({"unique_key": unique_key})
    version = existing["state"]["version"] + 1 if existing else 1
    
    neuron = {
        "id": f"neuron-{hashlib.md5(unique_key.encode()).hexdigest()}",
        "plane": plane,
        "type": "citation",
        "content": {
            "title": data["title"],
            "author": data["author"],
            "year": data["year"],
            "source": data["source"],
            "text": data["text"]
        },
        "context": context,
        "sub_context": sub_context,
        "tokenized_text": data["tokenized_text"],
        "token_ids": data["token_ids"],
        "linked_neurons": existing["linked_neurons"] if existing else [],
        "feedback": {
            "access_count": existing["feedback"]["access_count"] + 1 if existing else 1
        },
        "state": {
            "status": "active",
            "version": version,
            "last_updated": datetime.utcnow().isoformat() + "Z"
        },
        "signature": signature,
        "unique_key": unique_key,
        "security_mark": security_mark
    }
    
    neurons_collection.update_one(
        {"unique_key": unique_key},
        {"$set": neuron},
        upsert=True
    )
    logging.info(f"Stored neuron: {neuron['id']} (Version {version}) in plane {plane}")

# Main Execution (Your Control)
def main():
    # Load dictionary (placeholder until you load yours)
    load_dictionary()
    
    # Web sites to scrape
    sites = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://www.nasa.gov",
        "https://plato.stanford.edu/entries/artificial-intelligence/"
    ]
    
    for url in sites:
        scraped_data = scrape_website(url)
        if scraped_data:
            store_neuron(scraped_data, "initial_build", plane="web", context="general")
    
    # Local files to process (add your paths here)
    local_files = [
        "sample1.txt",
        "sample2.pdf",
        "sample3.docx",
        "sample4.png"
    ]
    
    for file_path in local_files:
        if os.path.exists(file_path):
            local_data = read_local_file(file_path)
            if local_data:
                store_neuron(local_data, "initial_build", plane="local", context="general")
        else:
            logging.warning(f"Local file not found: {file_path}")
    
    # Report progress
    neuron_count = neurons_collection.count_documents({})
    new_word_count = pending_words_collection.count_documents({})
    logging.info(f"Brain stats: {neuron_count} neurons, {new_word_count} pending words")

if __name__ == "__main__":
    main()