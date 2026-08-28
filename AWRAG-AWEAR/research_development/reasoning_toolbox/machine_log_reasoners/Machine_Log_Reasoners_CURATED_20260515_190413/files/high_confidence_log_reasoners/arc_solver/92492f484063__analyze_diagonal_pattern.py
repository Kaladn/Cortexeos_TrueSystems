"""Rotate inputs to align diagonal patterns vertically and analyze."""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy.ndimage import rotate

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

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
    '#7FDBFF',  # 8: cyan
    '#870C25',  # 9: maroon
]

def plot_grid(grid, title, ax):
    """Plot a grid with ARC colors."""
    cmap = ListedColormap(ARC_COLORS)
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=9)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.grid(True, which='both', color='white', linewidth=0.5)
    ax.set_xticks(np.arange(-0.5, grid.shape[1], 1))
    ax.set_yticks(np.arange(-0.5, grid.shape[0], 1))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(length=0)

def analyze_diagonal_direction(inp):
    """Find the direction of the diagonal pattern."""
    H, W = inp.shape
    non_zero_positions = []
    
    for r in range(H):
        for c in range(W):
            if inp[r, c] != 0:
                non_zero_positions.append((r, c))
    
    if len(non_zero_positions) < 2:
        return None, non_zero_positions
    
    # Calculate average slope
    positions = np.array(non_zero_positions)
    if len(positions) > 1:
        # Fit a line through the points
        r_coords = positions[:, 0]
        c_coords = positions[:, 1]
        
        # Calculate slope
        if np.std(c_coords) > 0.1:
            slope = np.polyfit(c_coords, r_coords, 1)[0]
        else:
            slope = np.inf
        
        return slope, non_zero_positions
    
    return None, non_zero_positions

def extract_diagonal_colors(inp):
    """Extract colors along the diagonal in order."""
    H, W = inp.shape
    
    # Find all non-zero positions
    non_zero = []
    for r in range(H):
        for c in range(W):
            if inp[r, c] != 0:
                non_zero.append((r, c, inp[r, c]))
    
    if not non_zero:
        return []
    
    # Sort by position (try different orderings)
    # Try top-left to bottom-right: sort by (r+c)
    sorted_by_sum = sorted(non_zero, key=lambda x: (x[0] + x[1], x[0]))
    
    # Try top-right to bottom-left: sort by (r-c)
    sorted_by_diff = sorted(non_zero, key=lambda x: (x[0] - x[1], x[0]))
    
    return {
        'by_sum': [c for r, col, c in sorted_by_sum],
        'by_diff': [c for r, col, c in sorted_by_diff],
        'positions': [(r, col) for r, col, c in sorted_by_sum]
    }

print("="*80)
print("DIAGONAL PATTERN ANALYSIS - Task 05269061")
print("="*80)

examples = [
    ("Train 1", np.array(task['train'][0]['input']), np.array(task['train'][0]['output'])),
    ("Train 2", np.array(task['train'][1]['input']), np.array(task['train'][1]['output'])),
    ("Train 3", np.array(task['train'][2]['input']), np.array(task['train'][2]['output'])),
    ("Test", np.array(task['test'][0]['input']), np.array(solutions['05269061'][0])),
]

# Create visualization
fig, axes = plt.subplots(4, 3, figsize=(12, 14))

findings = []

for idx, (label, inp, out) in enumerate(examples):
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"{'='*80}")
    
    # Analyze diagonal
    slope, positions = analyze_diagonal_direction(inp)
    diagonal_info = extract_diagonal_colors(inp)
    
    print(f"Non-zero positions: {positions}")
    print(f"Diagonal slope: {slope}")
    print(f"\nColors sorted by (r+c) [top-left to bottom-right]: {diagonal_info['by_sum']}")
    print(f"Colors sorted by (r-c) [top-right to bottom-left]: {diagonal_info['by_diff']}")
    
    # Get the 3x3 output pattern
    pattern = out[:3, :3]
    first_row = [int(pattern[0, 0]), int(pattern[0, 1]), int(pattern[0, 2])]
    print(f"\nOutput 3x3 pattern first row: {first_row}")
    
    # Check which ordering matches
    if diagonal_info['by_sum'] == first_row:
        print(f"✅ MATCH: Diagonal (r+c order) matches output pattern!")
        match_type = "r+c (↘)"
    elif diagonal_info['by_diff'] == first_row:
        print(f"✅ MATCH: Diagonal (r-c order) matches output pattern!")
        match_type = "r-c (↙)"
    elif list(reversed(diagonal_info['by_sum'])) == first_row:
        print(f"✅ MATCH: Reversed diagonal (r+c) matches output pattern!")
        match_type = "reversed r+c (↖)"
    elif list(reversed(diagonal_info['by_diff'])) == first_row:
        print(f"✅ MATCH: Reversed diagonal (r-c) matches output pattern!")
        match_type = "reversed r-c (↗)"
    else:
        print(f"❌ NO DIRECT MATCH")
        match_type = "unknown"
    
    findings.append({
        'label': label,
        'diagonal_sum': diagonal_info['by_sum'],
        'diagonal_diff': diagonal_info['by_diff'],
        'output_pattern': first_row,
        'match_type': match_type
    })
    
    # Plot original
    plot_grid(inp, f'{label} - Original Input', axes[idx, 0])
    
    # Plot with annotations
    ax = axes[idx, 1]
    plot_grid(inp, f'{label} - With Order', ax)
    for i, (r, c) in enumerate(diagonal_info['positions'][:3]):
        color = inp[r, c]
        ax.text(c, r, str(i+1), ha='center', va='center', 
               color='white', fontsize=14, fontweight='bold',
               bbox=dict(boxstyle='circle', facecolor='black', alpha=0.7))
    
    # Plot output pattern
    plot_grid(pattern, f'{label} - Output 3x3', axes[idx, 2])
    for r in range(3):
        for c in range(3):
            val = int(pattern[r, c])
            axes[idx, 2].text(c, r, str(val), ha='center', va='center',
                            color='white', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig('diagonal_analysis.png', dpi=150, bbox_inches='tight')
print(f"\n{'='*80}")
print("✅ Saved: diagonal_analysis.png")
print(f"{'='*80}")

# Summary
print(f"\n{'='*80}")
print("FINDINGS SUMMARY")
print(f"{'='*80}")
for f in findings:
    print(f"\n{f['label']}:")
    print(f"  Diagonal (r+c): {f['diagonal_sum']}")
    print(f"  Diagonal (r-c): {f['diagonal_diff']}")
    print(f"  Output pattern: {f['output_pattern']}")
    print(f"  Match type: {f['match_type']}")

print(f"\n{'='*80}")
print("KEY INSIGHT:")
print(f"{'='*80}")
print("If the diagonal ordering determines the output pattern,")
print("we need to identify WHICH diagonal direction and read order.")
