import os
import json
import numpy as np
import wave
import re
from tqdm import tqdm

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

def split_wav_file(wave_data, sample_rate, output_audio_path, max_size=2_000_000_000):
    """Splits WAV data into multiple files if size exceeds 2GB limit."""
    chunk_size = max_size // 2  # Divide by 2 to avoid exceeding limit
    num_parts = (wave_data.nbytes // chunk_size) + 1
    
    for i in range(num_parts):
        part_data = wave_data[i * chunk_size:(i + 1) * chunk_size]
        part_path = output_audio_path.replace(".wav", f"_part{i+1}.wav")
        
        with wave.open(part_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(part_data.tobytes())
        print(f"Part {i+1} saved: {part_path}")

def text_to_tone_audio(base_directory):
    """Converts text files from the Input folder to tone-based audio in the Output folder while preserving punctuation."""
    input_folder = os.path.join(base_directory, "Input")
    output_folder = os.path.join(base_directory, "Output")
    tonal_dict_folder = os.path.join(base_directory, "tonal_dict")
    
    os.makedirs(output_folder, exist_ok=True)
    tonal_dict = load_combined_tonal_dictionary(tonal_dict_folder)
    
    sample_rate = 16000  # 16kHz encoding
    duration = 0.15  # 150ms per tone
    silence_duration = 0.05  # 50ms for word spacing
    punctuation_silence = 0.15  # 150ms for punctuation
    amplitude = 32767  # Max amplitude for 16-bit audio
    
    text_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]
    print(f"Processing {len(text_files)} text files...")
    
    for text_file in tqdm(text_files, desc="Processing Text Files", unit="file"):
        input_path = os.path.join(input_folder, text_file)
        output_audio_path = os.path.join(output_folder, text_file.replace(".txt", ".wav"))
        
        with open(input_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        words_and_punct = re.findall(r'\b\w+\b|[.,!?;]', text)
        wave_data = []  # Use list instead of NumPy for efficiency
        
        print(f"Processing {len(words_and_punct)} words and punctuation marks...")
        
        for item in tqdm(words_and_punct, desc="Generating Audio", unit="word"):
            freq = tonal_dict.get(item, 440)  # Get tone or default to A4
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)
            wave_data.append(tone)
            
            silence_length = int(sample_rate * (punctuation_silence if item in ".,!?;" else silence_duration))
            wave_data.append(np.zeros(silence_length, dtype=np.int16))  # Add silence between words
        
        wave_data = np.concatenate(wave_data)  # Convert list to NumPy array
        
        if wave_data.nbytes > 2_000_000_000:
            print(f"File too large, splitting: {output_audio_path}")
            split_wav_file(wave_data, sample_rate, output_audio_path)
        else:
            with wave.open(output_audio_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(wave_data.tobytes())
            print(f"Audio file saved: {output_audio_path}")

# Example usage:
base_dir = r"C:\\Users\\mydyi\\Desktop\\Word to tone"
text_to_tone_audio(base_dir)
