"""
Test full pipeline on 310f3251 - Diagonal Marker Tiling
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from cod_616.arc_organ.arc_task_runner import ArcGridPair
from cod_616.arc_organ.arc_two_attempt_sampler import ARCTwoAttemptSampler

# Load 310f3251 from evaluation set
with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_data = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task_id = '310f3251'
task_data = eval_data[task_id]
task_solution = eval_solutions[task_id]

print(f"🎯 Testing full pipeline on {task_id}")
print(f"Training examples: {len(task_data['train'])}")
print(f"Test cases: {len(task_data['test'])}")

# Parse training examples
train_examples = []
for i, ex in enumerate(task_data['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    print(f"Example {i+1}: {inp.shape} → {out.shape}")
    train_examples.append(ArcGridPair(inp, out))

# Create sampler and generate attempts
sampler = ARCTwoAttemptSampler()
test_input = np.array(task_data['test'][0]['input'])
expected_output = np.array(task_solution[0])

print(f"\n{'='*60}")
print(f"TESTING ON TEST CASE")
print(f"{'='*60}")
print(f"Input shape: {test_input.shape}")
print(f"Expected output shape: {expected_output.shape}")

attempt_1, attempt_2 = sampler.generate_attempts(train_examples, test_input)

# Check attempts
match_1 = np.array_equal(attempt_1, expected_output)
match_2 = np.array_equal(attempt_2, expected_output)

print(f"\nAttempt 1: shape {attempt_1.shape}")
print(f"  Match: {'✅ YES!' if match_1 else '❌ No'}")

print(f"\nAttempt 2: shape {attempt_2.shape}")
print(f"  Match: {'✅ YES!' if match_2 else '❌ No'}")

if match_1 or match_2:
    print(f"\n{'🏆'*20}")
    print(f"🎯🎯🎯 TASK 310f3251 SOLVED VIA PIPELINE! 🎯🎯🎯")
    print(f"{'🏆'*20}")
else:
    print(f"\n❌ No attempt matched expected output")
