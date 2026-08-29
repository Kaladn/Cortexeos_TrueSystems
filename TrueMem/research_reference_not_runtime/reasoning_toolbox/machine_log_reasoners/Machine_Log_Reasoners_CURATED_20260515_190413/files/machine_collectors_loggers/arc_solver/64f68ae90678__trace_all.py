import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

d = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))

for ex_num, ex in enumerate(d['ac2e8ecf']['train'], 1):
    inp = np.array(ex['input'])
    expected = np.array(ex['output'])
    
    H = inp.shape[0]
    mid = H / 2.0
    
    print(f"\nExample {ex_num}: H={H}, midpoint={mid}")
    print("="*60)
    
    op = CenterRepulsionOperator()
    shapes = op._extract_shapes(inp)
    
    for s in shapes:
        direction = "UP" if s['center_row'] < mid else "DOWN"
        min_row = s['bbox'][0]
        max_row = s['bbox'][2]
        
        if s['center_row'] < mid:
            target = 0
            new_min = 0
        else:
            target = H - 1
            new_min = H - (max_row - min_row + 1)
        
        print(f"Color {s['color']}: center={s['center_row']:.1f}, rows {min_row}-{max_row}")
        print(f"  Direction: {direction}, will move to row {new_min}")
    
    # Run and check
    result = op.apply(inp, {})
    match = np.array_equal(result, expected)
    diffs = np.sum(result != expected)
    print(f"\nResult: {'PASS' if match else f'FAIL ({diffs} cells differ)'}")
