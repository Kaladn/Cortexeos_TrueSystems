import json
import yaml
import os
import uuid

# Input JSON file path (adjust as needed)
json_path = "config/neural_map.json"

# Output directory for CNFS Cube files
cn_output_dir = "cognitive_nodes"
os.makedirs(cn_output_dir, exist_ok=True)

# Load JSON
with open(json_path, 'r') as infile:
    neural_map = json.load(infile)

# Iterate and convert each entry
for entry_name, entry_data in neural_map.items():

    # Build lawful Cube structure
    cube = {
        'cube_id': str(uuid.uuid4()),
        'cube_type': entry_data.get('type', 'undefined'),
        'cube_version': '1.0.0',
        'faces': {
            'top_face': {
                'identity': {
                    'uuid': str(uuid.uuid4()),
                    'version': '1.0.0',
                    'type': entry_data.get('type', 'undefined')
                }
            },
            'bottom_face': {
                'contracts': entry_data.get('contracts', [])
            },
            'front_face': {
                'neuron_targets': [entry_data.get('path')] if 'path' in entry_data else []
            },
            'back_face': {
                'dependencies': entry_data.get('dependencies', [])
            },
            'left_face': {
                'input_signature': entry_data.get('harmonic_signature', {}).get('input', {})
            },
            'right_face': {
                'output_signature': entry_data.get('harmonic_signature', {}).get('output', {})
            },
            'center_core': {
                'resonance_answers': {
                    'last_activation': None,
                    'last_result_vector': [],
                    'success_weight': None,
                    'failure_weight': None,
                    'error_trace': []
                }
            }
        }
    }

    # Write Cube Node to CN file
    cn_filename = f"{entry_name}.cn"
    cn_path = os.path.join(cn_output_dir, cn_filename)

    with open(cn_path, 'w') as outfile:
        yaml.dump(cube, outfile, default_flow_style=False)

    print(f"[CNFS] Generated: {cn_path}")
