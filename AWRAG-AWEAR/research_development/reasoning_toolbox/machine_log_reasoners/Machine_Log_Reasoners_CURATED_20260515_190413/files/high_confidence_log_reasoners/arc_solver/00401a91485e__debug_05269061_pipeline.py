"""Debug why task 05269061 is failing in the main pipeline."""
import sys
sys.path.insert(0, 'cod_616')

import json
import numpy as np
from arc_organ.arc_pipeline import ArcPipeline

# Load task 05269061
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task_id = '05269061'
task = challenges[task_id]
task_solutions = solutions[task_id]

print("="*80)
print(f"Debugging task {task_id} in pipeline")
print("="*80)

pipeline = ArcPipeline()

# Process training examples
training_pairs = []
for i, ex in enumerate(task['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    training_pairs.append((inp, out))
    print(f"\nTraining example {i+1}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Output shape: {out.shape}")

# Test on test case
test_inp = np.array(task['test'][0]['input'])
expected_out = np.array(task_solutions[0])

print(f"\nTest case:")
print(f"  Input shape: {test_inp.shape}")
print(f"  Expected output shape: {expected_out.shape}")

# Try to solve
result = pipeline.solve(task_id, training_pairs, [test_inp])

if result and len(result) > 0:
    pred = result[0]
    print(f"\n✓ Got prediction, shape: {pred.shape}")
    
    if np.array_equal(pred, expected_out):
        print("✅ PERFECT MATCH!")
    else:
        print("❌ Mismatch")
        print(f"Expected first row: {expected_out[0,:].tolist()}")
        print(f"Got first row:      {pred[0,:].tolist()}")
        
        # Check which operator was used
        print(f"\nOperators tried: {pipeline.last_operators_tried if hasattr(pipeline, 'last_operators_tried') else 'N/A'}")
else:
    print("\n❌ No prediction generated")
    print("No operator matched the task")
