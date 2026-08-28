"""
Test LatticeRoleRecolorOperator on one known periodic task
"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import LatticeRoleRecolorOperator, merge_operator_params

with open("arc-prize-2024/arc-agi_training_challenges.json", "r") as f:
    train_challenges = json.load(f)

with open("arc-prize-2024/arc-agi_training_solutions.json", "r") as f:
    train_solutions = json.load(f)

task_id = "05269061"
task = train_challenges[task_id]

print(f"Testing LatticeRoleRecolorOperator on {task_id}")
print("=" * 70)

op = LatticeRoleRecolorOperator()

# Analyze training examples
train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) for ex in task["train"]]

params_list = []
for i, (inp, out) in enumerate(train_pairs):
    print(f"\nTrain example {i+1}:")
    print(f"  Input: {inp.shape}, Output: {out.shape}")
    
    params = op.analyze(inp, out)
    if params is None:
        print(f"  ❌ Analyze returned None")
    else:
        print(f"  ✅ Params: k={params['k']}, m={params['m']}")
        print(f"     Output pattern keys: {list(params['output_pattern'].keys())[:5]}...")
        print(f"     Input pattern keys: {list(params['input_pattern'].keys())[:5]}...")
        params_list.append(params)

if len(params_list) == len(train_pairs):
    print(f"\n✅ All {len(params_list)} training examples matched")
    
    # Try merge
    merged = merge_operator_params(op, params_list)
    if merged is None:
        print("❌ Merge failed")
    else:
        print(f"✅ Merge succeeded: k={merged['k']}, m={merged['m']}")
        
        # Test on test example
        test_input = np.array(task["test"][0]["input"])
        expected = np.array(train_solutions[task_id][0])
        
        print(f"\nApplying to test:")
        print(f"  Test input: {test_input.shape}")
        print(f"  Expected output: {expected.shape}")
        
        predicted = op.apply(test_input, merged)
        print(f"  Predicted output: {predicted.shape}")
        
        match = np.array_equal(predicted, expected)
        if match:
            print(f"  ✅ PERFECT MATCH!")
        else:
            diff = np.sum(predicted != expected)
            print(f"  ❌ {diff} pixels different")
            
            # Show a sample
            print(f"\n  Sample (first 3x3):")
            print(f"  Test input:\n{test_input[:3, :3]}")
            print(f"  Expected:\n{expected[:3, :3]}")
            print(f"  Predicted:\n{predicted[:3, :3]}")
else:
    print(f"\n❌ Only {len(params_list)}/{len(train_pairs)} examples matched")
