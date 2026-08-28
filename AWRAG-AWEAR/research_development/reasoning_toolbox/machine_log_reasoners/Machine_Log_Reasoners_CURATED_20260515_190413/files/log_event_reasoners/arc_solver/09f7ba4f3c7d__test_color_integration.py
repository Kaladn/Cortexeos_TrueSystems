"""
Test COLOR-ENGINE integration in MetaCompEngine.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
from pathlib import Path
from arc_organ.meta_comp_engine import MetaCompEngine
from arc_organ.arc_operators import OPERATORS


def load_task(task_id: str) -> dict:
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    with open(train_path, 'r') as f:
        data = json.load(f)
    return data[task_id]


def test_integration():
    """Test COLOR-ENGINE on the 2 perfect global mapping tasks."""
    print("=" * 80)
    print("TESTING COLOR-ENGINE INTEGRATION IN MetaCompEngine")
    print("=" * 80)
    print()
    
    # Initialize engine
    engine = MetaCompEngine(
        operators=OPERATORS,
        math_dsl_path=None,  # Skip macros for now
        use_color_engine=True
    )
    
    print(f"Engine initialized with {len(OPERATORS)} operators")
    print()
    
    # Test on the 2 perfect global mapping tasks
    perfect_tasks = ["b1948b0a", "c8f0f002"]
    
    for task_id in perfect_tasks:
        print(f"Testing {task_id}...")
        
        task = load_task(task_id)
        task['task_id'] = task_id
        
        # Solve
        result = engine.solve_task(task_id, task)
        
        if result and result.get('source') == 'color_engine':
            print(f"  ✓✓ SOLVED BY COLOR-ENGINE!")
            print(f"     Operator chain: {result['operator_chain']}")
            
            # Verify correctness (if we have test solutions)
            # For now just confirm we got predictions
            print(f"     Generated {len(result['predictions'])} predictions")
        else:
            print(f"  ✗ Not solved by COLOR-ENGINE (may be solved by other operators)")
        
        print()
    
    print("=" * 80)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_integration()
