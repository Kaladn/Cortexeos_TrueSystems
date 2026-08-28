import json
import numpy as np

with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

print("TASK: ac2e8ecf - Spatial Reasoning")
print("=" * 60)

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nExample {i}:")
    print(f"Input: {inp.shape}")
    print(inp)
    print(f"\nOutput: {out.shape}")
    print(out)
    print()
