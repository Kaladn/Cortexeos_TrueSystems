#!/usr/bin/env python3
"""
Integration Test - Euclidean Geometry with ARC-CORE
Test REL-ENGINE v2 on actual ARC training tasks.
"""

import json
import numpy as np
from engines.rel_engine_v2 import RelEngineV2
from engines.base_engine import TaskView


def load_training_set():
    """Load ARC training challenges."""
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        challenges = json.load(f)
    with open('arc-prize-2024/arc-agi_training_solutions.json', 'r') as f:
        solutions = json.load(f)
    return challenges, solutions


def test_rel_engine_v2_on_training():
    """Test REL-ENGINE v2 on training set."""
    print("=" * 60)
    print("REL-ENGINE V2 - TRAINING SET TEST")
    print("=" * 60)
    print()
    
    challenges, solutions = load_training_set()
    
    engine = RelEngineV2()
    
    solves = 0
    total = 0
    solved_tasks = []
    
    # Test on first 100 tasks (quick validation)
    task_ids = list(challenges.keys())[:100]
    
    for task_id in task_ids:
        total += 1
        
        task_data = challenges[task_id]
        solution_data = solutions[task_id]
        
        # Build train pairs
        train_pairs = []
        for ex in task_data['train']:
            inp = np.array(ex['input'])
            out = np.array(ex['output'])
            train_pairs.append((inp, out))
        
        # Get test input
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
            # Try top hypothesis
            hyp = hypotheses[0]
            
            # For now, just check if we detected a transform
            # (Full execution requires wiring into ARC-CORE)
            if hyp.confidence > 0.8:
                solves += 1
                solved_tasks.append({
                    'task_id': task_id,
                    'operation': hyp.operation,
                    'confidence': hyp.confidence
                })
                print(f"✓ {task_id}: {hyp.operation} (conf={hyp.confidence:.2f})")
    
    print()
    print("=" * 60)
    print(f"RESULTS: {solves}/{total} tasks analyzed ({solves/total*100:.1f}%)")
    print("=" * 60)
    print()
    
    if solved_tasks:
        print("Detected transforms:")
        for task in solved_tasks[:10]:
            print(f"  - {task['task_id']}: {task['operation']} ({task['confidence']:.2f})")
    
    return solves, total


if __name__ == "__main__":
    solves, total = test_rel_engine_v2_on_training()
    
    print()
    print("Note: This test only validates transform DETECTION.")
    print("Full solve count requires integration with ARC-CORE execution.")
