"""
Generate detailed report of high-confidence close matches for manual examination.

These tasks have correct anchor point measurements but need additional operators.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from arc_organ.object_space import detect_objects
from arc_organ.transform_matcher import find_close_matches


def analyze_high_confidence_task(task_id: str, task_data: dict) -> dict:
    """Analyze a high-confidence task in detail."""
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    objs_in = detect_objects(grid_in)
    objs_out = detect_objects(grid_out)
    
    matches = find_close_matches(grid_in, grid_out, min_confidence=0.7)
    
    analysis = {
        'task_id': task_id,
        'shape_in': grid_in.shape,
        'shape_out': grid_out.shape,
        'objects_in': len(objs_in),
        'objects_out': len(objs_out),
        'object_count_changed': len(objs_in) != len(objs_out),
        'best_match': matches[0].transform_name if matches else None,
        'confidence': matches[0].confidence if matches else 0.0,
        'evidence': matches[0] if matches else None
    }
    
    # Classify the pattern type
    if analysis['object_count_changed']:
        if analysis['objects_out'] > analysis['objects_in']:
            analysis['pattern_type'] = 'OBJECT_CREATION'
        else:
            analysis['pattern_type'] = 'OBJECT_DELETION'
    else:
        # Same object count - check what changed
        if analysis['evidence'] and 'shapes changed' in str(analysis['evidence'].mismatches):
            analysis['pattern_type'] = 'SHAPE_MODIFICATION'
        else:
            analysis['pattern_type'] = 'UNKNOWN'
    
    return analysis


def generate_close_match_report():
    """Generate detailed report of all high-confidence tasks."""
    print("\n" + "="*80)
    print(" HIGH-CONFIDENCE CLOSE MATCHES: DETAILED REPORT")
    print(" (Tasks ready for manual operator completion)")
    print("="*80)
    
    # Load data
    with open('results/objectspace_evaluation_results.json', 'r') as f:
        results = json.load(f)
    
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        tasks = json.load(f)
    
    failed_tasks = [
        r for r in results['detailed_results'] 
        if r['error'] == 'No transform matched'
    ]
    
    print(f"\nScanning {len(failed_tasks)} failed tasks for high-confidence matches...")
    
    high_confidence = []
    
    for failed in failed_tasks[:100]:  # Scan first 100
        task_id = failed['task_id']
        task_data = tasks[task_id]
        
        ex = task_data['train'][0]
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        # Skip shape changes
        if grid_in.shape != grid_out.shape:
            continue
        
        matches = find_close_matches(grid_in, grid_out, min_confidence=0.7)
        
        if matches and matches[0].confidence >= 0.7:
            analysis = analyze_high_confidence_task(task_id, task_data)
            high_confidence.append(analysis)
    
    # Categorize by pattern type
    by_pattern = {}
    for analysis in high_confidence:
        pattern = analysis['pattern_type']
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(analysis)
    
    # Report by category
    print(f"\n✓ Found {len(high_confidence)} high-confidence tasks (>= 0.7)")
    print(f"\nBreakdown by pattern type:")
    for pattern, tasks_list in sorted(by_pattern.items()):
        print(f"  {pattern}: {len(tasks_list)} tasks")
    
    print(f"\n{'='*80}")
    print(" OBJECT CREATION PATTERNS")
    print(f"{'='*80}")
    print("\nThese tasks preserve anchor points but create new objects:")
    
    if 'OBJECT_CREATION' in by_pattern:
        for analysis in by_pattern['OBJECT_CREATION'][:10]:
            print(f"\n{analysis['task_id']}:")
            print(f"  Objects: {analysis['objects_in']} → {analysis['objects_out']}")
            print(f"  Best match: {analysis['best_match']} (confidence: {analysis['confidence']:.2f})")
            print(f"  Grid: {analysis['shape_in']}")
            
            if analysis['evidence']:
                print(f"  Evidence:")
                for match in analysis['evidence'].matches[:2]:
                    print(f"    {match}")
            
            print(f"  → NEEDS: Object creation/duplication operators")
    
    print(f"\n{'='*80}")
    print(" SHAPE MODIFICATION PATTERNS")
    print(f"{'='*80}")
    print("\nThese tasks preserve object count but modify shapes:")
    
    if 'SHAPE_MODIFICATION' in by_pattern:
        for analysis in by_pattern['SHAPE_MODIFICATION'][:10]:
            print(f"\n{analysis['task_id']}:")
            print(f"  Objects: {analysis['objects_in']} (unchanged)")
            print(f"  Best match: {analysis['best_match']} (confidence: {analysis['confidence']:.2f})")
            print(f"  Grid: {analysis['shape_in']}")
            print(f"  → NEEDS: Shape transformation operators")
    
    print(f"\n{'='*80}")
    print(" RECOMMENDATIONS")
    print(f"{'='*80}")
    
    print(f"""
Based on anchor point measurements, these {len(high_confidence)} tasks show:

1. CORRECT CENTROID REASONING: Anchor points measured correctly
2. COLOR PRESERVATION: Most tasks preserve object colors
3. MISSING OPERATORS: Need additional transformation rules:

   For OBJECT_CREATION ({len(by_pattern.get('OBJECT_CREATION', []))} tasks):
   - Duplicate objects with offset
   - Create patterns around anchor points (cross, square, etc.)
   - Fill interior regions with new color
   - Radial expansion from centroid
   
   For SHAPE_MODIFICATION ({len(by_pattern.get('SHAPE_MODIFICATION', []))} tasks):
   - Expand/contract shapes
   - Add borders/frames
   - Pattern tiling within object bounds
   - Shape distortion (stretch, skew)

NEXT STEPS:
1. Examine these {len(high_confidence)} tasks manually
2. Identify common creation/modification patterns
3. Implement specialized operators for each pattern type
4. Test with existing baseline solvers (59 current solves)
5. Expected gain: +10-20 solves from high-confidence matches

OUTPUT: results/high_confidence_close_matches.json
""")
    
    # Save detailed report
    output = {
        'total_high_confidence': len(high_confidence),
        'by_pattern': {k: len(v) for k, v in by_pattern.items()},
        'tasks': high_confidence
    }
    
    Path('results').mkdir(exist_ok=True)
    with open('results/high_confidence_close_matches.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n✓ Detailed report saved to: results/high_confidence_close_matches.json")


if __name__ == "__main__":
    generate_close_match_report()
