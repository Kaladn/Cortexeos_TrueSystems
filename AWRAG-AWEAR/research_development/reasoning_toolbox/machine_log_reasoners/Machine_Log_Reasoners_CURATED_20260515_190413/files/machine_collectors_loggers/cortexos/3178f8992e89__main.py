import logging
try:
    from validator import validate_entities
except ImportError:
    logging.error("Module 'validator' not found. Please ensure it is installed or available in the directory.")
    raise
from entity_extractor import extract_entities
from standardizer import standardize_citation
try:
    from enricher import enrich_citation
except ImportError:
    logging.error("Module 'enricher' not found. Please ensure it is installed or available in the directory.")
    raise
 from database_manager import connect_db, create_citation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_citation(citation_text):
    """
    Processes a single citation through the pipeline.
    Args:
        citation_text (str): The raw citation text to process.
    """
    try:
        logging.info(f"Processing citation: {citation_text}")

        # Step 1: Extract entities
        category = "article"  # This should ideally come from the pre-separator module
        entities = extract_entities(citation_text, category)
        logging.info(f"Extracted Entities: {entities}")

        # Step 2: Validate entities
        errors = validate_entities(entities, category)
        if errors:
            logging.warning(f"Validation Errors: {errors}")
            return

        # Step 3: Enrich the citation
        enriched_entities = enrich_citation(entities)
        logging.info(f"Enriched Entities: {enriched_entities}")

        # Step 4: Standardize the citation
        standardized_citation = standardize_citation(enriched_entities, category)
        logging.info(f"Standardized Citation: {standardized_citation}")

        # Step 5: Store in database (optional)
        conn, cur = connect_db()
        citation_id = create_citation(cur, conn, enriched_entities)
        logging.info(f"Citation stored with ID: {citation_id}")
        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"Error processing citation: {e}")

def main():
    """
    Main entry point for the program.
    """
    # Example citation
    citation_text = "Doe, J. (2022). A study of citations. Journal of Information Science, 10(2), 123-145."
    process_citation(citation_text)

if __name__ == "__main__":
    main()
