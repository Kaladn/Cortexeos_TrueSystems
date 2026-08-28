import concurrent.futures
import glob

def process_file(file_path):
    """
    Processes a single file and returns a set of cleaned words.
    Adjust the cleaning logic as needed.
    """
    words = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Simple tokenization; you might add more cleaning (punctuation removal, spell-check, etc.)
                line_words = line.strip().split()
                for word in line_words:
                    # Only add word if it is purely alphabetic or a valid hyphenated word
                    if word.replace('-', '').isalpha():
                        words.add(word.lower())
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return words

def scrape_words(input_pattern, batch_size=5):
    """
    Scrape words from files matching the input pattern using parallel processing.
    """
    all_words = set()
    files = glob.glob(input_pattern)
    print(f"Found {len(files)} files to process.")

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # The chunksize helps with batching, adjust batch_size as needed
        for result in executor.map(process_file, files, chunksize=batch_size):
            all_words.update(result)

    return all_words

def append_words_to_file(words, output_file):
    """
    Append words to an existing file, ensuring duplicates are not added if that is required.
    """
    # Read existing words to avoid duplicates (if necessary)
    existing_words = set()
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_words = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        # File doesn't exist yet; that's okay
        pass

    new_words = words - existing_words

    if new_words:
        with open(output_file, "a", encoding="utf-8") as f:
            for word in sorted(new_words):
                f.write(word + "\n")
        print(f"Appended {len(new_words)} new words to {output_file}.")
    else:
        print("No new words to append.")

def main():
    # Define your input file pattern (e.g., all .txt files in a directory)
    input_pattern = "data/*.txt"  # Change this to your actual path
    output_file = "words_list.txt"

    # Scrape words using parallel processing
    all_words = scrape_words(input_pattern, batch_size=5)
    print(f"Total unique words scraped: {len(all_words)}")

    # Append the scraped words to your output file
    append_words_to_file(all_words, output_file)

if __name__ == "__main__":
    main()
