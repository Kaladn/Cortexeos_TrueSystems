"""
Visualize spatial reasoning task with PNG outputs
Analyze potential volumetric/3D structure
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

# ARC color palette
ARC_COLORS = [
    '#000000',  # 0: black (background)
    '#0074D9',  # 1: blue
    '#FF4136',  # 2: red
    '#2ECC40',  # 3: green
    '#FFDC00',  # 4: yellow
    '#AAAAAA',  # 5: gray
    '#F012BE',  # 6: magenta
    '#FF851B',  # 7: orange
    '#7FDBFF',  # 8: cyan
    '#870C25',  # 9: maroon
]

cmap = ListedColormap(ARC_COLORS)

def visualize_example(inp, out, example_num, task_id):
    """Create side-by-side visualization of input and output"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
    
    # Input
    ax1.imshow(inp, cmap=cmap, vmin=0, vmax=9)
    ax1.set_title(f'Input ({inp.shape[0]}×{inp.shape[1]})', fontsize=14, fontweight='bold')
    ax1.grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    ax1.set_xticks(np.arange(-0.5, inp.shape[1], 1))
    ax1.set_yticks(np.arange(-0.5, inp.shape[0], 1))
    ax1.tick_params(labelbottom=False, labelleft=False)
    
    # Output
    ax2.imshow(out, cmap=cmap, vmin=0, vmax=9)
    ax2.set_title(f'Output ({out.shape[0]}×{out.shape[1]})', fontsize=14, fontweight='bold')
    ax2.grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    ax2.set_xticks(np.arange(-0.5, out.shape[1], 1))
    ax2.set_yticks(np.arange(-0.5, out.shape[0], 1))
    ax2.tick_params(labelbottom=False, labelleft=False)
    
    plt.suptitle(f'Task {task_id} - Example {example_num}', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{task_id}_example_{example_num}.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {task_id}_example_{example_num}.png")
    plt.close()


def visualize_objects(inp, out, example_num, task_id):
    """Visualize with object detection overlay"""
    from scipy import ndimage
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 16))
    
    # Input
    axes[0, 0].imshow(inp, cmap=cmap, vmin=0, vmax=9)
    axes[0, 0].set_title(f'Input ({inp.shape[0]}×{inp.shape[1]})', fontsize=12, fontweight='bold')
    axes[0, 0].grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    
    # Input with object bounding boxes
    axes[0, 1].imshow(inp, cmap=cmap, vmin=0, vmax=9)
    axes[0, 1].set_title('Input - Objects Detected', fontsize=12, fontweight='bold')
    axes[0, 1].grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    
    # Detect objects
    colors = set(inp.flatten()) - {0}
    for color in colors:
        mask = (inp == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            if len(positions) > 0:
                min_row, min_col = positions.min(axis=0)
                max_row, max_col = positions.max(axis=0)
                center_row, center_col = positions.mean(axis=0)
                
                # Draw bounding box
                rect = mpatches.Rectangle((min_col-0.5, min_row-0.5), 
                                         max_col-min_col+1, max_row-min_row+1,
                                         linewidth=2, edgecolor='white', facecolor='none')
                axes[0, 1].add_patch(rect)
                
                # Draw center point
                axes[0, 1].plot(center_col, center_row, 'w*', markersize=10)
    
    # Output
    axes[1, 0].imshow(out, cmap=cmap, vmin=0, vmax=9)
    axes[1, 0].set_title(f'Output ({out.shape[0]}×{out.shape[1]})', fontsize=12, fontweight='bold')
    axes[1, 0].grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    
    # Output with object bounding boxes
    axes[1, 1].imshow(out, cmap=cmap, vmin=0, vmax=9)
    axes[1, 1].set_title('Output - Objects Detected', fontsize=12, fontweight='bold')
    axes[1, 1].grid(True, which='both', color='gray', linewidth=0.5, alpha=0.3)
    
    # Detect objects in output
    colors = set(out.flatten()) - {0}
    for color in colors:
        mask = (out == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            if len(positions) > 0:
                min_row, min_col = positions.min(axis=0)
                max_row, max_col = positions.max(axis=0)
                center_row, center_col = positions.mean(axis=0)
                
                # Draw bounding box
                rect = mpatches.Rectangle((min_col-0.5, min_row-0.5), 
                                         max_col-min_col+1, max_row-min_row+1,
                                         linewidth=2, edgecolor='white', facecolor='none')
                axes[1, 1].add_patch(rect)
                
                # Draw center point
                axes[1, 1].plot(center_col, center_row, 'w*', markersize=10)
    
    plt.suptitle(f'Task {task_id} - Example {example_num} - Object Analysis', 
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{task_id}_example_{example_num}_objects.png', dpi=150, bbox_inches='tight')
    print(f"Saved: {task_id}_example_{example_num}_objects.png")
    plt.close()


def analyze_transformation(inp, out, example_num):
    """Analyze the transformation numerically"""
    from scipy import ndimage
    
    print(f"\n{'='*60}")
    print(f"EXAMPLE {example_num} ANALYSIS")
    print(f"{'='*60}")
    
    H_in, W_in = inp.shape
    H_out, W_out = out.shape
    
    print(f"\nGrid dimensions:")
    print(f"  Input:  {H_in}×{W_in}")
    print(f"  Output: {H_out}×{W_out}")
    
    # Extract objects from input
    print(f"\nInput objects:")
    colors_in = set(inp.flatten()) - {0}
    objects_in = []
    
    for color in sorted(colors_in):
        mask = (inp == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            if len(positions) > 0:
                min_row, min_col = positions.min(axis=0)
                max_row, max_col = positions.max(axis=0)
                center_row, center_col = positions.mean(axis=0)
                
                obj = {
                    'color': color,
                    'size': len(positions),
                    'bbox': (min_row, min_col, max_row, max_col),
                    'center': (center_row, center_col)
                }
                objects_in.append(obj)
                
                print(f"  Color {color}: center=({center_row:.1f}, {center_col:.1f}), "
                      f"size={len(positions)}, bbox={min_row},{min_col} to {max_row},{max_col}")
    
    # Extract objects from output
    print(f"\nOutput objects:")
    colors_out = set(out.flatten()) - {0}
    objects_out = []
    
    for color in sorted(colors_out):
        mask = (out == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            if len(positions) > 0:
                min_row, min_col = positions.min(axis=0)
                max_row, max_col = positions.max(axis=0)
                center_row, center_col = positions.mean(axis=0)
                
                obj = {
                    'color': color,
                    'size': len(positions),
                    'bbox': (min_row, min_col, max_row, max_col),
                    'center': (center_row, center_col)
                }
                objects_out.append(obj)
                
                print(f"  Color {color}: center=({center_row:.1f}, {center_col:.1f}), "
                      f"size={len(positions)}, bbox={min_row},{min_col} to {max_row},{max_col}")
    
    # Analyze spatial distribution
    print(f"\nSpatial analysis:")
    
    midpoint = H_in // 2
    upper_in = [o for o in objects_in if o['center'][0] < midpoint]
    lower_in = [o for o in objects_in if o['center'][0] >= midpoint]
    
    upper_out = [o for o in objects_out if o['center'][0] < midpoint]
    lower_out = [o for o in objects_out if o['center'][0] >= midpoint]
    
    print(f"  Midpoint: row {midpoint}")
    print(f"  Input:  {len(upper_in)} objects in upper half, {len(lower_in)} in lower half")
    print(f"  Output: {len(upper_out)} objects in upper half, {len(lower_out)} in lower half")
    
    # Check for empty middle zone
    if H_out >= 5:
        middle_start = H_out // 2 - 2
        middle_end = H_out // 2 + 3
        middle_zone = out[middle_start:middle_end, :]
        if np.all(middle_zone == 0):
            print(f"  ✓ Empty zone detected: rows {middle_start} to {middle_end-1}")
        else:
            print(f"  No empty middle zone")


if __name__ == "__main__":
    # Load task
    with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
        data = json.load(f)
    
    task_id = 'ac2e8ecf'
    task = data[task_id]
    
    print(f"\n{'='*80}")
    print(f"VISUALIZING SPATIAL REASONING TASK: {task_id}")
    print(f"{'='*80}")
    
    for i, ex in enumerate(task['train'], 1):
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        
        # Create visualizations
        visualize_example(inp, out, i, task_id)
        visualize_objects(inp, out, i, task_id)
        
        # Numerical analysis
        analyze_transformation(inp, out, i)
    
    print(f"\n{'='*80}")
    print(f"VISUALIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"\nCreated {len(task['train']) * 2} PNG files:")
    for i in range(1, len(task['train']) + 1):
        print(f"  - {task_id}_example_{i}.png")
        print(f"  - {task_id}_example_{i}_objects.png")
    
    print(f"\nPATTERN HYPOTHESIS:")
    print(f"  Objects in upper half → compact at TOP")
    print(f"  Objects in lower half → compact at BOTTOM")
    print(f"  Middle region → EMPTY")
    print(f"  This is GRAVITY SORTING with hemisphere separation")
