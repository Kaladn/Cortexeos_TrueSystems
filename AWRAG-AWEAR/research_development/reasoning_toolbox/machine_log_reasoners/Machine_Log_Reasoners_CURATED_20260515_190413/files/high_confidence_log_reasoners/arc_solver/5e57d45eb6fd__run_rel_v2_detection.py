#!/usr/bin/env python3
"""
REL-ENGINE V2 - Detection Report (No Execution)
Pure transform detection on training set.
"""

import json
import time
import numpy as np
from engines.rel_engine_v2 import RelEngineV2
from engines.base_engine import TaskView


def load_training_set():
    """Load ARC training challenges and solutions."""
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        challenges = json.load(f)
    with open('arc-prize-2024/arc-agi_training_solutions.json', 'r') as f:
        solutions = json.load(f)
    return challenges, solutions


def run_detection_report():
    """Pure detection - no execution."""
    print("=" * 70)
    print("REL-ENGINE V2 - TRANSFORM DETECTION REPORT")
    print("Euclidean Geometry + 42 Transform Library")
    print("=" * 70)
    print()
    
    challenges, solutions = load_training_set()
    engine = RelEngineV2()
    
    results = {
        'total_tasks': 0,
        'detected': 0,
        'high_confidence': 0,
        'detected_tasks': [],
        'transforms_used': {},
    }
    
    start_time = time.time()
    
    print(f"Processing {len(challenges)} tasks...\n")
    
    for i, task_id in enumerate(challenges.keys()):
        results['total_tasks'] += 1
        
        task_data = challenges[task_id]
        
        # Build train pairs
        train_pairs = []
        for ex in task_data['train']:
            inp = np.array(ex['input'])
            out = np.array(ex['output'])
            train_pairs.append((inp, out))
        
        test_input = np.array(task_data['test'][0]['input'])
        
        # Create TaskView
        task_view = TaskView(
            train_pairs=train_pairs,
            test_input=test_input,
            task_id=task_id
        )
        
        # Analyze task
        hypotheses = engine.analyze(task_view)
        
        if hypotheses:
            results['detected'] += 1
            top_hyp = hypotheses[0]
            
            # Track transform usage
            op = top_hyp.operation
            results['transforms_used'][op] = results['transforms_used'].get(op, 0) + 1
            
            if top_hyp.confidence >= 0.8:
                results['high_confidence'] += 1
                results['detected_tasks'].append({
                    'task_id': task_id,
                    'operation': op,
                    'confidence': top_hyp.confidence,
                    'params': top_hyp.params
                })
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Progress: {i+1}/{len(challenges)} tasks ({rate:.1f} tasks/sec)")
    
    elapsed = time.time() - start_time
    
    # Print results
    print()
    print("=" * 70)
    print("DETECTION RESULTS")
    print("=" * 70)
    print(f"Total tasks:           {results['total_tasks']}")
    print(f"Transforms detected:   {results['detected']} ({results['detected']/results['total_tasks']*100:.1f}%)")
    print(f"High confidence (≥0.8): {results['high_confidence']} ({results['high_confidence']/results['total_tasks']*100:.1f}%)")
    print(f"Time elapsed:          {elapsed:.1f}s ({results['total_tasks']/elapsed:.2f} tasks/sec)")
    print()
    
    # Transform usage breakdown
    print("=" * 70)
    print("TRANSFORM DISTRIBUTION")
    print("=" * 70)
    sorted_transforms = sorted(results['transforms_used'].items(), key=lambda x: x[1], reverse=True)
    for op, count in sorted_transforms:
        pct = count/results['detected']*100 if results['detected'] > 0 else 0
        print(f"  {op:30s} {count:3d} ({pct:5.1f}%)")
    print()
    
    if results['detected_tasks']:
        print("=" * 70)
        print(f"HIGH CONFIDENCE DETECTIONS (≥0.8)")
        print("=" * 70)
        for task in results['detected_tasks'][:20]:  # Show first 20
            print(f"  {task['task_id']}: {task['operation']:25s} (conf={task['confidence']:.2f})")
        if len(results['detected_tasks']) > 20:
            print(f"  ... and {len(results['detected_tasks']) - 20} more")
        print()
    
    # Save results
    output_file = f"results/rel_v2_detection_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total_tasks': results['total_tasks'],
                'detected': results['detected'],
                'high_confidence': results['high_confidence'],
                'detection_rate': results['detected']/results['total_tasks'],
                'elapsed_seconds': elapsed
            },
            'detected_tasks': results['detected_tasks'],
            'transforms_used': results['transforms_used']
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print()
    
    return results


if __name__ == "__main__":
    results = run_detection_report()
    
    print("=" * 70)
    print("DETECTION COMPLETE")
    print("=" * 70)
    print()
    print(f"REL-ENGINE V2 detected geometric transforms in {results['detected']} tasks.")
    print(f"This represents {results['detected']/results['total_tasks']*100:.1f}% of the training set.")
    print()
    print("These are pure spatial relation tasks that the Euclidean geometry")
    print("engine can recognize. Execution requires ARC-CORE integration.")
