# harmonic_vectorizer.py

import numpy as np
import json
import os
from hashlib import sha256

class HarmonicVectorizer:
    def __init__(self, fft_bins=32):
        self.fft_bins = fft_bins

    def vectorize_entry(self, entry):
        """
        Entry is a dict with at least:
        - content (str): the main raw data
        - subject (str)
        - context (str)
        - tags (list[str])
        - priority (float or int)
        """
        light_vector = self._generate_light_vector(entry)
        harmonics_vector = self._generate_harmonics_vector(entry['content'])
        return {
            'id': entry.get('id') or self._hash_entry(entry),
            'light_vector': light_vector,
            'harmonics_vector': harmonics_vector,
            **{k: v for k, v in entry.items() if k not in ['light_vector', 'harmonics_vector']}
        }

    def _generate_light_vector(self, entry):
        """Maps metadata to an [R, G, B, intensity, opacity] style vector."""
        subject_hash = int(sha256(entry['subject'].encode()).hexdigest(), 16)
        context_hash = int(sha256(entry['context'].encode()).hexdigest(), 16)
        tag_hash = int(sha256(".".join(entry['tags']).encode()).hexdigest(), 16)

        r = (subject_hash % 256) / 255.0
        g = (context_hash % 256) / 255.0
        b = (tag_hash % 256) / 255.0
        intensity = min(float(entry.get('priority', 0.5)), 1.0)
        opacity = 1.0  # future use

        return [r, g, b, intensity, opacity]

    def _generate_harmonics_vector(self, content):
        """Converts text into a harmonic spectrum using FFT-like logic."""
        signal = np.array([ord(c) for c in content if ord(c) < 128], dtype=float)
        if signal.size == 0:
            return [0.0] * self.fft_bins

        # Pad or truncate to nearest power of 2
        target_len = 2 ** int(np.ceil(np.log2(len(signal))))
        signal = np.pad(signal, (0, target_len - len(signal)), mode='constant')

        fft = np.fft.fft(signal)[:self.fft_bins]
        magnitudes = np.abs(fft)
        # Handle potential division by zero if max(magnitudes) is 0
        max_magnitude = np.max(magnitudes)
        if max_magnitude == 0:
            normalized = [0.0] * self.fft_bins
        else:
            normalized = (magnitudes / max_magnitude).tolist()
        return normalized

    def _hash_entry(self, entry):
        data = entry['subject'] + entry['context'] + entry['content']
        return sha256(data.encode()).hexdigest()[:16]

    def vectorize_file(self, input_path, output_path):
        """Reads a JSONL file, vectorizes each entry, and writes output to another JSONL."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
            for line_number, line in enumerate(infile):
                try:
                    entry = json.loads(line.strip())
                    vectorized = self.vectorize_entry(entry)
                    outfile.write(json.dumps(vectorized) + '\n')
                except Exception as e:
                    print(f"Error processing entry on line {line_number + 1}: {e} - Entry: {line.strip()}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Batch vectorize CortexOS ingestion JSONL files.")
    parser.add_argument('--input', required=True, help='Path to input raw_data_ingest.jsonl')
    parser.add_argument('--output', required=True, help='Path to output vectorized_output.jsonl')
    args = parser.parse_args()

    vectorizer = HarmonicVectorizer()
    vectorizer.vectorize_file(args.input, args.output)
    print(f"Vectorization complete. Output saved to {args.output}")

