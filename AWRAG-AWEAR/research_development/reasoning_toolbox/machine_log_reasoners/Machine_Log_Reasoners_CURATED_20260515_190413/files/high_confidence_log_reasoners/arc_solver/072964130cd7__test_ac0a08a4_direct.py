"""Direct test of ac0a08a4 with all operators"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import OPERATORS, merge_operator_params

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task_id = 'ac0a08a4'
task = data[task_id]

train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
               for ex in task['train']]

print(f"Testing task {task_id}")
print(f"Training examples: {len(train_pairs)}")

# Try each operator
for op in OPERATORS:
    params_list = []
    
    for inp, out in train_pairs:
        params = op.analyze(inp, out)
        if params is None:
            break
        params_list.append(params)
    
    if len(params_list) == len(train_pairs):
        # All examples matched - try merge
        merged = merge_operator_params(op, params_list)
        if merged is not None:
            print(f"\n✅ MATCHED: {op.name}")
            print(f"   Params: {merged}")
            
            # Verify apply works
            for i, (inp, out) in enumerate(train_pairs, 1):
                pred = op.apply(inp, merged)
                match = np.array_equal(pred, out)
                print(f"   Example {i}: {'✓' if match else '✗'}")
            break
else:
    print("\n❌ NO OPERATOR MATCHED")
