#!/usr/bin/env python3
"""Test periodic recolor detection on known tiling tasks."""

import json
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.base_engine import TaskView
from engines.color_engine import PatternEngine

def load_task(task_id):
    """Load a specific task."""
    train_path = Path("arc-prize-2024/arc-agi_training_challenges.json")
    with open(train_path) as f:
        tasks = json.load(f)
    return tasks[task_id]

def test_task(task_id):
    """Test periodic recolor detection on one task."""
    task = load_task(task_id)
    
    # Convert to TaskView
    train_pairs = [
        (np.array(pair['input']), np.array(pair['output']))
        for pair in task['train']
    ]
    test_input = np.array(task['test'][0]['input'])
    
    task_view = TaskView(
        train_pairs=train_pairs,
        test_input=test_input,
        task_id=task_id
    )
    
    # Test pattern engine
    engine = PatternEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"\n=== {task_id} ===")
    print(f"Found {len(hypotheses)} hypotheses:")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: {hyp.dsl_program} (conf={hyp.confidence:.2f})")
        print(f"    {hyp.explanation}")
    
    if not hypotheses:
        print("  [X] No patterns detected")
        
        # Debug: show first output
        if train_pairs:
            first_out = train_pairs[0][1]
            print(f"\n  First output shape: {first_out.shape}")
            print(f"  First output:\n{first_out}")

def main():
    """Test on the 13 tiling tasks identified."""
    tiling_tasks = [
        ("05269061", "tiling_3x3"),
        ("25ff71a9", "tiling_3x3"),
        ("6e02f1e3", "tiling_3x3"),
        ("794b24be", "tiling_3x3"),
        ("9565186b", "tiling_3x3"),
        ("0d3d703e", "tiling_1x3"),
        ("4be741c5", "tiling_1x3"),
        ("25d8a9c8", "tiling_3x1"),
        ("995c5fa3", "tiling_3x1"),
        ("5582e5ca", "tiling_1x2"),
        ("746b3537", "tiling_2x1"),
        ("d0f5fe59", "tiling_4x4"),
        ("ea786f4a", "tiling_2x2"),
    ]
    
    print("=== PATTERN-ENGINE TILING DETECTION TEST ===")
    
    detected = 0
    for task_id, expected_pattern in tiling_tasks:
        test_task(task_id)
        
        task = load_task(task_id)
        train_pairs = [(np.array(p['input']), np.array(p['output'])) for p in task['train']]
        test_input = np.array(task['test'][0]['input'])
        task_view = TaskView(train_pairs=train_pairs, test_input=test_input, task_id=task_id)
        
        engine = PatternEngine()
        hypotheses = engine.analyze(task_view)
        
        if hypotheses:
            detected += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Detected: {detected}/{len(tiling_tasks)} tiling tasks")
    print(f"Expected from analysis: 13 tiling patterns")
    print(f"Current PATTERN-ENGINE solves: 2")
    print()

if __name__ == "__main__":
    main()
