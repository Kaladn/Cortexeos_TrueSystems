#!/usr/bin/env python3
"""Analyze the 20 position_based_recolor tasks to categorize pattern types."""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict

def load_task(task_id):
    """Load a specific task."""
    train_path = Path("arc-prize-2024/arc-agi_training_challenges.json")
    with open(train_path) as f:
        tasks = json.load(f)
    return tasks[task_id]

def analyze_periodicity(grid):
    """Detect if grid has periodic tiling pattern."""
    h, w = grid.shape
    
    # Try small periods
    for period_h in [1, 2, 3, 4]:
        for period_w in [1, 2, 3, 4]:
            if period_h == 1 and period_w == 1:
                continue
            
            is_periodic = True
            for i in range(h):
                for j in range(w):
                    if grid[i, j] != grid[i % period_h, j % period_w]:
                        is_periodic = False
                        break
                if not is_periodic:
                    break
            
            if is_periodic:
                return f"tiling_{period_h}x{period_w}"
    
    return None

def analyze_row_col_pattern(grid):
    """Check for row-based or column-based patterns."""
    h, w = grid.shape
    
    # Check if all rows have uniform color
    row_uniform = True
    for i in range(h):
        if len(set(grid[i, :])) > 1:
            row_uniform = False
            break
    
    if row_uniform:
        return "row_uniform"
    
    # Check if all columns have uniform color
    col_uniform = True
    for j in range(w):
        if len(set(grid[:, j])) > 1:
            col_uniform = False
            break
    
    if col_uniform:
        return "col_uniform"
    
    # Check for modular row pattern (row % N)
    for modulus in [2, 3, 4]:
        row_mod_colors = defaultdict(set)
        for i in range(h):
            mod_val = i % modulus
            row_mod_colors[mod_val].update(grid[i, :])
        
        # Check if each mod class has one consistent color
        if all(len(colors) == 1 for colors in row_mod_colors.values()):
            return f"row_mod{modulus}"
    
    # Check for modular column pattern (col % N)
    for modulus in [2, 3, 4]:
        col_mod_colors = defaultdict(set)
        for j in range(w):
            mod_val = j % modulus
            col_mod_colors[mod_val].update(grid[:, j])
        
        if all(len(colors) == 1 for colors in col_mod_colors.values()):
            return f"col_mod{modulus}"
    
    return None

def analyze_diagonal_pattern(grid):
    """Check for diagonal-based patterns."""
    h, w = grid.shape
    
    # Check (i+j) % N patterns
    for modulus in [2, 3, 4]:
        diag_colors = defaultdict(set)
        for i in range(h):
            for j in range(w):
                mod_val = (i + j) % modulus
                diag_colors[mod_val].add(int(grid[i, j]))
        
        if all(len(colors) == 1 for colors in diag_colors.values()):
            return f"diagonal_mod{modulus}"
    
    return None

def analyze_edge_pattern(grid):
    """Check for edge/border patterns."""
    h, w = grid.shape
    
    # Check 1-pixel edge
    edge_colors = set()
    interior_colors = set()
    
    for i in range(h):
        for j in range(w):
            is_edge = (i == 0 or i == h-1 or j == 0 or j == w-1)
            if is_edge:
                edge_colors.add(int(grid[i, j]))
            else:
                interior_colors.add(int(grid[i, j]))
    
    if len(edge_colors) == 1:
        return "edge_1px"
    
    # Check 2-pixel border
    for thickness in [2, 3]:
        if h <= 2*thickness or w <= 2*thickness:
            continue
        
        border_colors = set()
        interior_colors = set()
        
        for i in range(h):
            for j in range(w):
                in_border = (i < thickness or i >= h-thickness or 
                           j < thickness or j >= w-thickness)
                if in_border:
                    border_colors.add(int(grid[i, j]))
                else:
                    interior_colors.add(int(grid[i, j]))
        
        if len(border_colors) == 1:
            return f"border_{thickness}px"
    
    return None

def categorize_task(task_id):
    """Categorize a single task's pattern type."""
    task = load_task(task_id)
    
    patterns = []
    
    for pair in task['train']:
        output = np.array(pair['output'])
        
        # Try different pattern detections
        tiling = analyze_periodicity(output)
        if tiling:
            patterns.append(tiling)
            continue
        
        diagonal = analyze_diagonal_pattern(output)
        if diagonal:
            patterns.append(diagonal)
            continue
        
        row_col = analyze_row_col_pattern(output)
        if row_col:
            patterns.append(row_col)
            continue
        
        edge = analyze_edge_pattern(output)
        if edge:
            patterns.append(edge)
            continue
        
        patterns.append("complex")
    
    # Return most common pattern
    if patterns:
        counter = Counter(patterns)
        return counter.most_common(1)[0][0]
    
    return "unknown"

def main():
    """Analyze all position_based_recolor tasks."""
    
    # These are the 20 tasks solved by baseline's position_based_recolor
    # (identified from your diagnostic tool)
    position_tasks = [
        "05269061", "0d3d703e", "25d8a9c8", "25ff71a9", "3bd67248",
        "4347f46a", "444801d8", "4be741c5", "5582e5ca", "6e02f1e3",
        "746b3537", "794b24be", "8e1813be", "9565186b", "995c5fa3",
        "a8d7556c", "bb43febb", "c9e6f938", "d0f5fe59", "ea786f4a"
    ]
    
    print("\n=== POSITION_BASED_RECOLOR PATTERN ANALYSIS ===\n")
    
    categories = defaultdict(list)
    
    for task_id in position_tasks:
        try:
            pattern_type = categorize_task(task_id)
            categories[pattern_type].append(task_id)
            print(f"{task_id}: {pattern_type}")
        except Exception as e:
            print(f"{task_id}: ERROR - {e}")
            categories["error"].append(task_id)
    
    print("\n=== PATTERN BREAKDOWN ===\n")
    
    for pattern, tasks in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{pattern:20} {len(tasks):2} tasks")
        for task_id in tasks[:5]:
            print(f"  {task_id}")
        if len(tasks) > 5:
            print(f"  ... and {len(tasks)-5} more")
        print()
    
    print("\n=== IMPLEMENTATION STRATEGY ===\n")
    
    # Count by category
    tiling_count = sum(len(tasks) for pattern, tasks in categories.items() 
                      if pattern.startswith('tiling_'))
    diagonal_count = sum(len(tasks) for pattern, tasks in categories.items() 
                        if pattern.startswith('diagonal_'))
    row_col_count = sum(len(tasks) for pattern, tasks in categories.items() 
                       if pattern in ['row_uniform', 'col_uniform', 'row_mod2', 'row_mod3', 'col_mod2', 'col_mod3'])
    edge_count = sum(len(tasks) for pattern, tasks in categories.items() 
                    if pattern.startswith('edge_') or pattern.startswith('border_'))
    
    print(f"Tiling patterns (PATTERN-ENGINE):    {tiling_count}")
    print(f"Diagonal patterns (PATTERN-ENGINE):  {diagonal_count}")
    print(f"Row/col patterns (COLOR-ENGINE):     {row_col_count}")
    print(f"Edge/border patterns (COLOR-ENGINE): {edge_count}")
    print(f"Complex patterns (needs analysis):   {len(categories.get('complex', []))}")
    print()
    
    print("RECOMMENDATION:")
    print("1. Expand PATTERN-ENGINE to detect tiling and diagonal patterns")
    print("2. COLOR-ENGINE Phase 2 already handles row/col and edge/border")
    print("3. Build PATTERN_COLOR_ENGINE to combine pattern detection + recoloring")
    print()

if __name__ == "__main__":
    main()
