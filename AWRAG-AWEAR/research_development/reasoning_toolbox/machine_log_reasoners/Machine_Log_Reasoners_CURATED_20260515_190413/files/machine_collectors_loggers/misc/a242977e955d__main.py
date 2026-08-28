import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add current directory to path to ensure modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from validation_module import validate_entities
except ImportError:
    logging.error("Module 'validation_module' not found. Please ensure it is installed or available in the directory.")
    raise

from entity_extractor import extract_entities
from standardizer import standardize_citation
from pre_separator import categorize_citation

try:
    # Optional enricher module
    from enricher import enrich_citation
    ENRICHER_AVAILABLE = True
except ImportError:
    logging.warning("Module 'enricher' not found. Enrichment step will be skipped.")
    ENRICHER_AVAILABLE = False

from database_manager import connect_db, create_citation, create_tables

def process_citation(citation_text):
    """
    Processes a single citation through the pipeline.
    Args:
        citation_text (str): The raw citation text to process.
    """
    try:
        logging.info(f"Processing citation: {citation_text}")

        # Step 1: Determine citation category
        category = categorize_citation(citation_text)
        logging.info(f"Detected category: {category}")
        
        # Step 2: Extract entities
        entities = extract_entities(citation_text, category)
        logging.info(f"Extracted Entities: {entities}")

        # Step 3: Validate entities
        errors = validate_entities(entities, category)
        if errors:
            logging.warning(f"Validation Errors: {errors}")
            return None

        # Step 4: Enrich the citation (if enricher is available)
        if ENRICHER_AVAILABLE:
            enriched_entities = enrich_citation(entities)
            logging.info(f"Enriched Entities: {enriched_entities}")
        else:
            enriched_entities = entities
            logging.info("Enrichment step skipped.")

        # Step 5: Standardize the citation
        standardized_citation = standardize_citation(enriched_entities, category)
        logging.info(f"Standardized Citation: {standardized_citation}")

        # Step 6: Store in database
        conn, cur = connect_db()
        if conn and cur:
            # Ensure tables exist
            create_tables(cur)
            
            # Create citation record
            citation_id = create_citation(cur, conn, enriched_entities)
            logging.info(f"Citation stored with ID: {citation_id}")
            
            # Close database connection
            cur.close()
            conn.close()
            
            return {
                "citation_id": citation_id,
                "standardized_citation": standardized_citation,
                "entities": enriched_entities
            }
        else:
            logging.error("Failed to connect to database.")
            return {
                "standardized_citation": standardized_citation,
                "entities": enriched_entities
            }

    except Exception as e:
        logging.error(f"Error processing citation: {e}")
        return None

def main():
    """
    Main entry point for the program.
    """
    # Example citation
    citation_text = "Doe, J. (2022). A study of citations. Journal of Information Science, 10(2), 123-145."
    result = process_citation(citation_text)
    
    if result:
        print("\nProcessing Result:")
        print(f"Standardized Citation: {result.get('standardized_citation')}")
        if 'citation_id' in result:
            print(f"Citation ID in Database: {result.get('citation_id')}")
    else:
        print("Citation processing failed.")

if __name__ == "__main__":
    main()
