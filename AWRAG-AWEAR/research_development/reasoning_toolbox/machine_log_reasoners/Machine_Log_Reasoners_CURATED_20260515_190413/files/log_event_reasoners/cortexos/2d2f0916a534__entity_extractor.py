import spacy
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load a spaCy language model
nlp = spacy.load("en_core_web_sm")

def extract_entities(citation_text, category):
    """
    Extracts key entities (author, title, year, etc.) from a citation text.

    Args:
        citation_text (str): The raw citation text.
        category (str): The category of the citation (e.g., "article", "book").

    Returns:
        dict: A dictionary containing the extracted entities.
               Returns an empty dictionary if no entities are found.
    """
    doc = nlp(citation_text)
    entities = {}

    try:
        # --- Author Extraction ---
        if category in ["article", "book"]:
            author_match = re.match(r"^(.*?)(?:\.|;)\s*\(", citation_text)
            if author_match:
                entities["author"] = author_match.group(1).strip()
            else:
                # Use spaCy's NER as a fallback
                authors = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
                if authors:
                    entities["author"] = ", ".join(authors)

        # --- Title Extraction ---
        title_match = re.search(r"\(\d{4}\)\.\s*\"(.*?)\"| \((\d{4})\)\.\s*(.*?),", citation_text)
        if title_match:
            entities["title"] = title_match.group(1) or title_match.group(3)
            entities["title"] = entities["title"].strip()
        else:
            for ent in doc.ents:
                if ent.label_ == "WORK_OF_ART":
                    entities["title"] = ent.text
                    break

        # --- Year Extraction ---
        year_match = re.search(r"\((\d{4})\)", citation_text)
        if year_match:
            entities["year"] = year_match.group(1)

        # --- Category-Specific Extraction ---
        if category == "article":
            journal_match = re.search(r"([A-Za-z\s]+),\s*\d+", citation_text)
            if journal_match:
                entities["journal"] = journal_match.group(1).strip()

        elif category == "book":
            publisher_match = re.search(r"\.\s*(.*?):\s*[A-Za-z\s]+$", citation_text)
            if publisher_match:
                entities["publisher"] = publisher_match.group(1).strip()

    except Exception as e:
        logging.error(f"Error extracting entities from citation: {citation_text} - Error: {e}")
        return {}

    logging.info(f"Successfully extracted entities: {entities}")
    return entities

if __name__ == "__main__":
    # Example Citations
    citations = [
        {
            "text": "Doe, J., & Smith, A. (2022). \"The Impact of AI on Society.\" Journal of Artificial Intelligence, 45(2), 123-145.",
            "category": "article"
        },
        {
            "text": "Jones, M. (2021). A History of the Internet. New York: Tech Publishers.",
            "category": "book"
        },
        {
            "text": "Brown, L. (2023). Advanced Machine Learning Techniques.",
            "category": "book"
        }
    ]

    for citation in citations:
        extracted = extract_entities(citation["text"], citation["category"])
        print(f"Citation: {citation['text']}\nExtracted Entities: {extracted}\n")
