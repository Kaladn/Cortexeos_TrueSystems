"""Show the 4 new tasks our system solves."""
import json
import numpy as np

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    train_data = json.load(f)

new_tasks = ['a416b8f3', 'b1948b0a', 'c8f0f002', 'd511f180']

for task_id in new_tasks:
    print(f"\n{'='*70}")
    print(f"TASK: {task_id}")
    print(f"{'='*70}")
    
    task = train_data[task_id]
    
    for i, ex in enumerate(task['train'], 1):
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        
        print(f"\nExample {i}:")
        print(f"  Input shape:  {inp.shape}")
        print(f"  Output shape: {out.shape}")
        print(f"  Expansion:    {out.shape[0]/inp.shape[0]:.1f}x rows, {out.shape[1]/inp.shape[1]:.1f}x cols")
        
        # Check if it's simple tiling
        if out.shape[0] % inp.shape[0] == 0 and out.shape[1] % inp.shape[1] == 0:
            factor_r = out.shape[0] // inp.shape[0]
            factor_c = out.shape[1] // inp.shape[1]
            
            if factor_r == factor_c:
                # Check if it's exact tiling
                tiled = np.tile(inp, (factor_r, factor_c))
                if np.array_equal(tiled, out):
                    print(f"  Pattern:      ✓ Simple {factor_r}x tiling (EXACT MATCH)")
                else:
                    print(f"  Pattern:      {factor_r}x tiling with modifications")
            else:
                print(f"  Pattern:      {factor_r}x{factor_c} rectangular tiling")
        
        print(f"\n  Input:")
        print(inp)
        print(f"\n  Output:")
        print(out)
    
    # Show test case
    test_inp = np.array(task['test'][0]['input'])
    print(f"\nTest Input shape: {test_inp.shape}")
    print(test_inp)
