"""Debug why 3befdf3e isn't detected in sweep"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

# Load task 3befdf3e
train_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
with open(train_path) as f:
    train_tasks = json.load(f)

task = train_tasks['3befdf3e']
operator = CenterHaloExpansionOperator()

print("Testing 3befdf3e with sweep logic:")
print("=" * 60)

# Try to learn from first training example
params = None
for i, example in enumerate(task['train']):
    input_arr = np.array(example['input'])
    output_arr = np.array(example['output'])
    
    print(f"\nExample {i+1}:")
    print(f"  Input shape: {input_arr.shape}")
    print(f"  Output shape: {output_arr.shape}")
    
    detected_params = operator.analyze(input_arr, output_arr)
    print(f"  Detected params: {detected_params}")
    
    if detected_params:
        params = detected_params
        print(f"  ✅ Found params!")
        break
    else:
        print(f"  ❌ No params detected")

if params:
    print(f"\nUsing params: {params}")
    print("\nTesting all training examples:")
    
    matches = 0
    for i, example in enumerate(task['train']):
        input_arr = np.array(example['input'])
        output_arr = np.array(example['output'])
        
        generated = operator.apply(input_arr, params)
        match = np.array_equal(generated, output_arr)
        
        print(f"  Example {i+1}: {'✅ MATCH' if match else '❌ MISMATCH'}")
        
        if match:
            matches += 1
    
    print(f"\nTotal: {matches}/{len(task['train'])} matches")
else:
    print("\n❌ Could not detect params from any training example")
