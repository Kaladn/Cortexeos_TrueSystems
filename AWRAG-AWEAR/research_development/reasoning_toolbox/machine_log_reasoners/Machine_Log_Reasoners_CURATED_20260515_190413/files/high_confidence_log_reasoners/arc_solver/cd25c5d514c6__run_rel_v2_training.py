#!/usr/bin/env python3
"""
REL-ENGINE V2 - Full Training Set Evaluation
Run Euclidean geometry engine on all 1000 training tasks.
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


def run_full_training_evaluation():
    """Run REL-ENGINE v2 on all 1000 training tasks."""
    print("=" * 70)
    print("REL-ENGINE V2 - FULL TRAINING SET EVALUATION")
    print("Euclidean Geometry + 42 Transform Library")
    print("=" * 70)
    print()
    
    challenges, solutions = load_training_set()
    engine = RelEngineV2()
    
    results = {
        'total_tasks': 0,
        'detected': 0,
        'high_confidence': 0,
        'solved_tasks': [],
        'transforms_used': {},
        'failed_tasks': []
    }
    
    start_time = time.time()
    
    print(f"Processing {len(challenges)} tasks...\n")
    
    for i, task_id in enumerate(challenges.keys()):
        results['total_tasks'] += 1
        
        task_data = challenges[task_id]
        solution_data = solutions[task_id]
        
        # Build train pairs
        train_pairs = []
        for ex in task_data['train']:
            inp = np.array(ex['input'])
            out = np.array(ex['output'])
            train_pairs.append((inp, out))
        
        # Get test input and expected output
        test_input = np.array(task_data['test'][0]['input'])
        expected_output = np.array(solution_data[0])
        
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
                
                # Try to apply transform
                try:
                    # Find the matching transform from training
                    from engines.object_geometry import detect_objects, build_object_space
                    from engines.transform_library import TransformLibrary
                    
                    H, W = test_input.shape
                    objs = detect_objects(test_input)
                    os_test = build_object_space(objs, H, W)
                    
                    # Generate transforms and find the matching one
                    transforms = TransformLibrary.generate_all_transforms(os_test, os_test)
                    matching_transform = None
                    
                    for t in transforms:
                        if t.name == op:
                            matching_transform = t
                            break
                    
                    if matching_transform:
                        output = engine.apply_transform(test_input, matching_transform)
                        
                        if output is not None and np.array_equal(output, expected_output):
                            results['solved_tasks'].append({
                                'task_id': task_id,
                                'operation': op,
                                'confidence': top_hyp.confidence
                            })
                            print(f"✓ SOLVED: {task_id} ({op}, conf={top_hyp.confidence:.2f})")
                except Exception as e:
                    pass  # Continue on execution errors
            
        else:
            results['failed_tasks'].append(task_id)
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Progress: {i+1}/{len(challenges)} tasks ({rate:.1f} tasks/sec)")
    
    elapsed = time.time() - start_time
    
    # Print results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total tasks:          {results['total_tasks']}")
    print(f"Transforms detected:  {results['detected']} ({results['detected']/results['total_tasks']*100:.1f}%)")
    print(f"High confidence (≥0.8): {results['high_confidence']} ({results['high_confidence']/results['total_tasks']*100:.1f}%)")
    print(f"SOLVED:               {len(results['solved_tasks'])} ({len(results['solved_tasks'])/results['total_tasks']*100:.2f}%)")
    print(f"Time elapsed:         {elapsed:.1f}s ({results['total_tasks']/elapsed:.2f} tasks/sec)")
    print()
    
    if results['solved_tasks']:
        print("=" * 70)
        print(f"SOLVED TASKS ({len(results['solved_tasks'])})")
        print("=" * 70)
        for task in results['solved_tasks']:
            print(f"  {task['task_id']}: {task['operation']} (conf={task['confidence']:.2f})")
        print()
    
    # Transform usage breakdown
    print("=" * 70)
    print("TRANSFORM USAGE (TOP 10)")
    print("=" * 70)
    sorted_transforms = sorted(results['transforms_used'].items(), key=lambda x: x[1], reverse=True)
    for op, count in sorted_transforms[:10]:
        print(f"  {op:25s} {count:3d} ({count/results['detected']*100:.1f}%)")
    print()
    
    # Save results
    output_file = f"results/rel_v2_training_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total_tasks': results['total_tasks'],
                'detected': results['detected'],
                'high_confidence': results['high_confidence'],
                'solved': len(results['solved_tasks']),
                'elapsed_seconds': elapsed
            },
            'solved_tasks': results['solved_tasks'],
            'transforms_used': results['transforms_used'],
            'failed_count': len(results['failed_tasks'])
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print()
    
    return results


if __name__ == "__main__":
    results = run_full_training_evaluation()
    
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print()
    print("Note: 'Detected' = transform pattern identified in training pairs")
    print("      'Solved' = correct output generated for test input")
    print()
    print("Next step: Compare with baseline (64 solves) to measure improvement")
