import os
import string
from collections import Counter

def get_file_path():
    """Ask user for a file path and validate it."""
    while True:
        file_path = input("Enter the full path to your text file: ").strip()
        if os.path.isfile(file_path):
            return file_path
        else:
            print("❌ Invalid file path. Please try again.")

def clean_text(text):
    """Lowercase text and remove punctuation."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))  # Remove punctuation
    return text

def count_words(file_path):
    """Count word occurrences in a file."""
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    
    cleaned_text = clean_text(text)
    words = cleaned_text.split()
    
    word_count = Counter(words)  # Count occurrences of each word
    return word_count, len(words), len(word_count)

def save_results(word_count, file_path):
    """Save word frequency list to a file."""
    output_path = os.path.join(os.path.dirname(file_path), "word_list_output.txt")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Word\tCount\n")
        f.write("="*20 + "\n")
        for word, count in word_count.most_common():
            f.write(f"{word}\t{count}\n")
    
    print(f"✅ Word frequency list saved to: {output_path}")

def main():
    file_path = get_file_path()
    word_count, total_words, unique_words = count_words(file_path)

    print(f"\n📊 **File Analysis**")
    print(f"Total words: {total_words}")
    print(f"Unique words: {unique_words}\n")
    
    print("Top 10 most common words:")
    for word, count in word_count.most_common(10):
        print(f"{word}: {count}")

    save_results(word_count, file_path)

if __name__ == "__main__":
    main()
