import json
import numpy as np

with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['b8cdaf2b']

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\n{'='*60}")
    print(f"Example {i}: Input {inp.shape}")
    print(f"{'='*60}")
    
    for r in range(inp.shape[0]):
        print(f"Row {r}: {inp[r].tolist()}", end="")
        if np.all(inp[r] == 0):
            print(" <- ALL ZEROS")
        else:
            print()
    
    print(f"\nExpected output {out.shape}:")
    for r in range(out.shape[0]):
        print(f"Row {r}: {out[r].tolist()}")
