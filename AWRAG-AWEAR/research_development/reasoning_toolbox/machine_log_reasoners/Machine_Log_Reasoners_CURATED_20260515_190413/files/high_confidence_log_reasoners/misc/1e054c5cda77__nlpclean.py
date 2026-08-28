import os
import csv
import spacy
import PyPDF2
import html.parser
import xml.etree.ElementTree as ET
import traceback
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm

# Load spaCy English model
print("🔄 Loading spaCy model...")
try:
    nlp = spacy.load("en_core_web_sm")
    print("✅ spaCy model loaded!")
except Exception as e:
    print("❌ Failed to load spaCy model:", e)
    exit()

# Ask user for a file or directory
def get_input_path():
    print("\n📂 Choose input type:")
    print("1. Single File")
    print("2. Entire Directory")
    choice = input("\nEnter 1 or 2: ").strip()

    root = tk.Tk()
    root.withdraw()  # Hide GUI window

    if choice == "1":
        path = filedialog.askopenfilename(title="Select a document", filetypes=[
            ("Text files", "*.txt;*.csv;*.html;*.xml;*.pdf"),
            ("All Files", "*.*")
        ])
    elif choice == "2":
        path = filedialog.askdirectory(title="Select a folder")
    else:
        print("❌ Invalid choice. Restart the script.")
        exit()

    return path

INPUT_PATH = get_input_path()
OUTPUT_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "cleaned_words.txt")
ERROR_LOG = os.path.join(os.path.expanduser("~"), "Desktop", "error_log.txt")

# Allowed file types
ALLOWED_EXTENSIONS = (".txt", ".csv", ".html", ".xml", ".pdf")

# Store unique words (fixing the A-only issue!)
word_set = set()

def log_error(error_msg):
    """Write errors to a log file"""
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(error_msg + "\n" + "="*50 + "\n")

def process_text(text):
    """Extract words from text, clean, and add to word_set."""
    try:
        words = text.lower().split()
        for word in words:
            word = word.strip(",.?!'\"():;[]{}<>")  # Remove punctuation
            if (
                len(word) < 4 or  # Remove short words
                "-" in word or  # Remove hyphenated words
                any(char.isdigit() for char in word)  # Remove words with numbers
            ):
                continue
            
            # spaCy Language Check
            doc = nlp(word)
            if doc.has_vector and doc.vector_norm != 0:  # Word must have a vector representation
                word_set.add(word)  # ✅ FIXED: Adding correctly

    except Exception as e:
        log_error(f"❌ Error processing text: {e}\n{traceback.format_exc()}")

def process_file(file_path):
    """Reads words from different file formats."""
    try:
        if file_path.endswith(".csv"):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header if exists
                for row in reader:
                    if len(row) > 1:
                        process_text(row[1])
        
        elif file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in tqdm(reader.pages, desc="Extracting PDF", leave=False):
                    process_text(page.extract_text() or "")

        elif file_path.endswith(".html"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = html.parser.HTMLParser().unescape(f.read())
                process_text(text)

        elif file_path.endswith(".xml"):
            tree = ET.parse(file_path)
            root = tree.getroot()
            text = " ".join(elem.text or "" for elem in root.iter())
            process_text(text)

        else:  # Default to text processing
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                process_text(f.read())

    except Exception as e:
        log_error(f"❌ Error reading {file_path}: {e}\n{traceback.format_exc()}")

# Process Files
if os.path.isdir(INPUT_PATH):
    print(f"🔄 Scanning directory '{INPUT_PATH}'...")
    files = [os.path.join(INPUT_PATH, f) for f in os.listdir(INPUT_PATH) if f.endswith(ALLOWED_EXTENSIONS)]
    
    if not files:
        print("❌ No valid files found in the directory!")
        exit()

    for file in tqdm(files, desc="Processing Files", unit="file"):
        process_file(file)
else:
    print(f"🔄 Reading from '{INPUT_PATH}'...")
    process_file(INPUT_PATH)

# Save cleaned words
try:
    print(f"✅ Cleaning complete. Saving {len(word_set)} words to '{OUTPUT_FILE}'...")
    
    # ✅ FIXED: Sorting so it's not just "A" words
    sorted_words = sorted(word_set, key=lambda x: (x[0].lower(), x))  

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(sorted_words) + "\n")

    print("🎉 Done! Your cleaned word list is ready.")
except Exception as e:
    log_error(f"❌ Error saving file: {e}\n{traceback.format_exc()}")
    print("❌ Error saving file! Check error_log.txt on Desktop.")
