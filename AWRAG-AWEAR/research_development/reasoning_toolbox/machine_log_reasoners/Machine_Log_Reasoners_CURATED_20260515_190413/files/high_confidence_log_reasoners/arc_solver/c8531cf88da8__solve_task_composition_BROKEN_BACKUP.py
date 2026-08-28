"""
Composition-First Solver

New solve pipeline that tries:
1. 2-step composition (with prior ranking if available)
2. Single operators (fallback)

This replaces the old brute-force single-operator search with
intelligent composition search.
"""

import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
import sys

# Import existing operator infrastructure
try:
    from arc_operators import OPERATORS, infer_rule_for_task
except ImportError:
    from .arc_operators import OPERATORS, infer_rule_for_task

# Import new composition infrastructure
try:
    from composition_engine import CompositionSearch, CompositeOperator
    from prior_selector import PriorSelector
except ImportError:
    from .composition_engine import CompositionSearch, CompositeOperator
    from .prior_selector import PriorSelector


class CompositionSolver:
    """
    Solver that prioritizes 2-step compositions over single operators.
    
    Uses prior selector for intelligent search if Math-DSL rules available.
    """
    
    def __init__(self, 
                 operators: List = None,
                 rule_db_path: str = None,
                 use_prior: bool = True):
        """
        Args:
            operators: List of ArcOperator instances (uses OPERATORS if None)
            rule_db_path: Path to Math-DSL rule database
            use_prior: Whether to use prior selector for ranking
        """
        self.operators = operators if operators is not None else OPERATORS
        self.composition_search = CompositionSearch(self.operators)
        
        self.prior_selector = None
        if use_prior and rule_db_path:
            self.prior_selector = PriorSelector(rule_db_path)
        
        print(f"CompositionSolver initialized:")
        print(f"  - Operators: {len(self.operators)}")
        print(f"  - Prior selector: {'enabled' if self.prior_selector else 'disabled'}")
        print(f"  - Possible 2-step chains: {len(self.operators) ** 2}")
    
    def solve(self, task: Dict) -> Optional[Dict]:
        """
        Attempt to solve an ARC task.
        
        Strategy:
        1. Try 2-step composition (ranked by prior if available)
        2. Fall back to single operators if composition fails
        
        Args:
            task: ARC task dict with 'train' and 'test' keys
        
        Returns:
            Solution dict with 'rule_type', 'operators', 'configs', 'test_outputs'
            or None if no solution found
        """
        # STEP 1: Try 2-step composition
        composition_result = self._try_composition(task)
        if composition_result:
            return composition_result
        
        # STEP 2: Fall back to single operators
        single_result = self._try_single_operators(task)
        if single_result:
            return single_result
        
        return None
    
    def _try_composition(self, task: Dict) -> Optional[Dict]:
        """
        Try to solve with 2-step operator composition.
        
        Args:
            task: ARC task dict
        
        Returns:
            Solution dict or None
        """
        # Get prior-ranked pairs if available
        prior_ranked = None
        if self.prior_selector:
            try:
                prior_ranked = self.prior_selector.get_top_n_pairs(task, self.operators, n=50)
            except Exception as e:
                print(f"Prior ranking failed: {e}")
        
        # Search for valid 2-step chain
        result = self.composition_search.find_best_2_step(task, prior_ranked=prior_ranked)
        
        if result is None:
            return None
        
        op1, op2, cfg1, cfg2 = result
        
        # Apply chain to test inputs
        test_outputs = []
        for test_input in task["test"]:
            inp = test_input["input"]
            
            try:
                # Apply op1
                intermediate = op1.apply(inp, cfg1)
                
                # Apply op2
                final = op2.apply(intermediate, cfg2)
                
                test_outputs.append(final.tolist())
            except Exception as e:
                print(f"Error applying chain to test input: {e}")
                return None
        
        return {
            "rule_type": "composition",
            "operators": [op1.name, op2.name],
            "configs": {
                op1.name: cfg1,
                op2.name: cfg2
            },
            "test_outputs": test_outputs
        }
    
    def _try_single_operators(self, task: Dict) -> Optional[Dict]:
        """
        Try to solve with single operators (fallback).
        
        Uses existing infer_rule_for_task logic.
        
        Args:
            task: ARC task dict
        
        Returns:
            Solution dict or None
        """
        train_pairs = task["train"]
        
        # Get prior-ranked operators if available
        if self.prior_selector:
            try:
                top_ops = self.prior_selector.get_top_n_ops(task, self.operators, n=15)
                # Try ranked operators first
                for op in top_ops:
                    result = self._try_single_operator(op, train_pairs, task["test"])
                    if result:
                        return result
            except Exception:
                pass
        
        # Fall back to trying all operators
        for op in self.operators:
            result = self._try_single_operator(op, train_pairs, task["test"])
            if result:
                return result
        
        return None
    
    def _try_single_operator(self, op, train_pairs: List[Dict], test_inputs: List[Dict]) -> Optional[Dict]:
        """Try a single operator on the task."""
        try:
            # Analyze on first training example
            first_ex = train_pairs[0]
            config = op.analyze(first_ex["input"], first_ex["output"])
            
            if config is None:
                return None
            
            # Validate on all training examples
            for pair in train_pairs:
                result = op.apply(pair["input"], config)
                if not np.array_equal(result, pair["output"]):
                    return None
            
            # Apply to test inputs
            test_outputs = []
            for test_input in test_inputs:
                output = op.apply(test_input["input"], config)
                test_outputs.append(output.tolist())
            
            return {
                "rule_type": "single",
                "operators": [op.name],
                "configs": {op.name: config},
                "test_outputs": test_outputs
            }
        
        except Exception:
            return None


def solve_task_with_composition(task: Dict, 
                                rule_db_path: str = None,
                                use_prior: bool = True) -> Optional[Dict]:
    """
    Convenience function to solve a single task with composition.
    
    Args:
        task: ARC task dict
        rule_db_path: Path to Math-DSL rules (optional)
        use_prior: Whether to use prior selector
    
    Returns:
        Solution dict or None
    """
    solver = CompositionSolver(rule_db_path=rule_db_path, use_prior=use_prior)
    return solver.solve(task)


def test_solver():
    """Quick test of composition solver."""
    print("Composition Solver loaded successfully!")
    print(f"Available operators: {len(OPERATORS)}")
    
    # Test initialization
    solver = CompositionSolver(use_prior=False)
    print("Solver initialized without prior")
    
    return True


if __name__ == "__main__":
    test_solver()
