import json
import csv
import io

def preprocess_training_data(input_file_path, output_file_path):
    """
    Reads a JSON file containing a CSV-like string in one of its fields,
    parses the CSV data, and converts each row into a separate JSON object
    in JSONL format, suitable for the HarmonicVectorizer.
    """
    processed_count = 0
    error_count = 0

    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            original_data = json.load(infile)
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from input file {input_file_path}. Details: {e}")
        return
    except FileNotFoundError:
        print(f"Error: Input file {input_file_path} not found.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading {input_file_path}: {e}")
        return

    csv_string = original_data.get("completion")
    if not csv_string or not isinstance(csv_string, str):
        print(f"Error: 'completion' field not found or not a string in {input_file_path}.")
        return

    # Use io.StringIO to treat the string as a file for the csv reader
    csv_file_like_object = io.StringIO(csv_string)
    csv_reader = csv.reader(csv_file_like_object)

    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        header = next(csv_reader, None) # Skip header row (e.g., "Word,Symbol")
        if not header or header[0].lower() != "word" or header[1].lower() != "symbol":
            print(f"Warning: CSV header not as expected ('Word,Symbol'). Found: {header}. Proceeding with parsing.")
            # If header was not what we expected, we might need to re-process the first line if it was actual data
            # For this script, we'll assume the first line is always a header to be skipped or it's fine to skip if not matching.

        for i, row in enumerate(csv_reader):
            try:
                if len(row) == 2:
                    word = row[0].strip()
                    symbol = row[1].strip()

                    if not word: # Skip if word is empty after stripping
                        print(f"Skipping line {i+2} due to empty word.") # i+2 because of 0-indexing and header
                        error_count += 1
                        continue

                    # Create the JSON object for HarmonicVectorizer
                    output_entry = {
                        "id": f"lexicon_map_{word.replace(' ', '_').lower()}_{i}",
                        "content": word,
                        "tags": [symbol, "lexicon_mapping"],
                        "subject": "language.lexicon.word_symbol",
                        "context": "dataset.training_data_csv_conversion",
                        "priority": 0.75 # Default priority for these entries
                    }
                    outfile.write(json.dumps(output_entry) + '\n')
                    processed_count += 1
                else:
                    print(f"Skipping malformed row on line {i+2} (original CSV string): {row}")
                    error_count += 1
            except Exception as e:
                print(f"Error processing row on line {i+2} (original CSV string): {row}. Details: {e}")
                error_count += 1
    
    print(f"Preprocessing complete.")
    print(f"Successfully processed and wrote {processed_count} entries to {output_file_path}.")
    if error_count > 0:
        print(f"Encountered {error_count} errors or skipped lines during processing.")

if __name__ == '__main__':
    input_path = "/home/ubuntu/upload/training_data_from_csv.jsonl"
    output_path = "/home/ubuntu/processed_training_data.jsonl"
    print(f"Starting preprocessing of {input_path}...")
    preprocess_training_data(input_path, output_path)
    print(f"Preprocessing script finished. Check {output_path} for results.")

