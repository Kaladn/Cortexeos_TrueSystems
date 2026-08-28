import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']
op = CenterRepulsionOperator()

print("Testing analyze() on training examples...")
for i, ex in enumerate(task['train']):
    input_grid = np.array(ex['input'])
    output_grid = np.array(ex['output'])
    
    result = op.analyze(input_grid, output_grid)
    print(f"Example {i+1}: {result}")
    
    if result is None:
        # Debug why it's failing
        H, W = input_grid.shape
        midpoint = H / 2.0
        print(f"  Grid: {H}x{W}, midpoint: {midpoint}")
        
        input_shapes = op._extract_shapes(input_grid)
        output_shapes = op._extract_shapes(output_grid)
        print(f"  Input shapes: {len(input_shapes)}")
        print(f"  Output shapes: {len(output_shapes)}")
        
        if len(input_shapes) == len(output_shapes):
            upper_out = [s for s in output_shapes if s['center_row'] < midpoint]
            lower_out = [s for s in output_shapes if s['center_row'] >= midpoint]
            
            print(f"  Upper shapes: {len(upper_out)}, Lower shapes: {len(lower_out)}")
            
            if len(upper_out) > 0:
                upper_max_row = max(s['bbox'][2] for s in upper_out)
                print(f"  Upper max row: {upper_max_row}")
            
            if len(lower_out) > 0:
                lower_min_row = min(s['bbox'][0] for s in lower_out)
                print(f"  Lower min row: {lower_min_row}")
                
                if len(upper_out) > 0:
                    gap = lower_min_row - upper_max_row - 1
                    print(f"  Gap: {gap}")
