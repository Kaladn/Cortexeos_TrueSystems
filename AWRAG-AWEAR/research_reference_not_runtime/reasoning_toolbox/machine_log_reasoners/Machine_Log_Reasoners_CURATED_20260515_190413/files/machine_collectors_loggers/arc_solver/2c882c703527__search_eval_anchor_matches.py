"""
Search evaluation tasks using the anchor point measurement system.

Find high-confidence close matches in eval set.
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
from arc_organ.transform_matcher import find_close_matches

# Load evaluation challenges
with open('arc-prize-2024/arc-agi_evaluation_challenges.json') as f:
    eval_tasks = json.load(f)

print('Searching evaluation set with anchor point measurements...')
print('='*70)

high_confidence = []
medium_confidence = []

checked = 0
for task_id, task_data in eval_tasks.items():
    checked += 1
    if checked % 50 == 0:
        print(f'Checked {checked} tasks...')
    
    if not task_data.get('train'):
        continue
    
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    # Skip if shapes changed (not currently handled)
    if grid_in.shape != grid_out.shape:
        continue
    
    try:
        matches = find_close_matches(grid_in, grid_out, min_confidence=0.3)
        
        if matches:
            best_match = matches[0]
            
            if best_match.confidence >= 0.7:
                high_confidence.append((task_id, best_match))
            elif best_match.confidence >= 0.5:
                medium_confidence.append((task_id, best_match))
    except:
        continue

print(f'\nSearched {checked} evaluation tasks')
print('='*70)

print(f'\nHIGH CONFIDENCE (>= 0.7): {len(high_confidence)} tasks')
for task_id, match in high_confidence[:10]:
    print(f'  {task_id}: {match.transform_name} (conf={match.confidence:.2f}), '
          f'{len(match.measurements)} objects, colors_ok={match.color_preserved}')

if len(high_confidence) > 10:
    print(f'  ... and {len(high_confidence)-10} more')

print(f'\nMEDIUM CONFIDENCE (0.5-0.7): {len(medium_confidence)} tasks')
for task_id, match in medium_confidence[:10]:
    print(f'  {task_id}: {match.transform_name} (conf={match.confidence:.2f}), '
          f'{len(match.measurements)} objects')

if len(medium_confidence) > 10:
    print(f'  ... and {len(medium_confidence)-10} more')

# Save results
results = {
    'high_confidence': [(tid, {'transform': m.transform_name, 'confidence': m.confidence, 
                                'objects': len(m.measurements), 'color_preserved': m.color_preserved})
                        for tid, m in high_confidence],
    'medium_confidence': [(tid, {'transform': m.transform_name, 'confidence': m.confidence,
                                  'objects': len(m.measurements)})
                          for tid, m in medium_confidence]
}

with open('results/eval_anchor_point_matches.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f'\n✓ Results saved to: results/eval_anchor_point_matches.json')
print(f'\nThese {len(high_confidence)} high-confidence eval tasks are ready for operator development!')
