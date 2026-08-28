import os
import argparse
import logging
from typing import Iterator

# Configure logging for clear operational feedback
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def find_text_files(source_dir: str) -> Iterator[str]:
    """
    Recursively finds all .txt files in the source directory.

    Args:
        source_dir: The directory to search.

    Yields:
        The full path to each found text file.
    """
    logger.info(f"Searching for .txt files in '{source_dir}'...")
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith('.txt'):
                yield os.path.join(root, file)

def combine_and_chunk(source_dir: str, output_dir: str, max_size_mb: int = 100):
    """
    Combines text files from a source directory into chunks of a maximum size.

    Args:
        source_dir: The directory containing source .txt files.
        output_dir: The directory where chunk files will be saved.
        max_size_mb: The maximum size of each chunk in megabytes.
    """
    # --- Validation and Setup ---
    if not os.path.isdir(source_dir):
        logger.error(f"Source directory not found: {source_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output chunks will be saved to: {output_dir}")

    max_size_bytes = max_size_mb * 1024 * 1024
    logger.info(f"Maximum chunk size set to {max_size_mb} MB ({max_size_bytes} bytes).")

    # --- Processing Logic ---
    chunk_number = 1
    current_chunk_size = 0
    output_file = None
    file_count = 0

    try:
        for filepath in find_text_files(source_dir):
            file_count += 1
            logger.info(f"Processing file ({file_count}): {os.path.basename(filepath)}")
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
                    for line in infile:
                        # Start a new chunk if one doesn't exist or the current one is full
                        if output_file is None or (current_chunk_size + len(line.encode('utf-8'))) > max_size_bytes:
                            if output_file:
                                output_file.close()
                                logger.info(f"Completed chunk_{chunk_number - 1}.txt with size {current_chunk_size / (1024*1024):.2f} MB.")
                            
                            chunk_path = os.path.join(output_dir, f"chunk_{chunk_number}.txt")
                            output_file = open(chunk_path, 'w', encoding='utf-8')
                            logger.info(f"Creating new file: {chunk_path}")
                            
                            current_chunk_size = 0
                            chunk_number += 1

                        output_file.write(line)
                        current_chunk_size += len(line.encode('utf-8'))
                
                # Add a separator between contents of different files for clarity
                if output_file:
                    separator = "\n\n--- END OF FILE: {} ---\n\n".format(os.path.basename(filepath))
                    output_file.write(separator)
                    current_chunk_size += len(separator.encode('utf-8'))

            except Exception as e:
                logger.warning(f"Could not process file {filepath}. Error: {e}")
                continue

    finally:
        if output_file:
            output_file.close()
            logger.info(f"Completed final chunk_{chunk_number - 1}.txt with size {current_chunk_size / (1024*1024):.2f} MB.")

    logger.info(f"Process complete. Processed {file_count} files into {chunk_number - 1} chunks.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine and chunk text files from a directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="The source directory containing .txt files."
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="The directory where output chunks will be saved."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=100,
        help="Maximum size for each chunk in MB. (Default: 100)"
    )
    args = parser.parse_args()

    combine_and_chunk(args.source, args.output, args.size)