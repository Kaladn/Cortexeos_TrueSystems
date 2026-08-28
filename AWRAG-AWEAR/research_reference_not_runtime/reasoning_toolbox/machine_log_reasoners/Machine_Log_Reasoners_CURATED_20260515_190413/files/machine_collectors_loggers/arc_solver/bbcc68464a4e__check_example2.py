"""
Check example 2 shapes and dimensions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for i, ex in enumerate(task['train'], 1):
    print(f"\n{'='*60}")
    print(f"EXAMPLE {i}")
    print(f"{'='*60}")
    
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nGrid size: {inp.shape}")
    print(f"\nOutput:")
    print(out)
