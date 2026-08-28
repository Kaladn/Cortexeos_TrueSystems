import os
import json
import numpy as np
import time
import wave
import re
from tqdm import tqdm
from scipy.signal import find_peaks
from scipy.fft import fft

def load_combined_tonal_dictionary(tonal_dict_folder):
    """Loads and merges all tonal dictionary JSON files into a single dictionary."""
    combined_dict = {}
    json_files = [f for f in os.listdir(tonal_dict_folder) if f.endswith(".json")]
    
    print(f"Loading {len(json_files)} dictionary files...")
    for filename in tqdm(json_files, desc="Loading Dictionaries", unit="file"):
        file_path = os.path.join(tonal_dict_folder, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            combined_dict.update(json.load(file))
    return combined_dict

def audio_to_text(base_directory):
    """Converts tone-based audio back into words using frequency analysis."""
    input_folder = os.path.join(base_directory, "Output")  # Read from output folder
    output_folder = os.path.join(base_directory, "Decoded")
    tonal_dict_folder = os.path.join(base_directory, "tonal_dict")
    
    os.makedirs(output_folder, exist_ok=True)
    tonal_dict = load_combined_tonal_dictionary(tonal_dict_folder)
    reverse_dict = {v: k for k, v in tonal_dict.items()}  # Reverse mapping from tone to word
    
    sample_rate = 44100  # Standard CD quality
    
    audio_files = [f for f in os.listdir(input_folder) if f.endswith(".wav")]
    print(f"Processing {len(audio_files)} audio files...")
    
    for audio_file in tqdm(audio_files, desc="Processing Audio Files", unit="file"):
        input_audio_path = os.path.join(input_folder, audio_file)
        output_text_path = os.path.join(output_folder, audio_file.replace(".wav", ".txt"))
        
        with wave.open(input_audio_path, 'r') as wf:
            num_frames = wf.getnframes()
            audio_data = np.frombuffer(wf.readframes(num_frames), dtype=np.int16)
        
        chunk_size = int(sample_rate * 0.15)  # Match original tone duration
        words = []
        
        print(f"Decoding {num_frames // chunk_size} tone segments...")
        for i in tqdm(range(0, len(audio_data), chunk_size), desc="Decoding Audio", unit="tone"):
            segment = audio_data[i:i + chunk_size]
            if len(segment) == 0:
                continue
            
            # Perform FFT to detect the dominant frequency
            spectrum = np.abs(fft(segment))
            freqs = np.fft.fftfreq(len(segment), 1/sample_rate)
            peaks, _ = find_peaks(spectrum, height=1000)
            if len(peaks) > 0:
                detected_freq = freqs[peaks[0]]
                detected_word = reverse_dict.get(int(detected_freq), "[UNKNOWN]")
                words.append(detected_word)
            else:
                words.append("[UNKNOWN]")
        
        with open(output_text_path, 'w', encoding='utf-8') as file:
            file.write(" ".join(words))
        
        print(f"Decoded text saved: {output_text_path}")

# Example usage:
base_dir = r"C:\Users\mydyi\Desktop\Word to tone"
audio_to_text(base_dir)
