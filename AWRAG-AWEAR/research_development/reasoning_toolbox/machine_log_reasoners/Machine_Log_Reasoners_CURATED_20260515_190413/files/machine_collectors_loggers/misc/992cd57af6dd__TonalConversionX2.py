import os
import json
import numpy as np
import wave
import re
import multiprocessing
from tqdm import tqdm
from pydub import AudioSegment

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

def convert_wav_to_mp3(wav_path):
    """Converts a WAV file to 96 kbps MP3."""
    mp3_path = wav_path.replace(".wav", ".mp3")
    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3", bitrate="96k")
    print(f"MP3 file saved: {mp3_path}")

def process_text_file(text_file, base_directory, tonal_dict):
    """Processes a single text file and converts it to tone-based audio."""
    input_folder = os.path.join(base_directory, "Input")
    output_folder = os.path.join(base_directory, "Output")
    os.makedirs(output_folder, exist_ok=True)
    
    input_path = os.path.join(input_folder, text_file)
    output_audio_path = os.path.join(output_folder, text_file.replace(".txt", ""))
    
    sample_rate = 16000  # 16kHz encoding
    duration = 0.15  # 150ms per tone
    silence_duration = 0.05  # 50ms for word spacing
    punctuation_silence = 0.15  # 150ms for punctuation
    amplitude = 32767  # Max amplitude for 16-bit audio
    max_file_size = 100 * 1024 * 1024  # 100MB limit per WAV file
    
    with open(input_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    words_and_punct = re.findall(r'\b\w+\b|[.,!?;]', text)
    wave_data = []  # Use list instead of NumPy for efficiency
    
    print(f"Processing {len(words_and_punct)} words and punctuation marks in {text_file}...")
    file_index = 1
    
    for item in words_and_punct:
        freq = tonal_dict.get(item, 440)  # Get tone or default to A4
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)
        wave_data.append(tone)
        
        silence_length = int(sample_rate * (punctuation_silence if item in ".,!?;" else silence_duration))
        wave_data.append(np.zeros(silence_length, dtype=np.int16))  # Add silence between words
        
        # Convert list to NumPy array and check size
        if len(wave_data) > 0 and sum(arr.nbytes for arr in wave_data) >= max_file_size:
            wave_data = np.concatenate(wave_data)  # Convert list to array
            file_part_path = f"{output_audio_path}_part{file_index}.wav"
            
            with wave.open(file_part_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(wave_data.tobytes())
            print(f"Audio file saved: {file_part_path}")
            convert_wav_to_mp3(file_part_path)  # Convert to MP3
            
            file_index += 1  # Increment file index
            wave_data = []  # Reset data buffer
    
    if wave_data:
        wave_data = np.concatenate(wave_data)  # Convert remaining data to array
        final_file_path = f"{output_audio_path}_part{file_index}.wav"
        with wave.open(final_file_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(wave_data.tobytes())
        print(f"Audio file saved: {final_file_path}")
        convert_wav_to_mp3(final_file_path)  # Convert to MP3

def run_parallel_instance(base_directory, instance_name, text_files):
    """Runs an independent processing instance."""
    tonal_dict_folder = os.path.join(base_directory, "tonal_dict")
    tonal_dict = load_combined_tonal_dictionary(tonal_dict_folder)
    print(f"Starting {instance_name} with {len(text_files)} files...")
    
    for text_file in text_files:
        process_text_file(text_file, base_directory, tonal_dict)

def parallel_instances(base_directory):
    """Splits workload between two parallel instances."""
    input_folder = os.path.join(base_directory, "Input")
    text_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]
    
    half = len(text_files) // 2
    files_para1 = text_files[:half]
    files_para2 = text_files[half:]
    
    proc1 = multiprocessing.Process(target=run_parallel_instance, args=(base_directory, "Para1", files_para1))
    proc2 = multiprocessing.Process(target=run_parallel_instance, args=(base_directory, "Para2", files_para2))
    
    proc1.start()
    proc2.start()
    
    proc1.join()
    proc2.join()

# Example usage:
if __name__ == "__main__":
    base_dir = r"C:\\Users\\mydyi\\Desktop\\Word to tone"
    parallel_instances(base_dir)
