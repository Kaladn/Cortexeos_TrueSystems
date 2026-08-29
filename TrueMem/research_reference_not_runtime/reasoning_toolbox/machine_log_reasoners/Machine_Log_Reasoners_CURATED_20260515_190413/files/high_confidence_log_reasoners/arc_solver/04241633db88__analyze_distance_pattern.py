import numpy as np
import json

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)
with open('arc-prize-2025/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = data['ac2e8ecf']

print("Analyzing distance from centerline vs movement direction")
print("="*70)

for ex_idx, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    H, W = inp.shape
    midpoint = H / 2.0
    
    print(f"\nExample {ex_idx}: Grid {H}x{W}, midpoint = {midpoint}")
    
    # Get colors and their movements
    colors = sorted(set(inp.flatten()) - {0})
    movements = []
    
    for color in colors:
        # Find this color in input
        in_mask = (inp == color)
        in_positions = np.argwhere(in_mask)
        if len(in_positions) == 0:
            continue
        in_center_row = in_positions[:, 0].mean()
        
        # Find this color in output
        out_mask = (out == color)
        out_positions = np.argwhere(out_mask)
        if len(out_positions) == 0:
            continue
        out_center_row = out_positions[:, 0].mean()
        
        dist_from_center = abs(in_center_row - midpoint)
        crosses = (in_center_row < midpoint) != (out_center_row < midpoint)
        
        movements.append({
            'color': color,
            'in_row': in_center_row,
            'out_row': out_center_row,
            'dist_from_center': dist_from_center,
            'crosses': crosses
        })
    
    # Sort by distance from center
    movements.sort(key=lambda m: m['dist_from_center'])
    
    for m in movements:
        hemisphere_in = "UPPER" if m['in_row'] < midpoint else "LOWER"
        hemisphere_out = "UPPER" if m['out_row'] < midpoint else "LOWER"
        cross_str = "→ CROSSES" if m['crosses'] else "→ stays"
        print(f"  Color {m['color']}: dist={m['dist_from_center']:.1f}, " +
              f"{hemisphere_in}({m['in_row']:.1f}) → {hemisphere_out}({m['out_row']:.1f}) {cross_str}")
