#!/usr/bin/env python3
"""Scan training set for COLOR-ENGINE Phase 2 patterns."""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_tasks():
    """Load training tasks."""
    train_path = Path("arc-prize-2024/arc-agi_training_challenges.json")
    with open(train_path) as f:
        return json.load(f)

def check_edge_pattern(input_grid, output_grid):
    """Check if output has edge recoloring."""
    if input_grid.shape != output_grid.shape:
        return False
    
    h, w = input_grid.shape
    edge_colors = set()
    interior_preserved = True
    
    for i in range(h):
        for j in range(w):
            is_edge = (i == 0 or i == h-1 or j == 0 or j == w-1)
            
            if is_edge:
                edge_colors.add(int(output_grid[i, j]))
            else:
                if int(output_grid[i, j]) != int(input_grid[i, j]):
                    interior_preserved = False
    
    return len(edge_colors) == 1 and interior_preserved

def check_border_frame(input_grid, output_grid):
    """Check if output has thick border frame."""
    if input_grid.shape != output_grid.shape:
        return False
    
    h, w = input_grid.shape
    
    for thickness in [2, 3]:
        if h <= 2*thickness or w <= 2*thickness:
            continue
        
        frame_colors = set()
        interior_preserved = True
        
        for i in range(h):
            for j in range(w):
                in_frame = (i < thickness or i >= h-thickness or 
                           j < thickness or j >= w-thickness)
                
                if in_frame:
                    frame_colors.add(int(output_grid[i, j]))
                else:
                    if int(output_grid[i, j]) != int(input_grid[i, j]):
                        interior_preserved = False
        
        if len(frame_colors) == 1 and interior_preserved:
            return True
    
    return False

def check_checkerboard(output_grid):
    """Check if output is checkerboard pattern."""
    h, w = output_grid.shape
    colors = [set(), set()]
    
    for i in range(h):
        for j in range(w):
            parity = (i + j) % 2
            colors[parity].add(int(output_grid[i, j]))
    
    return len(colors[0]) == 1 and len(colors[1]) == 1 and colors[0] != colors[1]

def check_modular(output_grid):
    """Check if output has modular row/col pattern."""
    h, w = output_grid.shape
    
    for modulus in [2, 3, 4]:
        # Check row modular
        row_colors = defaultdict(set)
        for i in range(h):
            mod_val = i % modulus
            for j in range(w):
                row_colors[mod_val].add(int(output_grid[i, j]))
        
        # Valid if each mod class has one color and they differ
        if all(len(colors) == 1 for colors in row_colors.values()):
            if len(set(next(iter(c)) for c in row_colors.values())) > 1:
                return True
        
        # Check col modular
        col_colors = defaultdict(set)
        for j in range(w):
            mod_val = j % modulus
            for i in range(h):
                col_colors[mod_val].add(int(output_grid[i, j]))
        
        if all(len(colors) == 1 for colors in col_colors.values()):
            if len(set(next(iter(c)) for c in col_colors.values())) > 1:
                return True
    
    return False

def check_structural(input_grid, output_grid):
    """Check if output has interior/perimeter recoloring."""
    if input_grid.shape != output_grid.shape:
        return False
    
    h, w = input_grid.shape
    mask = input_grid != 0
    
    interior_colors = set()
    perimeter_colors = set()
    
    for i in range(h):
        for j in range(w):
            if not mask[i, j]:
                continue
            
            # Check if perimeter
            is_perimeter = False
            for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                ni, nj = i+di, j+dj
                if ni < 0 or ni >= h or nj < 0 or nj >= w or not mask[ni, nj]:
                    is_perimeter = True
                    break
            
            if is_perimeter:
                perimeter_colors.add(int(output_grid[i, j]))
            else:
                interior_colors.add(int(output_grid[i, j]))
    
    return (len(interior_colors) == 1 and len(perimeter_colors) == 1 and 
            interior_colors != perimeter_colors)

def scan_tasks():
    """Scan all tasks for Phase 2 patterns."""
    tasks = load_tasks()
    
    pattern_counts = defaultdict(list)
    
    for task_id, task_data in tasks.items():
        # Check each training pair
        for idx, pair in enumerate(task_data['train']):
            input_grid = np.array(pair['input'])
            output_grid = np.array(pair['output'])
            
            if check_edge_pattern(input_grid, output_grid):
                pattern_counts['edge'].append((task_id, idx))
            
            if check_border_frame(input_grid, output_grid):
                pattern_counts['border_frame'].append((task_id, idx))
            
            if check_checkerboard(output_grid):
                pattern_counts['checkerboard'].append((task_id, idx))
            
            if check_modular(output_grid):
                pattern_counts['modular'].append((task_id, idx))
            
            if check_structural(input_grid, output_grid):
                pattern_counts['structural'].append((task_id, idx))
    
    # Print results
    print("\n=== COLOR-ENGINE PHASE 2 SCAN ===\n")
    
    for pattern, matches in sorted(pattern_counts.items()):
        unique_tasks = set(task_id for task_id, _ in matches)
        print(f"{pattern:20} {len(unique_tasks):3} unique tasks")
        
        # Show first 10 examples
        for task_id in sorted(unique_tasks)[:10]:
            print(f"  {task_id}")
        
        if len(unique_tasks) > 10:
            print(f"  ... and {len(unique_tasks) - 10} more")
        print()
    
    total_unique = len(set(
        task_id for matches in pattern_counts.values() 
        for task_id, _ in matches
    ))
    
    print(f"Total unique tasks with Phase 2 patterns: {total_unique}\n")

if __name__ == "__main__":
    scan_tasks()
