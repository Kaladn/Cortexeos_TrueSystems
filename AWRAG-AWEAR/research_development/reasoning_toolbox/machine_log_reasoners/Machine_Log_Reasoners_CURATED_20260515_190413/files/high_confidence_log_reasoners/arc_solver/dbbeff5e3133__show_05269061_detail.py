"""Show detailed view of task 05269061 to understand the color mapping pattern."""

import json
import numpy as np
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import LatticeRoleRecolorOperator

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)

task = challenges['05269061']

print("TASK 05269061 - Detailed Analysis")
print("=" * 80)

# Show all training examples
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nTraining Example {i}:")
    print(f"  Input colors: {sorted(set(inp.flatten()))}")
    print(f"  Output colors: {sorted(set(out.flatten()))}")
    print(f"\n  Input (7x7):")
    print(inp)
    print(f"\n  Output (7x7):")
    print(out)
    print()

# Show test
test_inp = np.array(task['test'][0]['input'])
test_out = np.array(task['test'][0]['output'])

print(f"\nTest:")
print(f"  Input colors: {sorted(set(test_inp.flatten()))}")
print(f"  Output colors: {sorted(set(test_out.flatten()))}")
print(f"\n  Input (7x7):")
print(test_inp)
print(f"\n  Expected Output (7x7):")
print(test_out)

# Analyze with operator
print("\n" + "=" * 80)
print("OPERATOR ANALYSIS")
print("=" * 80)

op = LatticeRoleRecolorOperator()

# Analyze all training examples
params_list = []
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    params = op.analyze(inp, out)
    params_list.append(params)
    
    print(f"\nTraining Example {i} - Detected Pattern:")
    print(f"  Lattice: k={params['k']}, m={params['m']}")
    print(f"  Input pattern (lattice_pos -> input_color):")
    for pos in sorted(params['input_pattern'].keys()):
        print(f"    {pos} -> {params['input_pattern'][pos]}")
    print(f"  Output pattern (lattice_pos -> output_color):")
    for pos in sorted(params['output_pattern'].keys()):
        print(f"    {pos} -> {params['output_pattern'][pos]}")

# Show what the test is doing
print("\n" + "=" * 80)
print("TEST INPUT ANALYSIS")
print("=" * 80)

k, m = 3, 3
print(f"\nTest input broken down by lattice position (k={k}, m={m}):")
test_by_pos = {}
for r in range(test_inp.shape[0]):
    for c in range(test_inp.shape[1]):
        pos = (r % k, c % m)
        color = int(test_inp[r, c])
        if pos not in test_by_pos:
            test_by_pos[pos] = []
        test_by_pos[pos].append(color)

for pos in sorted(test_by_pos.keys()):
    colors = test_by_pos[pos]
    unique, counts = np.unique(colors, return_counts=True)
    print(f"  Position {pos}: colors {list(zip(unique, counts))}")

print(f"\nTest output broken down by lattice position:")
out_by_pos = {}
for r in range(test_out.shape[0]):
    for c in range(test_out.shape[1]):
        pos = (r % k, c % m)
        color = int(test_out[r, c])
        if pos not in out_by_pos:
            out_by_pos[pos] = []
        out_by_pos[pos].append(color)

for pos in sorted(out_by_pos.keys()):
    colors = out_by_pos[pos]
    unique, counts = np.unique(colors, return_counts=True)
    print(f"  Position {pos}: colors {list(zip(unique, counts))}")
