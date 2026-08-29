"""Debug why ac0a08a4 isn't matching"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import BlockExpansionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac0a08a4']
op = BlockExpansionOperator()

print("=" * 60)
print("DEBUGGING ac0a08a4 with BlockExpansionOperator")
print("=" * 60)

train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
               for ex in task['train']]

params_list = []

for i, (inp, out) in enumerate(train_pairs, 1):
    print(f"\nExample {i}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Output shape: {out.shape}")
    
    params = op.analyze(inp, out)
    print(f"  Analyze result: {params}")
    
    if params is not None:
        params_list.append(params)
        
        # Test apply
        pred = op.apply(inp, params)
        match = np.array_equal(pred, out)
        print(f"  Apply match: {match}")

print(f"\n{'=' * 60}")
print(f"Params collected: {len(params_list)}/{len(train_pairs)}")
print(f"Params list: {params_list}")

# Test merge
if len(params_list) == len(train_pairs):
    from cod_616.arc_organ.arc_operators import merge_operator_params
    merged = merge_operator_params(op, params_list)
    print(f"Merged params: {merged}")
else:
    print("Cannot merge - not all examples matched")
