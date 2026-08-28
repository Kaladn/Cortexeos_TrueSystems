import os
import json
import fitz  # PyMuPDF for PDFs
import docx
from pathlib import Path

def extract_text_from_docx(docx_path):
    """Extracts text from DOCX file."""
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text

def convert_to_symbolis(text):
    """Mock function for converting text to Symbolis."""
    # Replace this with actual Symbolis conversion logic
    symbolis_text = text.replace("a", "🜂").replace("e", "🜃").replace("i", "🜄")  # Example placeholder
    return symbolis_text

def save_symbolis_output(original_path, symbolis_text):
    """Saves the converted Symbolis text to a structured format."""
    output_path = Path(original_path).with_suffix(".symbolis.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(symbolis_text)
    print(f"✅ Symbolis file saved: {output_path}")

def process_file(file_path):
    """Detects file type and processes it accordingly."""
    ext = file_path.lower().split(".")[-1]
    
    if ext == "docx":
        extracted_text = extract_text_from_docx(file_path)
    elif ext == "pdf":
        extracted_text = extract_text_from_pdf(file_path)
    else:
        print(f"❌ Unsupported file type: {ext}")
        return
    
    symbolis_text = convert_to_symbolis(extracted_text)
    save_symbolis_output(file_path, symbolis_text)

# Example Usage
file_path = "example.docx"  # Replace with actual file path
process_file(file_path)
