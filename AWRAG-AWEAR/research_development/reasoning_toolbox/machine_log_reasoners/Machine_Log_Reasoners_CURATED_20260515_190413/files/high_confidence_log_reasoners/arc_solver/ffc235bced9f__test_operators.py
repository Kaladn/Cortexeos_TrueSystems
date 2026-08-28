"""Test the 6-1-6 operator system on known tasks."""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import solve_task, infer_rule_for_task, OPERATORS

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    train_data = json.load(f)

# Test on our 5 known solved tasks
known_tasks = ['007bbfb7', 'a416b8f3', 'b1948b0a', 'c8f0f002', 'd511f180']

print("="*70)
print("TESTING 6-1-6 OPERATOR SYSTEM")
print("="*70)

for task_id in known_tasks:
    task = train_data[task_id]
    
    # Convert to operator format
    train_pairs = [
        (np.array(ex['input']), np.array(ex['output']))
        for ex in task['train']
    ]
    
    test_inputs = [np.array(ex['input']) for ex in task['test']]
    
    # Infer rule
    op, params = infer_rule_for_task(train_pairs)
    
    print(f"\n{task_id}:")
    if op is None:
        print("  ❌ No operator matched")
    else:
        print(f"  ✅ Operator: {op.name}")
        print(f"  Params: {params}")
        
        # Test on first test case
        try:
            output = op.apply(test_inputs[0], params)
            print(f"  Generated output: {output.shape}")
        except Exception as e:
            print(f"  ⚠️  Apply failed: {e}")

print(f"\n{'='*70}")
print("OPERATOR PRIORITY ORDER:")
print(f"{'='*70}")
for i, op in enumerate(OPERATORS, 1):
    print(f"{i}. {op.name}")
