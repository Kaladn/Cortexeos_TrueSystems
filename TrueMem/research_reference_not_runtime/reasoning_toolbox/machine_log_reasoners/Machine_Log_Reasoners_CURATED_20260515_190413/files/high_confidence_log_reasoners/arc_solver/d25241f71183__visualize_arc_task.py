#!/usr/bin/env python3
"""Visualize ARC task with color mapping."""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
import sys

# ARC color palette
COLORS = {
    0: '#000000',  # black
    1: '#0074D9',  # blue
    2: '#FF4136',  # red
    3: '#2ECC40',  # green
    4: '#FFDC00',  # yellow
    5: '#AAAAAA',  # gray
    6: '#F012BE',  # magenta
    7: '#FF851B',  # orange
    8: '#7FDBFF',  # light blue
    9: '#870C25',  # dark red
}

def load_task(task_id, dataset='evaluation'):
    """Load task from dataset."""
    if dataset == 'evaluation':
        path = Path("arc-prize-2024/arc-agi_evaluation_challenges.json")
    else:
        path = Path("arc-prize-2024/arc-agi_training_challenges.json")
    
    with open(path) as f:
        tasks = json.load(f)
    
    return tasks[task_id]

def plot_grid(ax, grid, title=""):
    """Plot a single grid."""
    grid = np.array(grid)
    h, w = grid.shape
    
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=10, fontweight='bold')
    
    # Draw cells
    for i in range(h):
        for j in range(w):
            color_val = int(grid[i, j])
            color = COLORS.get(color_val, '#FFFFFF')
            
            rect = Rectangle((j, h-1-i), 1, 1, 
                           facecolor=color, 
                           edgecolor='#DDDDDD', 
                           linewidth=0.5)
            ax.add_patch(rect)
    
    # Grid lines
    for i in range(h + 1):
        ax.axhline(i, color='#DDDDDD', linewidth=0.5)
    for j in range(w + 1):
        ax.axvline(j, color='#DDDDDD', linewidth=0.5)

def visualize_task(task_id, dataset='evaluation', save_path=None):
    """Visualize full task with training and test examples."""
    task = load_task(task_id, dataset)
    
    n_train = len(task['train'])
    n_test = len(task['test'])
    
    # Create figure
    fig = plt.figure(figsize=(14, 3 * (n_train + n_test)))
    
    # Training examples
    for idx, pair in enumerate(task['train']):
        # Input
        ax_in = plt.subplot(n_train + n_test, 2, 2*idx + 1)
        plot_grid(ax_in, pair['input'], f"Train {idx+1} Input")
        
        # Output
        ax_out = plt.subplot(n_train + n_test, 2, 2*idx + 2)
        plot_grid(ax_out, pair['output'], f"Train {idx+1} Output")
    
    # Test examples
    for idx, test_case in enumerate(task['test']):
        ax_test = plt.subplot(n_train + n_test, 2, 2*(n_train + idx) + 1)
        plot_grid(ax_test, test_case['input'], f"Test {idx+1} Input")
        
        # Leave output blank (to be predicted)
        ax_blank = plt.subplot(n_train + n_test, 2, 2*(n_train + idx) + 2)
        ax_blank.text(0.5, 0.5, '?', 
                     ha='center', va='center', 
                     fontsize=50, color='#CCCCCC')
        ax_blank.set_xlim(0, 1)
        ax_blank.set_ylim(0, 1)
        ax_blank.axis('off')
        ax_blank.set_title(f"Test {idx+1} Output (Predict)", fontsize=10, fontweight='bold')
    
    plt.suptitle(f"Task {task_id} ({dataset.upper()})", 
                fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved to: {save_path}")
    else:
        plt.show()
    
    return fig

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_arc_task.py TASK_ID [--dataset train|evaluation]")
        sys.exit(1)
    
    task_id = sys.argv[1]
    dataset = 'evaluation'
    
    if '--dataset' in sys.argv:
        idx = sys.argv.index('--dataset')
        if idx + 1 < len(sys.argv):
            dataset = sys.argv[idx + 1]
    
    output_file = f"visualizations/task_{task_id}_{dataset}.png"
    Path("visualizations").mkdir(exist_ok=True)
    
    visualize_task(task_id, dataset, save_path=output_file)
    print(f"\n✓ Task {task_id} visualized")
