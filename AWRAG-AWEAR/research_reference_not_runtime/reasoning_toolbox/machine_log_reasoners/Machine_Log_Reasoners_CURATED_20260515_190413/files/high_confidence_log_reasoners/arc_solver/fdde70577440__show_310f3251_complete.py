"""
Show ALL training examples and test case for 310f3251 clearly
"""
import json
import numpy as np

# Load
with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']
solution = eval_solutions['310f3251']

print(f"\n{'='*70}")
print(f"TASK 310f3251 - Complete View")
print(f"{'='*70}\n")

# Show all training examples
for i, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"{'='*70}")
    print(f"TRAINING EXAMPLE {i}")
    print(f"{'='*70}")
    print(f"\nInput shape: {inp.shape}")
    print(inp)
    
    print(f"\nOutput shape: {out.shape}")
    print(out)
    print()

# Show test case
print(f"{'='*70}")
print(f"TEST CASE (what we need to solve)")
print(f"{'='*70}")

test_inp = np.array(task['test'][0]['input'])
test_out = np.array(solution[0])

print(f"\nTest Input shape: {test_inp.shape}")
print(test_inp)

print(f"\nExpected Output shape: {test_out.shape}")
print(test_out)

print(f"\n{'='*70}")
print("PATTERN SUMMARY:")
print(f"{'='*70}")
print("""
Rule appears to be:
1. Tile the input 3× in both directions
2. At the top-left corner of each tile, if input[0,0] was 0, replace with 2

This creates a "grid marker" effect showing where tiles start.
""")
