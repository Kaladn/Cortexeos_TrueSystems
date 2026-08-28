"""Debug why examples 2 and 4 fail"""
import json
import numpy as np

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
task = data['b8cdaf2b']

for i in [2, 4]:  # Failed examples
    ex = task['train'][i-1]
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nExample {i}:")
    print("Input:")
    for row in inp:
        print("  " + " ".join(str(x) for x in row))
    print("Output:")
    for row in out:
        print("  " + " ".join(str(x) for x in row))
    
    # Check bottom structure
    H, W = inp.shape
    for r in range(H-1, -1, -1):
        if np.any(inp[r] != 0):
            print(f"\nBottom row: {r}")
            print(f"  Content: {list(inp[r])}")
            
            # Check row above too
            if r > 0:
                print(f"Row above ({r-1}): {list(inp[r-1])}")
            break
