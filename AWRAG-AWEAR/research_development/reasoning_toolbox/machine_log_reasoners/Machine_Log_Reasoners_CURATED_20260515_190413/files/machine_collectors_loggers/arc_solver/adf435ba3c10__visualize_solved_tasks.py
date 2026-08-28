"""Generate PNG visualizations of all 18 solved tasks"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import os

# ARC color palette (standard 10 colors)
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
    '#870C25',  # 9: brown
]

cmap = ListedColormap(ARC_COLORS)

# Load dataset
data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))

# All 18 solved tasks
solved_tasks = [
    '007bbfb7', '332efdb3', '3befdf3e', '496994bd', '5582e5ca', '5b6cbef5',
    '60c09cac', '67a3c6ac', '68b16354', '9172f3a0', 'a416b8f3', 'ac0a08a4',
    'b1948b0a', 'c59eb873', 'c8f0f002', 'd511f180', 'd5d6de2d', 'f25ffba3'
]

# Operator names for each task
task_operators = {
    '007bbfb7': 'self_masking_tiling',
    '332efdb3': 'position_based_recolor',
    '3befdf3e': 'center_halo_expansion',
    '496994bd': 'symmetry_completion',
    '5582e5ca': 'color_histogram_fill',
    '5b6cbef5': 'self_masking_tiling',
    '60c09cac': 'block_expansion',
    '67a3c6ac': 'mirror',
    '68b16354': 'mirror',
    '9172f3a0': 'block_expansion',
    'a416b8f3': 'horizontal_replicate',
    'ac0a08a4': 'block_expansion',
    'b1948b0a': 'recolor_mapping',
    'c59eb873': 'block_expansion',
    'c8f0f002': 'recolor_mapping',
    'd511f180': 'swap_mapping',
    'd5d6de2d': 'hollow_frame_extraction',
    'f25ffba3': 'symmetry_completion',
}

# Create output directory
os.makedirs('solved_task_visualizations', exist_ok=True)

for task_id in solved_tasks:
    task = data[task_id]
    operator = task_operators[task_id]
    
    num_examples = len(task['train'])
    
    # Create figure with subplots for each example (input and output side by side)
    fig, axes = plt.subplots(num_examples, 2, figsize=(8, 4 * num_examples))
    
    # Handle single example case
    if num_examples == 1:
        axes = [axes]
    
    fig.suptitle(f'Task {task_id} - {operator}', fontsize=16, fontweight='bold')
    
    for i, example in enumerate(task['train']):
        inp = np.array(example['input'])
        out = np.array(example['output'])
        
        # Input
        ax_in = axes[i][0] if num_examples > 1 else axes[0]
        ax_in.imshow(inp, cmap=cmap, vmin=0, vmax=9)
        ax_in.set_title(f'Example {i+1} - Input ({inp.shape[0]}×{inp.shape[1]})')
        ax_in.grid(True, which='both', color='white', linewidth=0.5, alpha=0.3)
        ax_in.set_xticks(np.arange(-0.5, inp.shape[1], 1), minor=True)
        ax_in.set_yticks(np.arange(-0.5, inp.shape[0], 1), minor=True)
        ax_in.set_xticks([])
        ax_in.set_yticks([])
        
        # Output
        ax_out = axes[i][1] if num_examples > 1 else axes[1]
        ax_out.imshow(out, cmap=cmap, vmin=0, vmax=9)
        ax_out.set_title(f'Example {i+1} - Output ({out.shape[0]}×{out.shape[1]})')
        ax_out.grid(True, which='both', color='white', linewidth=0.5, alpha=0.3)
        ax_out.set_xticks(np.arange(-0.5, out.shape[1], 1), minor=True)
        ax_out.set_yticks(np.arange(-0.5, out.shape[0], 1), minor=True)
        ax_out.set_xticks([])
        ax_out.set_yticks([])
    
    plt.tight_layout()
    
    # Save with operator name in filename
    filename = f'solved_task_visualizations/{task_id}_{operator}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Saved {task_id} ({operator})')

print(f'\n✅ Generated {len(solved_tasks)} visualization PNGs in solved_task_visualizations/')
