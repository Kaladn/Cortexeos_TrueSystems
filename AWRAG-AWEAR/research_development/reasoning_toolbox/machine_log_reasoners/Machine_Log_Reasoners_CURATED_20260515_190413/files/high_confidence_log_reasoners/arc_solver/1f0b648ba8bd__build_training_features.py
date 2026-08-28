"""
Build feature database from ALL 1000 training tasks.

This creates a lookup table:
- For each training task: extract features
- When solving test task: find K nearest neighbors in feature space
- Try operators that worked on similar training tasks FIRST

This is the REAL prior selector - use training data as oracle.
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.feature_extractor import FeatureExtractor
from arc_organ.arc_operators import OPERATORS, infer_rule_for_task

BASE_DIR = Path(__file__).parent.parent
TRAINING_CHALLENGES = BASE_DIR / "arc-prize-2025" / "arc-agi_training_challenges.json"
TRAINING_SOLUTIONS = BASE_DIR / "arc-prize-2025" / "arc-agi_training_solutions.json"
OUTPUT_DB = BASE_DIR / "training_feature_database.json"


def main():
    print("="*70)
    print("BUILDING TRAINING FEATURE DATABASE")
    print("="*70)
    print()
    
    # Load training data
    print("Loading training challenges and solutions...")
    with open(TRAINING_CHALLENGES) as f:
        challenges = json.load(f)
    with open(TRAINING_SOLUTIONS) as f:
        solutions = json.load(f)
    
    print(f"Loaded {len(challenges)} training tasks")
    print()
    
    # Initialize feature extractor
    extractor = FeatureExtractor()
    operators = OPERATORS
    
    # Build database
    database = {}
    solved_count = 0
    
    print("Extracting features and testing operators...")
    for i, (task_id, task_data) in enumerate(challenges.items(), 1):
        if i % 100 == 0:
            print(f"  [{i}/1000] processed, {solved_count} solvable with single operator")
        
        # Extract features (convert to numpy arrays)
        train_with_arrays = [
            {
                "input": np.array(pair["input"]),
                "output": np.array(pair["output"])
            }
            for pair in task_data["train"]
        ]
        features = extractor.extract({"train": train_with_arrays})
        
        # Try to solve with single operator
        train_pairs = [
            (np.array(pair["input"]), np.array(pair["output"]))
            for pair in task_data["train"]
        ]
        
        op, params = infer_rule_for_task(train_pairs)
        operator_name = op.name if op else None
        
        if operator_name:
            solved_count += 1
        
        # Store in database
        database[task_id] = {
            "features": features,
            "operator": operator_name,  # None if unsolvable with single op
            "train_count": len(task_data["train"]),
            "grid_shapes": [
                {"input": pair["input"], "output": pair["output"]}
                for pair in task_data["train"]
            ]
        }
    
    print(f"\n  [1000/1000] processed, {solved_count} solvable with single operator")
    print()
    
    # Save database
    print(f"Saving feature database to {OUTPUT_DB}...")
    
    # Convert numpy arrays to lists for JSON serialization
    for task_id, data in database.items():
        # Keep grid shapes as shape info only, not full grids
        data["grid_shapes"] = [
            {
                "input_shape": [len(pair["input"]), len(pair["input"][0]) if pair["input"] else 0],
                "output_shape": [len(pair["output"]), len(pair["output"][0]) if pair["output"] else 0]
            }
            for pair in task_data["train"]
        ]
    
    # Convert numpy types to Python types for JSON
    def convert_numpy(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        return obj
    
    database = convert_numpy(database)
    
    with open(OUTPUT_DB, 'w') as f:
        json.dump(database, f, indent=2)
    
    print(f"✓ Database saved: {len(database)} tasks")
    print()
    
    # Statistics
    print("="*70)
    print("STATISTICS")
    print("="*70)
    print(f"Total tasks: {len(database)}")
    print(f"Solvable with single operator: {solved_count} ({solved_count/10:.1f}%)")
    print(f"Need composition: {len(database) - solved_count} ({(len(database)-solved_count)/10:.1f}%)")
    print()
    
    # Operator distribution
    ops = [d["operator"] for d in database.values() if d["operator"]]
    print("Operator distribution (top 15):")
    for op, count in Counter(ops).most_common(15):
        print(f"  {count:3d}× {op}")
    print()
    
    print("✓ Feature database ready for prior selection!")


if __name__ == "__main__":
    main()
