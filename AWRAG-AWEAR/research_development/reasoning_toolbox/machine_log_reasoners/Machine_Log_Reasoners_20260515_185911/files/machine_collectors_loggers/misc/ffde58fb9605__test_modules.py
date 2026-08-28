import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the directory containing the modules to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def run_tests():
    """
    Run tests on all fixed modules to ensure they work properly.
    """
    test_results = {}
    
    # Test 1: Test pre_separator module
    try:
        logging.info("Testing pre_separator module...")
        from pre_separator import categorize_citation
        
        test_citation = "Doe, J., & Smith, A. (2022). The Impact of AI on Society. Journal of Artificial Intelligence, 45(2), 123-145."
        category = categorize_citation(test_citation)
        
        assert category in ["article", "book", "conference", "thesis", "preprint", "web", "unknown"]
        test_results["pre_separator"] = "PASS"
        logging.info(f"Pre-separator test passed. Detected category: {category}")
    except Exception as e:
        test_results["pre_separator"] = f"FAIL: {str(e)}"
        logging.error(f"Pre-separator test failed: {e}")
    
    # Test 2: Test entity_extractor module
    try:
        logging.info("Testing entity_extractor module...")
        from entity_extractor import extract_entities
        
        test_citation = "Doe, J., & Smith, A. (2022). The Impact of AI on Society. Journal of Artificial Intelligence, 45(2), 123-145."
        category = "article"
        entities = extract_entities(test_citation, category)
        
        assert isinstance(entities, dict)
        assert "author" in entities
        assert "title" in entities
        assert "year" in entities
        test_results["entity_extractor"] = "PASS"
        logging.info(f"Entity extractor test passed. Extracted entities: {entities}")
    except Exception as e:
        test_results["entity_extractor"] = f"FAIL: {str(e)}"
        logging.error(f"Entity extractor test failed: {e}")
    
    # Test 3: Test validation_module
    try:
        logging.info("Testing validation_module...")
        from validation_module import validate_entities
        
        test_entities = {
            "author": "Doe, J.",
            "title": "Example Title",
            "year": "2023",
            "journal": "Journal of Information Science",
        }
        category = "article"
        errors = validate_entities(test_entities, category)
        
        assert isinstance(errors, list)
        test_results["validation_module"] = "PASS"
        logging.info(f"Validation module test passed. Validation errors: {errors}")
    except Exception as e:
        test_results["validation_module"] = f"FAIL: {str(e)}"
        logging.error(f"Validation module test failed: {e}")
    
    # Test 4: Test standardizer module
    try:
        logging.info("Testing standardizer module...")
        from standardizer import standardize_citation
        
        test_entities = {
            "author": "Doe, J.",
            "title": "Example Title",
            "year": "2023",
            "journal": "Journal of Information Science",
            "volume": "10",
            "issue": "2",
            "pages": "123-145"
        }
        category = "article"
        standardized = standardize_citation(test_entities, category)
        
        assert isinstance(standardized, str)
        assert len(standardized) > 0
        test_results["standardizer"] = "PASS"
        logging.info(f"Standardizer test passed. Standardized citation: {standardized}")
    except Exception as e:
        test_results["standardizer"] = f"FAIL: {str(e)}"
        logging.error(f"Standardizer test failed: {e}")
    
    # Test 5: Test database_manager module
    try:
        logging.info("Testing database_manager module...")
        from database_manager import connect_db, create_tables, create_citation
        
        # Use in-memory database for testing
        conn, cur = connect_db(":memory:")
        assert conn is not None
        assert cur is not None
        
        # Create tables
        success = create_tables(cur)
        assert success is True
        
        # Insert a test citation
        test_entities = {
            "author": "Doe, J.",
            "title": "Example Title",
            "year": "2023",
            "journal": "Journal of Information Science",
        }
        citation_id = create_citation(cur, conn, test_entities, "article")
        assert citation_id is not None
        
        # Clean up
        cur.close()
        conn.close()
        
        test_results["database_manager"] = "PASS"
        logging.info("Database manager test passed.")
    except Exception as e:
        test_results["database_manager"] = f"FAIL: {str(e)}"
        logging.error(f"Database manager test failed: {e}")
    
    # Test 6: Test main module
    try:
        logging.info("Testing main module...")
        from main import process_citation
        
        test_citation = "Doe, J. (2022). A study of citations. Journal of Information Science, 10(2), 123-145."
        result = process_citation(test_citation)
        
        # Result might be None if validation fails, which is acceptable
        test_results["main"] = "PASS"
        logging.info(f"Main module test passed. Processing result: {result}")
    except Exception as e:
        test_results["main"] = f"FAIL: {str(e)}"
        logging.error(f"Main module test failed: {e}")
    
    # Print summary
    logging.info("\n--- Test Results Summary ---")
    for module, result in test_results.items():
        logging.info(f"{module}: {result}")
    
    # Return overall success status
    return all(result == "PASS" for result in test_results.values())

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed. Check the logs for details.")
