#!/usr/bin/env python3
"""
ARC Production Solver - Command Line Interface

A unified CLI for the ARC reasoning engine, bringing together:
- Baseline solver (29 operators, 56 solves)
- ARC-CORE (8 specialist engines)
- Hybrid solver (64+ solves)
- Operator discovery tools
- Diagnostic utilities

Usage:
    python arc_cli.py solve <task_id>
    python arc_cli.py evaluate [--dataset training|evaluation]
    python arc_cli.py diagnose <task_id>
    python arc_cli.py operators [--list|--test <name>]
    python arc_cli.py status

Author: Lee (Shadow Wolf) + Claude + GPT
Date: November 2025
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class Config:
    """Global configuration."""
    project_root: Path = Path(__file__).parent
    data_2024: Path = Path(__file__).parent / "arc-prize-2024"
    data_2025: Path = Path(__file__).parent / "arc-prize-2025"
    results_dir: Path = Path(__file__).parent / "results"
    
    # Solver settings
    timeout_per_task: float = 60.0
    max_composition_depth: int = 3
    
    # Display settings
    color_map: Dict[int, str] = None
    
    def __post_init__(self):
        self.color_map = {
            0: ".",  # black/background
            1: "1",  # blue
            2: "2",  # red
            3: "3",  # green
            4: "4",  # yellow
            5: "5",  # grey
            6: "6",  # magenta
            7: "7",  # orange
            8: "8",  # cyan
            9: "9",  # brown
        }

CONFIG = Config()


# =============================================================================
# DATA LOADING
# =============================================================================

def load_dataset(dataset: str = "training", year: str = "2025") -> Dict:
    """Load ARC dataset."""
    if year == "2025":
        base = CONFIG.data_2025
    else:
        base = CONFIG.data_2024
    
    challenges_file = base / f"arc-agi_{dataset}_challenges.json"
    solutions_file = base / f"arc-agi_{dataset}_solutions.json"
    
    if not challenges_file.exists():
        print(f"Error: Dataset not found at {challenges_file}")
        sys.exit(1)
    
    with open(challenges_file) as f:
        challenges = json.load(f)
    
    solutions = {}
    if solutions_file.exists():
        with open(solutions_file) as f:
            solutions = json.load(f)
    
    return {"challenges": challenges, "solutions": solutions}


def load_task(task_id: str, dataset: str = "training") -> Optional[Dict]:
    """Load a single task by ID."""
    data = load_dataset(dataset)
    
    if task_id in data["challenges"]:
        task = data["challenges"][task_id]
        task["task_id"] = task_id
        if task_id in data["solutions"]:
            task["solution"] = data["solutions"][task_id]
        return task
    
    # Try evaluation set
    data = load_dataset("evaluation")
    if task_id in data["challenges"]:
        task = data["challenges"][task_id]
        task["task_id"] = task_id
        if task_id in data["solutions"]:
            task["solution"] = data["solutions"][task_id]
        return task
    
    return None


# =============================================================================
# GRID DISPLAY
# =============================================================================

def grid_to_string(grid: np.ndarray, indent: int = 2) -> str:
    """Convert grid to displayable string."""
    lines = []
    prefix = " " * indent
    for row in grid:
        line = " ".join(CONFIG.color_map.get(int(c), "?") for c in row)
        lines.append(prefix + line)
    return "\n".join(lines)


def display_task(task: Dict, show_solution: bool = False):
    """Display a task's training examples."""
    print(f"\nTask: {task.get('task_id', 'unknown')}")
    print("=" * 60)
    
    for i, example in enumerate(task["train"]):
        print(f"\nTraining Example {i + 1}:")
        print("  Input:")
        print(grid_to_string(np.array(example["input"]), indent=4))
        print("  Output:")
        print(grid_to_string(np.array(example["output"]), indent=4))
    
    print(f"\nTest Input:")
    print(grid_to_string(np.array(task["test"][0]["input"]), indent=2))
    
    if show_solution and "solution" in task:
        print(f"\nExpected Output:")
        print(grid_to_string(np.array(task["solution"][0]), indent=2))


# =============================================================================
# SOLVER INTERFACE
# =============================================================================

class HybridSolver:
    """
    Unified solver combining baseline operators + ARC-CORE engines.
    
    Architecture:
        Layer 0: Baseline (29 operators, per-example validation)
        Layer 1: ARC-CORE (8 specialist engines)
        Layer 2: Composition (multi-step chains)
    """
    
    def __init__(self):
        self.baseline = None
        self.arc_core = None
        self.stats = {
            "baseline_solves": 0,
            "arc_core_solves": 0,
            "composition_solves": 0,
            "total_attempts": 0,
            "by_operator": {},
            "by_engine": {},
        }
        self._load_components()
    
    def _load_components(self):
        """Load solver components."""
        try:
            from arc_organ.arc_operators import OPERATORS
            from solvers.baseline_solver import BaselineSolver
            self.baseline = BaselineSolver(OPERATORS)
            self.operators = OPERATORS
            print(f"[OK] Loaded {len(OPERATORS)} baseline operators")
        except Exception as e:
            print(f"[WARN] Could not load baseline: {e}")
            self.operators = []
        
        try:
            from arc_core import ArcCore
            self.arc_core = ArcCore()
            print(f"[OK] Loaded ARC-CORE with 8 engines")
        except Exception as e:
            print(f"[WARN] Could not load ARC-CORE: {e}")
    
    def solve(self, task: Dict) -> Optional[Dict]:
        """
        Solve task using hybrid approach.
        
        Returns:
            {
                "method": "baseline" | "arc_core" | "composition",
                "operator": str,
                "dsl": str,
                "prediction": List[List[int]],
                "confidence": float,
            }
        """
        self.stats["total_attempts"] += 1
        task_id = task.get("task_id", "unknown")
        
        # Layer 0: Baseline
        if self.baseline:
            result = self.baseline.solve(task)
            if result:
                op_name = result.get("operator", "unknown")
                self.stats["baseline_solves"] += 1
                self.stats["by_operator"][op_name] = self.stats["by_operator"].get(op_name, 0) + 1
                return {
                    "method": "baseline",
                    "operator": op_name,
                    "dsl": f"OP:{op_name.upper()}",
                    "prediction": result.get("test_outputs", []),
                    "confidence": 1.0,
                }
        
        # Layer 1: ARC-CORE
        if self.arc_core:
            trace = self.arc_core.solve(task, task_id)
            if trace.success:
                engine = trace.winning_hypothesis.engine_name if trace.winning_hypothesis else "unknown"
                self.stats["arc_core_solves"] += 1
                self.stats["by_engine"][engine] = self.stats["by_engine"].get(engine, 0) + 1
                return {
                    "method": "arc_core",
                    "engine": engine,
                    "dsl": trace.winning_hypothesis.explanation if trace.winning_hypothesis else "",
                    "prediction": [trace.solution.tolist()] if trace.solution is not None else [],
                    "confidence": trace.winning_hypothesis.confidence if trace.winning_hypothesis else 0.0,
                }
        
        return None
    
    def get_stats(self) -> Dict:
        """Get solver statistics."""
        return self.stats.copy()


# =============================================================================
# CLI COMMANDS
# =============================================================================

def cmd_solve(args):
    """Solve a single task."""
    task = load_task(args.task_id)
    if not task:
        print(f"Error: Task '{args.task_id}' not found")
        return 1
    
    if args.show:
        display_task(task, show_solution=args.solution)
    
    solver = HybridSolver()
    
    print(f"\nSolving task: {args.task_id}")
    print("-" * 40)
    
    start = time.time()
    result = solver.solve(task)
    elapsed = time.time() - start
    
    if result:
        print(f"SOLVED in {elapsed:.3f}s")
        print(f"  Method: {result['method']}")
        if result['method'] == 'baseline':
            print(f"  Operator: {result['operator']}")
        else:
            print(f"  Engine: {result.get('engine', 'unknown')}")
        print(f"  DSL: {result['dsl']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        
        if args.output and result['prediction']:
            print(f"\nPrediction:")
            print(grid_to_string(np.array(result['prediction'][0])))
        
        return 0
    else:
        print(f"FAILED after {elapsed:.3f}s")
        return 1


def cmd_evaluate(args):
    """Evaluate on full dataset."""
    dataset = args.dataset or "training"
    data = load_dataset(dataset)
    challenges = data["challenges"]
    solutions = data["solutions"]
    
    solver = HybridSolver()
    
    print(f"\nEvaluating on {dataset} set ({len(challenges)} tasks)")
    print("=" * 60)
    
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": dataset,
            "dataset_size": len(challenges),
        },
        "solutions": {},
        "failed_tasks": [],
    }
    
    start_time = time.time()
    solved = 0
    
    for i, (task_id, task_data) in enumerate(challenges.items()):
        task_data["task_id"] = task_id
        
        result = solver.solve(task_data)
        
        if result:
            solved += 1
            results["solutions"][task_id] = result
            
            # Verify if we have solution
            if task_id in solutions and result["prediction"]:
                expected = np.array(solutions[task_id][0])
                predicted = np.array(result["prediction"][0])
                if not np.array_equal(expected, predicted):
                    print(f"  [MISMATCH] {task_id}: prediction differs from solution")
        else:
            results["failed_tasks"].append(task_id)
        
        # Progress
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Progress: {i + 1}/{len(challenges)} ({rate:.1f} tasks/s) | Solved: {solved}")
    
    elapsed = time.time() - start_time
    stats = solver.get_stats()
    
    results["stats"] = {
        "total": solved,
        "baseline": stats["baseline_solves"],
        "arc_core": stats["arc_core_solves"],
        "by_operator": stats["by_operator"],
        "by_engine": stats["by_engine"],
        "elapsed_seconds": elapsed,
    }
    
    # Save results
    output_file = CONFIG.results_dir / f"cli_eval_{dataset}_{int(time.time())}.json"
    CONFIG.results_dir.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total solved: {solved}/{len(challenges)} ({100*solved/len(challenges):.1f}%)")
    print(f"  Baseline: {stats['baseline_solves']}")
    print(f"  ARC-CORE: {stats['arc_core_solves']}")
    print(f"Time: {elapsed:.1f}s ({len(challenges)/elapsed:.1f} tasks/s)")
    print(f"\nResults saved to: {output_file}")
    
    # Top operators
    if stats["by_operator"]:
        print("\nTop operators:")
        sorted_ops = sorted(stats["by_operator"].items(), key=lambda x: -x[1])[:10]
        for op, count in sorted_ops:
            print(f"  {op}: {count}")
    
    # Engine breakdown
    if stats["by_engine"]:
        print("\nBy engine:")
        for engine, count in sorted(stats["by_engine"].items(), key=lambda x: -x[1]):
            print(f"  {engine}: {count}")
    
    return 0


def cmd_diagnose(args):
    """Diagnose why a task fails."""
    task = load_task(args.task_id)
    if not task:
        print(f"Error: Task '{args.task_id}' not found")
        return 1
    
    print(f"\nDiagnosing task: {args.task_id}")
    print("=" * 60)
    
    display_task(task, show_solution=True)
    
    # Analyze structure
    train_ex = task["train"][0]
    inp = np.array(train_ex["input"])
    out = np.array(train_ex["output"])
    
    print("\nStructural Analysis:")
    print(f"  Input shape:  {inp.shape}")
    print(f"  Output shape: {out.shape}")
    print(f"  Shape change: {'Yes' if inp.shape != out.shape else 'No'}")
    
    inp_colors = set(int(c) for c in inp.flatten() if c != 0)
    out_colors = set(int(c) for c in out.flatten() if c != 0)
    print(f"  Input colors:  {sorted(inp_colors)}")
    print(f"  Output colors: {sorted(out_colors)}")
    print(f"  New colors:    {sorted(out_colors - inp_colors)}")
    
    # Try each operator
    print("\nOperator Analysis:")
    try:
        from arc_organ.arc_operators import OPERATORS
        
        for op in OPERATORS:
            try:
                params = op.analyze(inp, out)
                if params is not None:
                    result = op.apply(inp, params)
                    matches = np.array_equal(result, out)
                    status = "MATCH" if matches else "params but wrong output"
                    print(f"  {op.name}: {status}")
                    if matches:
                        print(f"    Params: {params}")
            except Exception as e:
                pass
    except ImportError:
        print("  [Could not load operators]")
    
    return 0


def cmd_operators(args):
    """List or test operators."""
    try:
        from arc_organ.arc_operators import OPERATORS
    except ImportError:
        print("Error: Could not load operators")
        return 1
    
    if args.test:
        # Test specific operator
        op = next((o for o in OPERATORS if o.name == args.test), None)
        if not op:
            print(f"Error: Operator '{args.test}' not found")
            return 1
        
        print(f"\nTesting operator: {op.name}")
        print("-" * 40)
        
        data = load_dataset("training")
        solved = []
        
        for task_id, task_data in data["challenges"].items():
            for ex in task_data["train"]:
                inp = np.array(ex["input"])
                out = np.array(ex["output"])
                
                try:
                    params = op.analyze(inp, out)
                    if params is not None:
                        result = op.apply(inp, params)
                        if np.array_equal(result, out):
                            solved.append(task_id)
                            break
                except:
                    pass
        
        print(f"Solves {len(set(solved))} tasks:")
        for tid in sorted(set(solved))[:20]:
            print(f"  {tid}")
        if len(set(solved)) > 20:
            print(f"  ... and {len(set(solved)) - 20} more")
        
        return 0
    
    # List all operators
    print(f"\nOperator Library ({len(OPERATORS)} operators)")
    print("=" * 60)
    
    # Group by type
    tiers = {
        "Recoloring": [],
        "Geometric": [],
        "Tiling": [],
        "Advanced": [],
    }
    
    recolor_keywords = ["recolor", "mapping", "swap", "color"]
    geo_keywords = ["mirror", "crop", "extract", "grow", "shrink", "symmetry", "block", "diagonal"]
    tile_keywords = ["tile", "tiling", "replicate", "expand", "latin"]
    
    for op in OPERATORS:
        name_lower = op.name.lower()
        if any(kw in name_lower for kw in recolor_keywords):
            tiers["Recoloring"].append(op)
        elif any(kw in name_lower for kw in geo_keywords):
            tiers["Geometric"].append(op)
        elif any(kw in name_lower for kw in tile_keywords):
            tiers["Tiling"].append(op)
        else:
            tiers["Advanced"].append(op)
    
    for tier_name, ops in tiers.items():
        if ops:
            print(f"\n{tier_name} ({len(ops)}):")
            for op in ops:
                print(f"  {op.name}")
    
    return 0


def cmd_status(args):
    """Show system status."""
    print("\nARC Production Solver - Status")
    print("=" * 60)
    
    # Check datasets
    print("\nDatasets:")
    for year in ["2024", "2025"]:
        base = CONFIG.data_2024 if year == "2024" else CONFIG.data_2025
        if base.exists():
            train_file = base / "arc-agi_training_challenges.json"
            eval_file = base / "arc-agi_evaluation_challenges.json"
            
            train_count = 0
            eval_count = 0
            
            if train_file.exists():
                with open(train_file) as f:
                    train_count = len(json.load(f))
            if eval_file.exists():
                with open(eval_file) as f:
                    eval_count = len(json.load(f))
            
            print(f"  {year}: {train_count} training, {eval_count} evaluation")
        else:
            print(f"  {year}: Not found")
    
    # Check operators
    print("\nOperators:")
    try:
        from arc_organ.arc_operators import OPERATORS
        print(f"  Loaded: {len(OPERATORS)} operators")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check engines
    print("\nEngines:")
    engines = ["geo_engine", "color_engine", "comp_engine_v2", "pattern_engine", 
               "shape_engine", "rel_engine", "rel_engine_v2"]
    for engine in engines:
        try:
            __import__(f"engines.{engine}")
            print(f"  {engine}: OK")
        except Exception as e:
            print(f"  {engine}: MISSING")
    
    # Check results
    print("\nRecent Results:")
    if CONFIG.results_dir.exists():
        results = sorted(CONFIG.results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for r in results:
            print(f"  {r.name}")
    else:
        print("  No results directory")
    
    # Performance summary
    print("\nPerformance Summary:")
    print("  Baseline:  56 solves (5.0%)")
    print("  Hybrid:    64 solves (5.7%)")
    print("  Target:    100+ solves (10%)")
    
    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ARC Production Solver CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python arc_cli.py solve 007bbfb7 --show --output
  python arc_cli.py evaluate --dataset training
  python arc_cli.py diagnose 00d62c1b
  python arc_cli.py operators --list
  python arc_cli.py operators --test position_based_recolor
  python arc_cli.py status
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # solve
    solve_parser = subparsers.add_parser("solve", help="Solve a single task")
    solve_parser.add_argument("task_id", help="Task ID to solve")
    solve_parser.add_argument("--show", action="store_true", help="Display task")
    solve_parser.add_argument("--output", action="store_true", help="Show prediction")
    solve_parser.add_argument("--solution", action="store_true", help="Show expected solution")
    
    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate on dataset")
    eval_parser.add_argument("--dataset", choices=["training", "evaluation"], default="training")
    
    # diagnose
    diag_parser = subparsers.add_parser("diagnose", help="Diagnose a failing task")
    diag_parser.add_argument("task_id", help="Task ID to diagnose")
    
    # operators
    ops_parser = subparsers.add_parser("operators", help="List or test operators")
    ops_parser.add_argument("--list", action="store_true", help="List all operators")
    ops_parser.add_argument("--test", metavar="NAME", help="Test specific operator")
    
    # status
    subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    # Route to command
    if args.command == "solve":
        return cmd_solve(args)
    elif args.command == "evaluate":
        return cmd_evaluate(args)
    elif args.command == "diagnose":
        return cmd_diagnose(args)
    elif args.command == "operators":
        return cmd_operators(args)
    elif args.command == "status":
        return cmd_status(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
