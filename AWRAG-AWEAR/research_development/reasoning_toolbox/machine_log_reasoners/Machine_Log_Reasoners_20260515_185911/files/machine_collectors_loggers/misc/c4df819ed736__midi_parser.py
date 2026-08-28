import mido

class MIDIParser:
    def __init__(self, file_path):
        self.mid = mido.MidiFile(file_path)
        self.events = []
        print(f"MIDIParser initialized with file: {file_path}")

    def extract_events(self):
        """Extracts note_on events from the MIDI file."""
        current_time_ticks = 0 # Mido messages store time as delta ticks from previous message
        ticks_per_beat = self.mid.ticks_per_beat if self.mid.ticks_per_beat else 480 # Common default
        tempo = 500000 # Default MIDI tempo (microseconds per beat)

        # Find the first tempo change event to set initial tempo if available
        for msg in self.mid:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
        
        print(f"Initial ticks_per_beat: {ticks_per_beat}, Initial tempo: {tempo} us/beat")

        for i, msg in enumerate(self.mid):
            # Convert delta ticks to absolute milliseconds from start
            # time_offset_ms = mido.tick2second(current_time_ticks, ticks_per_beat, tempo) * 1000
            # current_time_ticks += msg.time # Accumulate time in ticks
            
            # Mido's msg.time is delta time in ticks. We need to accumulate it.
            current_time_ticks += msg.time
            time_offset_seconds = mido.tick2second(current_time_ticks, ticks_per_beat, tempo)

            if msg.type == 'set_tempo': # Update tempo if it changes mid-track
                tempo = msg.tempo
                print(f"Tempo changed at tick {current_time_ticks} to {tempo} us/beat")

            if msg.type == 'note_on' and msg.velocity > 0: # Note_on with velocity 0 is often note_off
                self.events.append({
                    "pitch": msg.note, # MIDI note number (0-127)
                    "velocity": msg.velocity / 127.0, # Normalized velocity (0.0-1.0)
                    "time_offset_ticks": current_time_ticks, # Absolute time in MIDI ticks
                    "time_offset_seconds": time_offset_seconds, # Absolute time in seconds
                    "channel": msg.channel # MIDI channel (0-15)
                    # Duration would require tracking note_off events, more complex for v1
                })
        print(f"Extracted {len(self.events)} note_on events.")
        return self.events

def midi_event_to_ray_params(event):
    """
    Converts a single MIDI event (from MIDIParser.extract_events) 
    into a dictionary of ray parameters.
    This is a basic mapping; can be made more sophisticated.
    Output ray parameters are r, g, b (0-255), amplitude (0-1), phase (0-360).
    Origin and direction are set to default values for now.
    """
    pitch = event["pitch"]
    velocity = event["velocity"]
    time_offset_seconds = event["time_offset_seconds"]

    # Simple pitch to color mapping (can be improved)
    # Example: Use pitch for R, scaled pitch for G, another scale for B
    # Ensure values are within 0-255 for color
    r = pitch % 255
    g = (pitch * 2) % 255 
    b = (pitch * 3) % 255

    # Amplitude from velocity is already normalized (0-1)
    amplitude = velocity

    # Phase from time_offset (e.g., map seconds to degrees, wrapping around 360)
    # Example: 1 second = 36 degrees, so 10 seconds wraps around.
    # This is a simple example; a more meaningful mapping might be needed.
    phase = (time_offset_seconds * 36) % 360 # Simple scaling, can be refined

    # Default spatial attributes for now, as they are not derived from MIDI event in this basic version
    default_origin = [0.0, 0.0, 0.0]
    default_direction = [1.0, 0.0, 0.0] # Normalized

    ray_params = {
        "color_r": float(r),
        "color_g": float(g),
        "color_b": float(b),
        "amplitude": float(amplitude),
        "phase": float(phase),
        "origin_x": default_origin[0],
        "origin_y": default_origin[1],
        "origin_z": default_origin[2],
        "dir_x": default_direction[0],
        "dir_y": default_direction[1],
        "dir_z": default_direction[2],
        # Add other potential fields if needed by the Ray data structure later
        # "pitch_encoded": float(pitch), # If explicitly needed in Ray struct
        # "midi_velocity": float(event["velocity"]), # If raw velocity needed
        # "time_offset_ms_for_ray": float(time_offset_seconds * 1000) # If ms needed
    }
    return ray_params

if __name__ == '__main__':
    # This is a placeholder for testing. 
    # You'll need a sample MIDI file (e.g., "sample.mid") in the same directory.
    # Create a dummy MIDI file for testing if you don't have one.
    try:
        # Create a dummy MIDI file for basic testing
        mid_test = mido.MidiFile()
        track = mido.MidiTrack()
        mid_test.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
        track.append(mido.Message('note_on', note=60, velocity=64, time=480, channel=0))
        track.append(mido.Message('note_off', note=60, velocity=64, time=480, channel=0))
        track.append(mido.Message('note_on', note=64, velocity=80, time=0, channel=0)) # Chord
        track.append(mido.Message('note_on', note=67, velocity=70, time=0, channel=0)) # Chord
        track.append(mido.Message('note_off', note=64, velocity=64, time=960, channel=0))
        track.append(mido.Message('note_off', note=67, velocity=64, time=0, channel=0))
        mid_test.save('/home/ubuntu/test_midi_file.mid')
        print("Dummy MIDI file created: /home/ubuntu/test_midi_file.mid")

        parser = MIDIParser('/home/ubuntu/test_midi_file.mid')
        extracted_midi_events = parser.extract_events()
        
        print(f"\n--- Extracted MIDI Events (first 5) ---")
        for i, event_data in enumerate(extracted_midi_events[:5]):
            print(f"Event {i}: {event_data}")

        print(f"\n--- Converted Ray Parameters (from first 5 MIDI events) ---")
        generated_rays_params = []
        for i, event_data in enumerate(extracted_midi_events[:5]):
            ray_p = midi_event_to_ray_params(event_data)
            generated_rays_params.append(ray_p)
            print(f"From MIDI Event {i}: {ray_p}")
        
        # Further steps would involve creating the flat numpy array of these ray_params
        # to feed into the GPUTaskManager, similar to create_input_rays_flat

    except FileNotFoundError:
        print("Error: test_midi_file.mid not found. Please place a MIDI file with this name or update path.")
    except Exception as e:
        print(f"An error occurred during MIDI parsing test: {e}")

