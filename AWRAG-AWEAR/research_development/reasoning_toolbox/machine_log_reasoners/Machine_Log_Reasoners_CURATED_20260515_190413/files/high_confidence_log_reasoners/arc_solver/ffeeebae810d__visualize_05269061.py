"""Visual display of task 05269061 to understand the pattern."""

import json
import numpy as np

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

COLOR_MAP = {
    0: '·',  # black/background
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    8: '8',
}

def visualize(grid, label=""):
    """Pretty print grid with color symbols."""
    if label:
        print(f"\n{label}")
    for row in grid:
        print('  ' + ' '.join(COLOR_MAP.get(int(c), str(c)) for c in row))

print("=" * 80)
print("TASK 05269061 - Visual Analysis")
print("=" * 80)

# Show all training examples
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    non_zero = sorted(set(inp.flatten()) - {0})
    
    print(f"\n{'='*80}")
    print(f"TRAINING EXAMPLE {i}")
    print(f"Non-zero colors in input: {non_zero}")
    print(f"{'='*80}")
    
    visualize(inp, "INPUT (7x7):")
    visualize(out, "OUTPUT (7x7):")
    
    # Show the 3x3 pattern
    print("\n  Output 3x3 repeating pattern:")
    pattern_3x3 = out[:3, :3]
    visualize(pattern_3x3, "")

# Show test
test_inp = np.array(task['test'][0]['input'])
test_out = np.array(solutions['05269061'][0])

non_zero = sorted(set(test_inp.flatten()) - {0})

print(f"\n{'='*80}")
print(f"TEST")
print(f"Non-zero colors in input: {non_zero}")
print(f"{'='*80}")

visualize(test_inp, "INPUT (7x7):")
visualize(test_out, "OUTPUT (7x7):")

print("\n  Output 3x3 repeating pattern:")
pattern_3x3 = test_out[:3, :3]
visualize(pattern_3x3, "")

print("\n" + "="*80)
print("PATTERN SUMMARY")
print("="*80)
print("\nTraining 1: Input colors {2,3,8} → Output pattern starts: 2 8 3")
print("Training 2: Input colors {1,2,4} → Output pattern starts: 2 4 1")
print("Training 3: Input colors {3,4,8} → Output pattern starts: 4 8 3")
print("Test:       Input colors {1,2,4} → Output pattern starts: 2 1 4")
print("\nNote: Training 2 and Test have same input colors {1,2,4}")
print("      but DIFFERENT output ordering!")
print("      Training 2: [2,4,1,...]")
print("      Test:       [2,1,4,...]")
