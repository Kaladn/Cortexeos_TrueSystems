import re
import logging
import torch
import os
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check for GPU availability and set up ROCm for AMD GPUs if available
def setup_gpu():
    """
    Set up GPU acceleration with ROCm for AMD GPUs if available.
    Returns:
        str: The device to use ('cuda', 'rocm', or 'cpu')
    """
    if torch.cuda.is_available():
        device = torch.device('cuda')
        logging.info(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
        return 'cuda'
    else:
        try:
            # Check for ROCm (AMD GPU support)
            if hasattr(torch, 'hip') and torch.hip.is_available():
                device = torch.device('hip')
                logging.info(f"Using ROCm (AMD GPU): {torch.hip.get_device_name(0)}")
                return 'rocm'
            else:
                logging.warning("No GPU acceleration available. Using CPU.")
                return 'cpu'
        except:
            logging.warning("No GPU acceleration available. Using CPU.")
            return 'cpu'

# Set up device
device_type = setup_gpu()

# Define a simpler model for citation classification
MODEL_NAME = "distilbert-base-uncased"

# Initialize the model only when needed
classifier = None

def load_classifier():
    """
    Lazy-load the classifier model to save memory when not in use.
    """
    global classifier
    
    if classifier is None:
        try:
            logging.info(f"Loading classification model: {MODEL_NAME}")
            
            # Load model with GPU acceleration if available
            if device_type in ['cuda', 'rocm']:
                classifier = pipeline(
                    "text-classification", 
                    model=MODEL_NAME, 
                    device=0  # Use first GPU
                )
            else:
                classifier = pipeline(
                    "text-classification", 
                    model=MODEL_NAME
                )
                
            logging.info("Classification model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading classification model: {e}")
            # Fallback to rule-based classification only
            classifier = None
            
    return classifier

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
        # --- Rule-Based Categorization (for simple cases) ---
        if re.search(r"\b(journal|j\.|volume|vol\.|issue)\b", citation_text, re.IGNORECASE):
            return "article"
            
        if re.search(r"\b(ed|edition|volume|edited by|publisher|press)\b", citation_text, re.IGNORECASE):
            return "book"
            
        if re.search(r"\b(proceedings of|conference|symposium|workshop)\b", citation_text, re.IGNORECASE):
            return "conference"
            
        if re.search(r"\b(ph\.d\.|master's thesis|dissertation)\b", citation_text, re.IGNORECASE):
            return "thesis"
            
        if re.search(r"\b(arxiv|preprint)\b", citation_text, re.IGNORECASE):
            return "preprint"
            
        if re.search(r"\b(retrieved from|available at|http|www)\b", citation_text, re.IGNORECASE):
            return "web"

        # --- Machine Learning-Based Categorization (for complex cases) ---
        model = load_classifier()
        
        if model:
            # Use the model for classification
            result = model(citation_text)[0]
            confidence = result['score']
            
            # Only use model prediction if confidence is high enough
            if confidence > 0.7:
                # Map model output labels to citation categories
                # DistilBERT base model has different labels, so we map them to our categories
                label_mapping = {
                    "LABEL_0": "article",
                    "LABEL_1": "book",
                    "POSITIVE": "article",  # For binary classification models
                    "NEGATIVE": "book"      # For binary classification models
                }
                
                predicted_label = result['label']
                if predicted_label in label_mapping:
                    return label_mapping[predicted_label]
            
            # If confidence is low or label mapping failed, fall back to "unknown"
            logging.info(f"Model prediction uncertain ({confidence:.2f}): {result['label']}")
            return "article"  # Default to article as most common type
        else:
            # If model failed to load, default to article
            logging.warning("Model not available, defaulting to 'article'")
            return "article"

    except Exception as e:
        logging.error(f"Error categorizing citation: {citation_text} - Error: {e}")
        return "unknown"

if __name__ == "__main__":
    # Example Usage:
    citations = [
        "Doe, J., & Smith, A. (2022). The Impact of AI on Society. Journal of Artificial Intelligence, 45(2), 123-145.",
        "Jones, M. (2021). A History of the Internet. New York: Tech Publishers.",
        "Brown, L. (2023). Advanced Machine Learning Techniques. In Proceedings of the International Conference on Data Science (pp. 45-56).",
        "Williams, P. (2019). Data Mining for Business Intelligence. (Doctoral dissertation). Retrieved from http://example.com/dissertation",
        "Garcia, R. et al. (2020). A Novel Framework for Citation Analysis. arXiv preprint arXiv:2001.12345.",
        "Smith, J. (2023, June 1). The Future of AI. Blog post. Available at: https://www.exampleblog.com/future-of-ai"
    ]

    print(f"Using device: {device_type}")
    for citation in citations:
        category = categorize_citation(citation)
        print(f"Citation: {citation}\nCategory: {category}\n---")
