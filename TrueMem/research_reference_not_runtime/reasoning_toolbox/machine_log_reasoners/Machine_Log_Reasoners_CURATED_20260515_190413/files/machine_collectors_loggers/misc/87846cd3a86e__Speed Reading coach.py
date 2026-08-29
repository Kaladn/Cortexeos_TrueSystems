import os
import json
import numpy as np
import time
import wave
import re
from tqdm import tqdm
from scipy.signal import find_peaks
from scipy.fft import fft
import pygame

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

def speed_reading_game(base_directory):
    """Creates a speed reading trainer that plays audio while displaying synchronized text."""
    input_folder = os.path.join(base_directory, "Output")
    decoded_folder = os.path.join(base_directory, "Decoded")
    
    audio_files = [f for f in os.listdir(input_folder) if f.endswith(".wav")]
    if not audio_files:
        print("No audio files found. Run text-to-tone conversion first.")
        return
    
    pygame.init()
    screen = pygame.display.set_mode((800, 200))
    pygame.display.set_caption("Speed Reading Trainer")
    font = pygame.font.Font(None, 36)
    
    for audio_file in audio_files:
        audio_path = os.path.join(input_folder, audio_file)
        text_path = os.path.join(decoded_folder, audio_file.replace(".wav", ".txt"))
        
        if not os.path.exists(text_path):
            print(f"Decoded text missing for {audio_file}. Skipping...")
            continue
        
        with open(text_path, 'r', encoding='utf-8') as file:
            words = file.read().split()
        
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        
        clock = pygame.time.Clock()
        index = 0
        speed_factor = 1.0  # Adjusts playback speed dynamically
        
        running = True
        while running and index < len(words):
            screen.fill((0, 0, 0))
            text_surface = font.render(words[index], True, (255, 255, 255))
            screen.blit(text_surface, (400 - text_surface.get_width() // 2, 100))
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.mixer.music.stop()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        speed_factor = min(2.0, speed_factor + 0.1)
                        pygame.mixer.music.set_volume(speed_factor)
                    elif event.key == pygame.K_DOWN:
                        speed_factor = max(0.5, speed_factor - 0.1)
                        pygame.mixer.music.set_volume(speed_factor)
            
            index += 1
            clock.tick(2 * speed_factor)  # Adjust reading speed based on input
        
        pygame.mixer.music.stop()
    
    pygame.quit()

# Example usage:
base_dir = r"C:\Users\mydyi\Desktop\Word to tone"
audio_to_text(base_dir)
speed_reading_game(base_dir)
