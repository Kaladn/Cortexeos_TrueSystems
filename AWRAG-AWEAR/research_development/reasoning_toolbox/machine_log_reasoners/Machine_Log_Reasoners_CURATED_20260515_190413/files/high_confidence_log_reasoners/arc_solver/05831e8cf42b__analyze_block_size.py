import json
import numpy as np

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
task = data['ac0a08a4']

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    non_zero = np.count_nonzero(inp)
    block_size = len(out) // len(inp)
    
    print(f"Ex{i}: non_zero={non_zero}, block_size={block_size}")
