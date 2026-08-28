import json
import numpy as np

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))

task_ids = ['60c09cac', '9172f3a0', 'c59eb873']

for task_id in task_ids:
    if task_id not in data:
        print(f"{task_id}: NOT IN DATASET")
        continue
        
    task = data[task_id]
    print(f"\n{task_id}:")
    
    for i, ex in enumerate(task['train'], 1):
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        
        H_in, W_in = inp.shape
        H_out, W_out = out.shape
        
        if H_out % H_in == 0 and W_out % W_in == 0:
            block_h = H_out // H_in
            block_w = W_out // W_in
            non_zero = np.count_nonzero(inp)
            
            print(f"  Ex{i}: {H_in}×{W_in} → {H_out}×{W_out}, block={block_h}×{block_w}, non_zero={non_zero}")
        else:
            print(f"  Ex{i}: NOT block expansion ({H_in}×{W_in} → {H_out}×{W_out})")
