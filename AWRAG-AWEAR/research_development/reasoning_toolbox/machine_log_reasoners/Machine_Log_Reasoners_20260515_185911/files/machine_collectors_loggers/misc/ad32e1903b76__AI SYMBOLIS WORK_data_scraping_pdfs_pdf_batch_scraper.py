import os
import json
import fitz  # PyMuPDF

PDF_FOLDER = "data_scraping/pdfs/"
OUTPUT_FILE = "data_scraping/wordlist.json"

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

def clean_and_tokenize(text):
    """Tokenizes words and removes duplicates."""
    words = text.lower().split()  # Basic word splitting
    words = [word.strip(".,!?()[]{}:;\"'") for word in words]  # Clean punctuation
    words = list(set(words))  # Remove duplicates
    return words

def process_pdfs():
    """Processes all PDFs in the folder and builds a word list."""
    word_list = set()
    
    for file in os.listdir(PDF_FOLDER):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, file)
            print(f"📖 Extracting from {file}...")
            text = extract_text_from_pdf(pdf_path)
            words = clean_and_tokenize(text)
            word_list.update(words)
    
    # Save word list to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(word_list)), f, indent=2)
    
    print(f"\n✅ Word list saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_pdfs()
