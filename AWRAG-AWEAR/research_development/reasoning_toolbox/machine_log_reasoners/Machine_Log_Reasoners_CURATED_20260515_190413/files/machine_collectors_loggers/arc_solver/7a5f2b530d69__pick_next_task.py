import json
import random

# Load dataset
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

# Already solved tasks (updated for 2025)
solved = ['007bbfb7', '332efdb3', '3befdf3e', '496994bd', '5582e5ca', '5b6cbef5',
          '60c09cac', '67a3c6ac', '68b16354', '9172f3a0', 'a416b8f3', 'ac0a08a4',
          'b1948b0a', 'b8cdaf2b', 'c59eb873', 'c8f0f002', 'd511f180', 'd5d6de2d', 'f25ffba3']

# Get unsolved tasks
unsolved = [tid for tid in data.keys() if tid not in solved]

# Pick a random one
random.seed(42)
task_id = random.choice(unsolved)
task = data[task_id]

print(f"\n{'='*60}")
print(f"NEXT TASK: {task_id}")
print(f"{'='*60}")
print(f"\nTraining examples: {len(task['train'])}")
print(f"Test examples: {len(task['test'])}")

for i, example in enumerate(task['train'], 1):
    inp = example['input']
    out = example['output']
    print(f"\nExample {i}:")
    print(f"  Input:  {len(inp)}×{len(inp[0])} grid")
    print(f"  Output: {len(out)}×{len(out[0])} grid")
    
    # Show the grids
    print(f"\n  Input grid:")
    for row in inp:
        print(f"    {row}")
    print(f"\n  Output grid:")
    for row in out:
        print(f"    {row}")

print(f"\n{'='*60}\n")
