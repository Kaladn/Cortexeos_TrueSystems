"""Test if the anti-diagonal color determines the first color in Latin square."""

import json
import numpy as np

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

print("="*80)
print("ANTI-DIAGONAL ANCHOR RULE TEST")
print("="*80)

for i, example in enumerate(task['train']):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"\n{'='*80}")
    print(f"TRAINING EXAMPLE {i+1}")
    print(f"{'='*80}")
    
    # Extract 3 colors from input
    colors = sorted([c for c in np.unique(inp) if c != 0])
    print(f"Input colors: {colors}")
    
    # Output pattern first row
    pattern = list(out[0, :3])
    print(f"Output pattern first row: {pattern}")
    
    # Anti-diagonal of OUTPUT (top-right to bottom-left through center)
    # For 7x7: (0,6), (1,5), (2,4), (3,3), (4,2), (5,1), (6,0)
    H = out.shape[0]
    anti_diag_vals = [int(out[i, H-1-i]) for i in range(H)]
    print(f"Anti-diagonal values: {anti_diag_vals}")
    
    # Check if all same
    if len(set(anti_diag_vals)) == 1:
        anchor = anti_diag_vals[0]
        print(f"✅ Anti-diagonal is UNIFORM: {anchor}")
        print(f"   First color in pattern: {pattern[0]}")
        print(f"   MATCH: {anchor == pattern[0]}")
    else:
        print(f"❌ Anti-diagonal is NOT uniform: {set(anti_diag_vals)}")

# Test example (use solution file since test has no output in challenge)
print(f"\n{'='*80}")
print(f"TEST EXAMPLE (from training solutions)")
print(f"{'='*80}")

test_inp = np.array(task['test'][0]['input'])
# This is a training task, so test output is in training solutions
test_out = np.array(solutions['05269061'][0])

colors = sorted([c for c in np.unique(test_inp) if c != 0])
print(f"Input colors: {colors}")

pattern = list(test_out[0, :3])
print(f"Output pattern first row: {pattern}")

H = test_out.shape[0]
anti_diag_vals = [int(test_out[i, H-1-i]) for i in range(H)]
print(f"Anti-diagonal values: {anti_diag_vals}")

if len(set(anti_diag_vals)) == 1:
    anchor = anti_diag_vals[0]
    print(f"✅ Anti-diagonal is UNIFORM: {anchor}")
    print(f"   First color in pattern: {pattern[0]}")
    print(f"   MATCH: {anchor == pattern[0]}")

print(f"\n{'='*80}")
print(f"SUMMARY: ANTI-DIAGONAL ANCHOR RULE")
print(f"{'='*80}")
print("Rule: The color that appears uniformly on the anti-diagonal")
print("      of the OUTPUT grid is the FIRST color (c0) in the")
print("      Latin square pattern [c0, c1, c2]")
print("="*80)
