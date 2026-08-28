"""
Show task 310f3251 (the other 2×2 → 6×6 task that we're not catching)
"""
import json
import numpy as np

# Load evaluation challenges
with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task_id = '310f3251'
task = eval_challenges[task_id]
solution = eval_solutions[task_id]

print(f"\n{'='*60}")
print(f"Task: {task_id} (2×2 → 6×6)")
print(f"{'='*60}")

print(f"\n📚 TRAINING EXAMPLES ({len(task['train'])}):\n")

for i, example in enumerate(task['train'], 1):
    input_grid = np.array(example['input'])
    output_grid = np.array(example['output'])
    
    print(f"Example {i}:")
    print(f"\nInput ({input_grid.shape}):")
    print(input_grid)
    
    print(f"\nOutput ({output_grid.shape}):")
    print(output_grid)
    
    print("\n" + "-"*60 + "\n")

print(f"\n🎯 TEST CASE:\n")
test_input = np.array(task['test'][0]['input'])
expected_output = np.array(solution[0])

print(f"Test Input ({test_input.shape}):")
print(test_input)

print(f"\nExpected Output ({expected_output.shape}):")
print(expected_output)

# Test if it's sandwich tiling
print(f"\n{'='*60}")
print("PATTERN ANALYSIS:")
print(f"{'='*60}\n")

print("Testing sandwich tiling (like 00576224):")
print("  - Rows 1-2: tile 3× horizontally")
print("  - Rows 3-4: flip columns, tile 3×")
print("  - Rows 5-6: repeat rows 1-2")

rows_1_2 = np.tile(test_input, (1, 3))
rows_3_4 = np.tile(np.flip(test_input, axis=1), (1, 3))
rows_5_6 = rows_1_2
sandwich = np.vstack([rows_1_2, rows_3_4, rows_5_6])

print(f"\nSandwich pattern would give:")
print(sandwich)

if np.array_equal(expected_output, sandwich):
    print("\n✓ MATCHES sandwich tiling!")
else:
    print("\n✗ Does NOT match sandwich tiling")
    
    # Try simple tiling
    print("\n\nTesting simple 3×3 tiling:")
    simple = np.tile(test_input, (3, 3))
    print(simple)
    
    if np.array_equal(expected_output, simple):
        print("\n✓ MATCHES simple tiling!")
    else:
        print("\n✗ Does NOT match simple tiling either")
        print("\nLet's look at the pattern more carefully...")
