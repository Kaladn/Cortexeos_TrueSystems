"""Find tasks with simple size preservation (same input/output dimensions)"""
import json
import numpy as np
import random

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))

solved = ['007bbfb7', '332efdb3', '3befdf3e', '496994bd', '5582e5ca', '5b6cbef5',
          '60c09cac', '67a3c6ac', '68b16354', '9172f3a0', 'a416b8f3', 'ac0a08a4',
          'b1948b0a', 'c59eb873', 'c8f0f002', 'd511f180', 'd5d6de2d', 'f25ffba3']

# Find tasks where all examples have same input/output size
candidates = []

for task_id in data.keys():
    if task_id in solved:
        continue
    
    task = data[task_id]
    same_size = True
    
    for ex in task['train']:
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        if inp.shape != out.shape:
            same_size = False
            break
    
    if same_size:
        candidates.append(task_id)

print(f"Found {len(candidates)} tasks with size-preserving transforms")
print(f"\nRandom sample of 10:")

random.seed()
sample = random.sample(candidates, min(10, len(candidates)))

for tid in sample:
    task = data[tid]
    ex = task['train'][0]
    inp = np.array(ex['input'])
    print(f"  {tid}: {inp.shape[0]}×{inp.shape[1]}")
