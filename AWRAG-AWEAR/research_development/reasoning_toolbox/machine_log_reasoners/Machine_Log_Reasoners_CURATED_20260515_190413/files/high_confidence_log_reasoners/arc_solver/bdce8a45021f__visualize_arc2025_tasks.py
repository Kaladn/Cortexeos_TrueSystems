"""
Visualize the 14 high-confidence arc-2025 tasks with PNG outputs
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from pathlib import Path

# ARC color palette
ARC_COLORS = [
    '#000000',  # 0: black
    '#0074D9',  # 1: blue
    '#FF4136',  # 2: red
    '#2ECC40',  # 3: green
    '#FFDC00',  # 4: yellow
    '#AAAAAA',  # 5: grey
    '#F012BE',  # 6: magenta
    '#FF851B',  # 7: orange
    '#7FDBFF',  # 8: sky
    '#870C25',  # 9: maroon
]

cmap = ListedColormap(ARC_COLORS)

def visualize_task(task_id, task_data, output_dir):
    """Generate PNG visualization for a single task"""
    train_examples = task_data['train']
    test_examples = task_data['test']
    
    n_train = len(train_examples)
    n_test = len(test_examples)
    
    # Create figure with all examples
    fig, axes = plt.subplots(n_train + n_test, 2, 
                             figsize=(8, 3 * (n_train + n_test)))
    
    if n_train + n_test == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle(f'Task {task_id}', fontsize=16, fontweight='bold')
    
    # Plot training examples
    for i, ex in enumerate(train_examples):
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        axes[i, 0].imshow(grid_in, cmap=cmap, vmin=0, vmax=9)
        axes[i, 0].set_title(f'Train {i+1} Input')
        axes[i, 0].axis('off')
        axes[i, 0].grid(True, which='both', color='white', linewidth=0.5)
        
        axes[i, 1].imshow(grid_out, cmap=cmap, vmin=0, vmax=9)
        axes[i, 1].set_title(f'Train {i+1} Output')
        axes[i, 1].axis('off')
        axes[i, 1].grid(True, which='both', color='white', linewidth=0.5)
    
    # Plot test examples
    for i, ex in enumerate(test_examples):
        grid_in = np.array(ex['input'])
        
        row_idx = n_train + i
        axes[row_idx, 0].imshow(grid_in, cmap=cmap, vmin=0, vmax=9)
        axes[row_idx, 0].set_title(f'Test {i+1} Input')
        axes[row_idx, 0].axis('off')
        axes[row_idx, 0].grid(True, which='both', color='white', linewidth=0.5)
        
        axes[row_idx, 1].text(0.5, 0.5, '?', 
                              ha='center', va='center',
                              fontsize=48, color='gray',
                              transform=axes[row_idx, 1].transAxes)
        axes[row_idx, 1].set_title(f'Test {i+1} Output (Unknown)')
        axes[row_idx, 1].axis('off')
    
    plt.tight_layout()
    
    # Save
    output_path = output_dir / f'{task_id}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path

def extract_transformation_rule(task_id, task_data):
    """Analyze task and extract transformation pattern"""
    train_examples = task_data['train']
    
    rules = []
    
    for i, ex in enumerate(train_examples):
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        # Basic statistics
        h_in, w_in = grid_in.shape
        h_out, w_out = grid_out.shape
        
        colors_in = set(int(x) for x in grid_in.flatten()) - {0}
        colors_out = set(int(x) for x in grid_out.flatten()) - {0}
        
        diff_mask = (grid_in != grid_out)
        n_changed = int(diff_mask.sum())
        
        is_identity = np.array_equal(grid_in, grid_out)
        
        rule = {
            'example': i + 1,
            'grid_shape_in': (h_in, w_in),
            'grid_shape_out': (h_out, w_out),
            'shape_preserved': (h_in == h_out and w_in == w_out),
            'colors_in': sorted(colors_in),
            'colors_out': sorted(colors_out),
            'n_pixels_changed': int(n_changed),
            'is_identity': bool(is_identity),
        }
        
        # Detect specific patterns
        if is_identity:
            rule['pattern'] = 'IDENTITY (output = input)'
        elif n_changed == 1:
            pos = np.argwhere(diff_mask)[0]
            old_val = grid_in[pos[0], pos[1]]
            new_val = grid_out[pos[0], pos[1]]
            rule['pattern'] = f'SINGLE_PIXEL_CHANGE at ({pos[0]},{pos[1]}): {old_val}→{new_val}'
        elif n_changed < 10:
            rule['pattern'] = f'MINIMAL_CHANGE ({n_changed} pixels)'
        else:
            rule['pattern'] = f'TRANSFORMATION ({n_changed} pixels changed)'
        
        rules.append(rule)
    
    return rules

def main():
    # Load tasks
    with open('arc-prize-2025/arc-agi_evaluation_challenges.json') as f:
        tasks = json.load(f)
    
    # The 14 high-confidence tasks
    high_conf_tasks = [
        '135a2760', '1ae2feb7', '22eb0ac0', '2dee498d',
        '48f8583b', '7b0280bc', '7df24a62', '8f3a5a89',
        'b6f77b65', 'baf41dbf', 'c8f0f002', 'da515329',
        'dfadab01', 'e3721c99'
    ]
    
    # Create output directory
    output_dir = Path('results/arc2025_visualizations')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations and rules
    all_rules = {}
    
    for task_id in high_conf_tasks:
        if task_id not in tasks:
            print(f'⚠ Task {task_id} not found')
            continue
        
        task_data = tasks[task_id]
        
        # Generate PNG
        png_path = visualize_task(task_id, task_data, output_dir)
        print(f'✓ Generated: {png_path}')
        
        # Extract rules
        rules = extract_transformation_rule(task_id, task_data)
        all_rules[task_id] = rules
    
    # Save rules to JSON
    rules_path = output_dir / 'transformation_rules.json'
    with open(rules_path, 'w') as f:
        json.dump(all_rules, f, indent=2)
    
    print(f'\n✓ Saved transformation rules: {rules_path}')
    
    # Generate summary report
    report_path = output_dir / 'TASK_RULES_SUMMARY.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('ARC-2025 High-Confidence Tasks: Transformation Rules\n')
        f.write('='*70 + '\n\n')
        
        for task_id in high_conf_tasks:
            if task_id not in all_rules:
                continue
            
            f.write(f'Task: {task_id}\n')
            f.write('-'*70 + '\n')
            
            for rule in all_rules[task_id]:
                f.write(f"  Example {rule['example']}:\n")
                f.write(f"    Grid: {rule['grid_shape_in']} → {rule['grid_shape_out']}\n")
                f.write(f"    Colors: {rule['colors_in']} → {rule['colors_out']}\n")
                f.write(f"    Changed: {rule['n_pixels_changed']} pixels\n")
                f.write(f"    Pattern: {rule['pattern']}\n")
                f.write('\n')
            
            f.write('\n')
    
    print(f'✓ Saved summary report: {report_path}')
    print(f'\n✓ All visualizations saved to: {output_dir}')
    print(f'  - 14 PNG images')
    print(f'  - transformation_rules.json')
    print(f'  - TASK_RULES_SUMMARY.txt')

if __name__ == '__main__':
    main()
