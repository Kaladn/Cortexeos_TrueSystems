"""
Evaluate the Mixer on full ARC 2025 training set (1000 tasks).

This will:
1. Load all 1000 training tasks
2. Run the Mixer on each (single ops + 2-step composition)
3. Save results incrementally to avoid losing progress
4. Generate statistics on solve rate

TARGET: 100+ solves (10% coverage)
"""

import json
import sys
from pathlib import Path
import time
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.arc_operators import OPERATORS
from arc_organ.feature_extractor import FeatureExtractor
from arc_organ.mixer import CompositionMixer, PriorRanker


def load_training_data():
    """Load ARC 2025 training challenges."""
    data_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(data_path) as f:
        return json.load(f)


def evaluate_mixer():
    """Run mixer on all 1000 training tasks and save results."""
    print("="*70)
    print("MIXER EVALUATION - ARC 2025 TRAINING SET")
    print("="*70)
    print()
    
    # Load data
    print("Loading training challenges...")
    challenges = load_training_data()
    print(f"[OK] Loaded {len(challenges)} tasks")
    print()
    
    # Initialize components
    print("Initializing mixer...")
    feature_db_path = Path(__file__).parent.parent / "training_feature_database.json"
    prior_ranker = PriorRanker(feature_db_path) if feature_db_path.exists() else None
    mixer = CompositionMixer(OPERATORS, prior_ranker)
    extractor = FeatureExtractor()
    print()
    
    # Results storage
    results = {
        "single_solves": [],
        "composition_solves": [],
        "failed": [],
        "solve_details": {}
    }
    
    # Try to load existing results
    results_path = Path(__file__).parent.parent / "mixer_evaluation_results.json"
    if results_path.exists():
        print("Loading existing results...")
        with open(results_path) as f:
            results = json.load(f)
        print(f"[OK] Resuming from {len(results['solve_details'])} tasks")
        print()
    
    # Evaluate each task
    start_time = time.time()
    
    for idx, task_id in enumerate(challenges.keys(), 1):
        # Skip if already evaluated
        if task_id in results["solve_details"]:
            continue
        
        task = challenges[task_id]
        
        # Extract features
        features = extractor.extract(task)
        
        # Try to solve
        result = mixer.solve_task(task, features)
        
        # Record result
        if result:
            if result["type"] == "single":
                results["single_solves"].append(task_id)
                print(f"[{idx:4d}/1000] [SINGLE] {task_id}: {result['operators'][0]}")
            else:
                results["composition_solves"].append(task_id)
                print(f"[{idx:4d}/1000] [COMPOSITION] {task_id}: {' -> '.join(result['operators'])}")
            
            results["solve_details"][task_id] = {
                "type": result["type"],
                "operators": result["operators"]
            }
        else:
            results["failed"].append(task_id)
            if idx % 50 == 0:  # Only print failures every 50 tasks
                print(f"[{idx:4d}/1000] [FAILED] {task_id}")
        
        # Save progress every 100 tasks
        if idx % 100 == 0:
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
            
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = (1000 - idx) / rate
            print()
            print(f"Progress: {idx}/1000 tasks ({idx/10:.1f}%)")
            print(f"Solves: {len(results['single_solves'])} single + {len(results['composition_solves'])} composition = {len(results['single_solves']) + len(results['composition_solves'])} total")
            print(f"Rate: {rate:.1f} tasks/sec | ETA: {remaining/60:.1f} min")
            print()
    
    # Final save
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    total_solves = len(results["single_solves"]) + len(results["composition_solves"])
    print()
    print("="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Single operator solves:  {len(results['single_solves']):4d} ({len(results['single_solves'])/10:.1f}%)")
    print(f"Composition solves:      {len(results['composition_solves']):4d} ({len(results['composition_solves'])/10:.1f}%)")
    print(f"Total solves:            {total_solves:4d} ({total_solves/10:.1f}%)")
    print(f"Failed:                  {len(results['failed']):4d} ({len(results['failed'])/10:.1f}%)")
    print()
    
    # Show composition details
    if results["composition_solves"]:
        print("COMPOSITION DETAILS:")
        for task_id in results["composition_solves"]:
            ops = results["solve_details"][task_id]["operators"]
            print(f"  {task_id}: {' → '.join(ops)}")
        print()
    
    print(f"Results saved to: {results_path}")
    print()
    
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed/60:.1f} minutes ({elapsed/1000:.1f} sec/task)")


if __name__ == "__main__":
    evaluate_mixer()
