import os
import string

def split_word_frequency_by_alpha(input_file, output_dir):
    """
    Reads a large word frequency file line by line, extracts the first letter of each word,
    and appends that line to a corresponding alphabetical file (a.txt, b.txt, etc.).
    
    :param input_file: Path to the large word frequency file (e.g., word_frequencies.txt).
    :param output_dir: Directory to store the alphabetical output files.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Open the large file in read mode
    with open(input_file, "r", encoding="utf-8", errors="ignore") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Each line is typically "word count"
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue  # Skip malformed lines

            word = parts[0]
            # The rest of the line is the frequency or counts (parts[1])

            # Get the first letter and make it lowercase
            first_letter = word[0].lower() if word else ""

            # Check if it's a valid letter (a-z). Otherwise, categorize separately or skip.
            if first_letter not in string.ascii_lowercase:
                # Optionally, skip or put in a special file like '#' for non-alpha
                # continue
                first_letter = "#"  # We'll store non-alpha in '#.txt'
            
            # Construct the output filename, e.g., "a.txt"
            out_filename = f"{first_letter}.txt"
            out_path = os.path.join(output_dir, out_filename)

            # Append this line to the appropriate file
            with open(out_path, "a", encoding="utf-8") as outfile:
                outfile.write(line + "\n")

    print("✅ Finished splitting by first letter!")


if __name__ == "__main__":
    # Example usage:
    input_path = r"C:\AI SYMBOLIS WORK\word_frequencies.txt"  # Your massive word frequency file
    output_folder = r"C:\First Word Alpha Parsed Data"
    
    split_word_frequency_by_alpha(input_path, output_folder)
