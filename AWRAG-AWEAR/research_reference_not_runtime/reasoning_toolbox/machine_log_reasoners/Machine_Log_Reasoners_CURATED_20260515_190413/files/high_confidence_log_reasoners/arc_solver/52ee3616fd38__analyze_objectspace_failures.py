"""
Analyze why ObjectSpace transforms aren't matching.

Diagnose the 393 "No transform matched" failures to identify patterns.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from collections import defaultdict
from arc_organ.object_space import detect_objects, build_object_space
from arc_organ.transform_library import TRANSFORM_LIBRARY


def analyze_failed_task(task_id: str, task_data: dict) -> dict:
    """Analyze why a task failed to find a transform."""
    analysis = {
        'task_id': task_id,
        'num_train': len(task_data['train']),
        'input_shape': None,
        'output_shape': None,
        'input_objects': 0,
        'output_objects': 0,
        'shape_changed': False,
        'object_count_changed': False,
        'transform_attempts': []
    }
    
    try:
        ex = task_data['train'][0]
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        analysis['input_shape'] = grid_in.shape
        analysis['output_shape'] = grid_out.shape
        analysis['shape_changed'] = grid_in.shape != grid_out.shape
        
        objects_in = detect_objects(grid_in)
        objects_out = detect_objects(grid_out)
        
        analysis['input_objects'] = len(objects_in)
        analysis['output_objects'] = len(objects_out)
        analysis['object_count_changed'] = len(objects_in) != len(objects_out)
        
        if objects_in and objects_out:
            os_in = build_object_space(objects_in, *grid_in.shape)
            os_out = build_object_space(objects_out, *grid_out.shape)
            
            # Check each transform
            for transform in TRANSFORM_LIBRARY:
                matches = transform.matches(os_in, os_out)
                analysis['transform_attempts'].append({
                    'name': transform.name,
                    'matches': matches
                })
    
    except Exception as e:
        analysis['error'] = str(e)
    
    return analysis


def run_failure_analysis():
    """Analyze all failed tasks."""
    print("\n" + "="*80)
    print(" FAILURE ANALYSIS: Why Transforms Don't Match")
    print("="*80)
    
    # Load results
    with open('results/objectspace_evaluation_results.json', 'r') as f:
        results = json.load(f)
    
    failed_tasks = [r for r in results['detailed_results'] 
                    if r['error'] == 'No transform matched']
    
    print(f"\nAnalyzing {len(failed_tasks)} failed tasks...")
    
    # Sample analysis (first 20 tasks)
    sample_size = 20
    print(f"\nDetailed analysis of first {sample_size} tasks:\n")
    
    tasks = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
    
    shape_changed = 0
    object_count_changed = 0
    
    for i, failed in enumerate(failed_tasks[:sample_size]):
        task_id = failed['task_id']
        task_data = tasks[task_id]
        
        analysis = analyze_failed_task(task_id, task_data)
        
        print(f"{i+1}. {task_id}")
        print(f"   Input: {analysis['input_shape']}, {analysis['input_objects']} objects")
        print(f"   Output: {analysis['output_shape']}, {analysis['output_objects']} objects")
        
        if analysis['shape_changed']:
            print(f"   ⚠ Grid shape changed")
            shape_changed += 1
        
        if analysis['object_count_changed']:
            print(f"   ⚠ Object count changed")
            object_count_changed += 1
        
        # Show which transforms were close
        near_misses = [t for t in analysis.get('transform_attempts', []) 
                       if t['matches']]
        if near_misses:
            print(f"   Near misses: {', '.join(t['name'] for t in near_misses)}")
        
        print()
    
    # Overall statistics
    print("\n" + "="*80)
    print(" FAILURE PATTERNS")
    print("="*80)
    
    print(f"\nIn sample of {sample_size} failed tasks:")
    print(f"  Grid shape changed: {shape_changed} ({100*shape_changed/sample_size:.0f}%)")
    print(f"  Object count changed: {object_count_changed} ({100*object_count_changed/sample_size:.0f}%)")
    
    print("\n" + "="*80)
    print(" KEY INSIGHTS")
    print("="*80)
    
    print("""
Current transform library limitations:

1. SHAPE CHANGES: {shape_changed}/{sample_size} tasks change grid dimensions
   - Current transforms preserve grid shape
   - Need: crop, pad, resize transforms

2. OBJECT COUNT CHANGES: {object_count_changed}/{sample_size} tasks change object count
   - Current transforms preserve object count (1-to-1 mapping)
   - Need: split, merge, duplicate, delete transforms

3. MISSING TRANSFORM TYPES:
   - Color changes (recolor objects)
   - Spatial operations (stack, align, distribute)
   - Conditional transforms (if-then rules)
   - Multi-step compositions

4. MATCHING TOO STRICT:
   - Small tolerance issues (floating point precision)
   - Need fuzzy matching for approximate transforms
   - Consider partial matches (some objects transform, others don't)

RECOMMENDATION: Expand transform library with:
- Grid resize/crop/pad
- Object duplication/deletion
- Color transforms
- Relaxed matching criteria
""".format(shape_changed=shape_changed, sample_size=sample_size, 
           object_count_changed=object_count_changed))


if __name__ == "__main__":
    run_failure_analysis()
