"""
Scan failed tasks for close matches using anchor point measurements.

Reports tasks with high-confidence partial matches for manual examination.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from arc_organ.transform_matcher import find_close_matches, report_close_matches


def scan_failed_tasks_for_close_matches():
    """Scan failed tasks and report close matches."""
    print("\n" + "="*80)
    print(" SCANNING FAILED TASKS FOR CLOSE MATCHES")
    print("="*80)
    
    # Load evaluation results
    with open('results/objectspace_evaluation_results.json', 'r') as f:
        results = json.load(f)
    
    # Load task data
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        tasks = json.load(f)
    
    # Get failed tasks with "No transform matched"
    failed_tasks = [
        r for r in results['detailed_results'] 
        if r['error'] == 'No transform matched'
    ]
    
    print(f"\nAnalyzing {len(failed_tasks)} failed tasks...")
    print("Looking for matches with confidence >= 0.5\n")
    
    high_confidence_matches = []
    medium_confidence_matches = []
    
    for i, failed in enumerate(failed_tasks[:50]):  # Sample first 50
        task_id = failed['task_id']
        task_data = tasks[task_id]
        
        ex = task_data['train'][0]
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        # Skip if shapes changed (not currently handled)
        if grid_in.shape != grid_out.shape:
            continue
        
        matches = find_close_matches(grid_in, grid_out, min_confidence=0.3)
        
        if matches:
            best_match = matches[0]
            
            if best_match.confidence >= 0.7:
                high_confidence_matches.append((task_id, best_match))
            elif best_match.confidence >= 0.5:
                medium_confidence_matches.append((task_id, best_match))
    
    # Report high confidence matches
    print(f"\n{'='*80}")
    print(f" HIGH CONFIDENCE MATCHES (>= 0.7)")
    print(f"{'='*80}")
    
    if high_confidence_matches:
        print(f"\nFound {len(high_confidence_matches)} task(s) with high confidence:\n")
        
        for task_id, match in high_confidence_matches[:5]:
            task_data = tasks[task_id]
            ex = task_data['train'][0]
            grid_in = np.array(ex['input'])
            grid_out = np.array(ex['output'])
            
            report_close_matches(task_id, grid_in, grid_out)
    else:
        print("\n❌ No high confidence matches found")
    
    # Report medium confidence matches
    print(f"\n{'='*80}")
    print(f" MEDIUM CONFIDENCE MATCHES (0.5-0.7)")
    print(f"{'='*80}")
    
    if medium_confidence_matches:
        print(f"\nFound {len(medium_confidence_matches)} task(s) with medium confidence:\n")
        
        for task_id, match in medium_confidence_matches[:5]:
            print(f"  {task_id}: {match.transform_name} (confidence: {match.confidence:.2f})")
            print(f"    Objects: {len(match.measurements)}, Avg distance: {match.avg_distance:.2f}")
            print(f"    Matches: {len(match.matches)}, Mismatches: {len(match.mismatches)}")
            
            if match.mismatches:
                print(f"    Key issue: {match.mismatches[0]}")
            print()
    else:
        print("\n❌ No medium confidence matches found")
    
    # Summary
    print(f"\n{'='*80}")
    print(f" SUMMARY")
    print(f"{'='*80}")
    print(f"\nTasks analyzed: 50")
    print(f"High confidence (>= 0.7): {len(high_confidence_matches)}")
    print(f"Medium confidence (0.5-0.7): {len(medium_confidence_matches)}")
    print(f"\nThese tasks are good candidates for:")
    print(f"  - Manual rule crafting with other operators")
    print(f"  - Transform composition (multi-step)")
    print(f"  - Partial transform patterns")


if __name__ == "__main__":
    scan_failed_tasks_for_close_matches()
