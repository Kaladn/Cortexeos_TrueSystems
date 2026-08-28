"""
ARC-CORE Full Evaluation — 8-Engine Architecture

Tests the new ARC-CORE system with all engines on full dataset.
Currently: GEO-ENGINE operational, others stubbed.
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from arc_core import ArcCore


def load_dataset():
    """Load ARC 2025 training dataset."""
    base_path = Path(__file__).parent / 'arc-prize-2025'
    
    with open(base_path / 'arc-agi_training_challenges.json') as f:
        train_data = json.load(f)
    
    with open(base_path / 'arc-agi_training_solutions.json') as f:
        solutions = json.load(f)
    
    return train_data, solutions


def main():
    """Run full evaluation with ARC-CORE."""
    print("=" * 80)
    print("ARC-CORE — FULL 8-ENGINE EVALUATION")
    print("=" * 80)
    print()
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load dataset
    print("Loading dataset...")
    challenges, solutions = load_dataset()
    print(f"  Training tasks: {len(challenges)}")
    print()
    
    # Initialize ARC-CORE
    print("Initializing ARC-CORE...")
    core = ArcCore()
    print(f"  Engines: 8 (GEO operational, others stubbed)")
    print()
    
    # Results
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(challenges),
            "architecture": "ARC-CORE 8-engine"
        },
        "solutions": {},
        "failed_tasks": [],
        "stats": {
            "macro": 0,
            "single_engine": 0,
            "composition": 0,
            "total": 0,
            "by_engine": {}
        }
    }
    
    print("=" * 80)
    print("RUNNING EVALUATION")
    print("=" * 80)
    print()
    
    start_time = time.time()
    
    for i, (task_id, task_data) in enumerate(sorted(challenges.items())):
        # Progress
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (len(challenges) - i - 1) / rate
            solved = results["stats"]["total"]
            print(f"[{i+1}/{len(challenges)}] Solved: {solved}, ETA: ~{remaining:.0f}s")
        
        # Add test with solution
        task_data_copy = task_data.copy()
        task_data_copy['test'] = [{'input': solutions[task_id][0]}]
        
        # Solve with ARC-CORE
        trace = core.solve(task_data_copy, task_id=task_id)
        
        if trace.success:
            # Record solution
            results["solutions"][task_id] = {
                "method": trace.method,
                "dsl": trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else None,
                "engine": trace.winning_hypothesis.engine_name if trace.winning_hypothesis else None,
                "confidence": trace.winning_hypothesis.confidence if trace.winning_hypothesis else 0.0,
                "time": trace.execution_time
            }
            
            # Update stats
            if trace.method == "macro":
                results["stats"]["macro"] += 1
            elif trace.method == "single_engine":
                results["stats"]["single_engine"] += 1
                engine = trace.winning_hypothesis.engine_name
                results["stats"]["by_engine"][engine] = results["stats"]["by_engine"].get(engine, 0) + 1
            elif trace.method == "composition":
                results["stats"]["composition"] += 1
            
            results["stats"]["total"] += 1
        else:
            results["failed_tasks"].append(task_id)
    
    elapsed = time.time() - start_time
    
    # Print results
    print()
    print("=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print()
    
    total = results["stats"]["total"]
    failed = len(results["failed_tasks"])
    
    print(f"Results:")
    print(f"  Macro solves:        {results['stats']['macro']:4d}")
    print(f"  Single-engine:       {results['stats']['single_engine']:4d}")
    print(f"  Composition:         {results['stats']['composition']:4d}")
    print(f"  Total solved:        {total:4d} ({total/len(challenges)*100:.2f}%)")
    print(f"  Failed:              {failed:4d} ({failed/len(challenges)*100:.2f}%)")
    print()
    
    if results["stats"]["by_engine"]:
        print("By engine:")
        for engine, count in sorted(results["stats"]["by_engine"].items(), key=lambda x: -x[1]):
            print(f"  {engine:12s}: {count:4d}")
        print()
    
    print(f"Performance:")
    print(f"  Total time:          {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"  Average per task:    {elapsed/len(challenges):.3f}s")
    print()
    
    # Comparison
    print("Comparison vs baseline:")
    print(f"  Baseline (old):      59 solves")
    print(f"  ARC-CORE (new):      {total} solves")
    delta = total - 59
    if delta > 0:
        print(f"  ✓ Improvement:       +{delta} solves")
    elif delta < 0:
        print(f"  ⚠ Regression:        {delta} solves")
    else:
        print(f"  = No change")
    print()
    
    # Save results
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'arc_core_results_{timestamp}.json'
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}")
    print()
    print("=" * 80)
    
    # Get ARC-CORE stats
    core_stats = core.get_statistics()
    print()
    print("ARC-CORE Statistics:")
    print(f"  Tasks solved:        {core_stats['tasks_solved']}")
    print(f"  Macro solves:        {core_stats['macro_solves']}")
    print(f"  Single-engine:       {core_stats['single_engine_solves']}")
    print(f"  Compositions:        {core_stats['composition_solves']}")
    print()


if __name__ == "__main__":
    main()
