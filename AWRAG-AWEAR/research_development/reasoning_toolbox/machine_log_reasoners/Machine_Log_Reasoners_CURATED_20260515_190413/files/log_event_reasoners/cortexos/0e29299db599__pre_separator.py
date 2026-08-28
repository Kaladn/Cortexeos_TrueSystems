import re
import logging
from transformers import pipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load a pre-trained DistilBERT model for text classification
# You might need to fine-tune this model on your specific citation data
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-citation-categories") # Replace with your model

def categorize_citation(citation_text):
    """
    Categorizes a citation into a broad category (e.g., article, book, etc.).

    Args:
        citation_text (str): The raw citation text.

    Returns:
        str: The predicted category of the citation.
             Returns "unknown" if the category cannot be determined.
    """
    try:
        # --- Basic Keyword-Based Categorization (for simple cases) ---
        if re.search(r"\b(ed|edition|volume|edited by)\b", citation_text, re.IGNORECASE):
            return "book"
        if re.search(r"\b(proceedings of|conference|symposium)\b", citation_text, re.IGNORECASE):
            return "conference"
        if re.search(r"\b(ph\.d\.|master's thesis|dissertation)\b", citation_text, re.IGNORECASE):
            return "thesis"
        if re.search(r"\b(arxiv|preprint)\b", citation_text, re.IGNORECASE):
            return "preprint"
        if re.search(r"\b(retrieved from|available at|http|www)\b", citation_text, re.IGNORECASE):
             return "web"

        # --- Machine Learning-Based Categorization (for complex cases) ---
        result = classifier(citation_text)[0]
        predicted_category = result['label']

        # Map model output labels to your desired categories
        category_mapping = {
            "LABEL_0": "article",
            "LABEL_1": "book",
            "LABEL_2": "conference",
            "LABEL_3": "thesis",
            "LABEL_4": "report",
            "LABEL_5": "web"
            # ... add more mappings as needed ...
        }

        if predicted_category in category_mapping:
            return category_mapping[predicted_category]
        else:
            logging.warning(f"Unknown category label from model: {predicted_category}")
            return "unknown"

    except Exception as e:
        logging.error(f"Error categorizing citation: {citation_text} - Error: {e}")
        return "unknown"

# Example Usage:
citations = [
    "Doe, J., & Smith, A. (2022). The Impact of AI on Society. Journal of Artificial Intelligence, 45(2), 123-145.",
    "Jones, M. (2021). A History of the Internet. New York: Tech Publishers.",
    "Brown, L. (2023). Advanced Machine Learning Techniques. In Proceedings of the International Conference on Data Science (pp. 45-56).",
    "Williams, P. (2019). Data Mining for Business Intelligence. (Doctoral dissertation). Retrieved from http://example.com/dissertation",
    "Garcia, R. et al. (2020). A Novel Framework for Citation Analysis. arXiv preprint arXiv:2001.12345.",
    "Smith, J. (2023, June 1). The Future of AI. Blog post. Available at: https://www.exampleblog.com/future-of-ai"
]

for citation in citations:
    category = categorize_citation(citation)
    print(f"Citation: {citation}\nCategory: {category}\n---")
