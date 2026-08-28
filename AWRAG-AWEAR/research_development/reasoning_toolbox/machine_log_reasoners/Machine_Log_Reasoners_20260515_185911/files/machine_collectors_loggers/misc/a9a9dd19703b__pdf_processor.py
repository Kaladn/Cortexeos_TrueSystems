import os
import json
import fitz  # PyMuPDF
import re

PDF_FOLDER = "data_scraping/pdfs/"
OUTPUT_FILE = "data_scraping/wordlist.json"

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text

def clean_and_tokenize(text):
    """Tokenizes words, removes duplicates, and filters out non-alphabetic characters."""
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())  # Extract words with at least 2 letters
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

    # Convert set to sorted list and save
    word_list = sorted(list(word_list))

    # 🔹 DEBUG: Print extracted words for verification
    print(f"📝 Extracted Words Count: {len(word_list)}")
    print(f"📝 Sample Words: {word_list[:50]}")  # Display first 50 words for preview

    save_word_list(word_list, OUTPUT_FILE)

def save_word_list(word_list, output_file):
    """Saves the extracted word list to a JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(word_list, f, indent=4)

    print(f"✅ Word list saved to {output_file}")

if __name__ == "__main__":
    process_pdfs()
