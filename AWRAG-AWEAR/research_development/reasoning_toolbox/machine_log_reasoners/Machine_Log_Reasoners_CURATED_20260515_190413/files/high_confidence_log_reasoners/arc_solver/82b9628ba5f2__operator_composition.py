"""
Operator Composition Engine - Multi-Step Spatial Reasoning

This implements chaining of operators to solve complex transformations
that require multiple sequential steps.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from arc_organ.arc_operators import OPERATORS, merge_operator_params, ArcOperator


class OperatorComposition:
    """Represents a chain of operators applied sequentially"""
    
    def __init__(self, operators: List[ArcOperator], params_list: List[Dict]):
        self.operators = operators
        self.params_list = params_list
        self.name = " → ".join([op.name for op in operators])
    
    def apply(self, input_grid: np.ndarray) -> np.ndarray:
        """Apply operators sequentially"""
        result = input_grid
        for op, params in zip(self.operators, self.params_list):
            result = op.apply(result, params)
        return result
    
    def __repr__(self):
        return f"Composition({self.name})"


def try_2step_composition(train_pairs: List[Tuple[np.ndarray, np.ndarray]]) -> Optional[OperatorComposition]:
    """
    Try all 2-step operator compositions: op1 → op2
    
    For each pair (op1, op2):
    1. For each training example (input, output):
       - Test if op1 can analyze input → intermediate
       - Test if op2 can analyze intermediate → output
    2. If all examples work, merge parameters and validate with apply()
    """
    
    for op1 in OPERATORS:
        for op2 in OPERATORS:
            # Try this composition on all training examples
            params1_list = []
            params2_list = []
            valid = True
            
            for inp, expected_out in train_pairs:
                # Step 1: Try all possible intermediates via op1
                intermediate_found = False
                
                # Try op1's analyze on variations
                # For now, just try op1.apply with various param guesses
                # This is exploratory - we need op1 to transform input somehow
                
                # Strategy: Try op1 with extracted params from other examples
                # Or try op1's analyze between input and all possible states
                
                # For 2-step: We need to find intermediate such that:
                # op1(input) = intermediate AND op2(intermediate) = output
                
                # Brute force approach:
                # 1. Get all possible params for op1 from this input
                # 2. Apply op1 with those params → intermediate
                # 3. Try op2.analyze(intermediate, output)
                
                # This is expensive - need smarter approach
                # For now, skip if we can't efficiently search
                
                pass
            
            if not valid:
                continue
    
    return None


def try_operator_with_intermediate_search(
    op: ArcOperator,
    input_grid: np.ndarray,
    output_grid: np.ndarray,
    max_tries: int = 10
) -> Optional[Tuple[np.ndarray, Dict]]:
    """
    Try to find intermediate grid where:
    - op can transform input → intermediate
    - Returns (intermediate, params) if found
    """
    
    # Strategy 1: Try op.analyze(input, output) directly
    params = op.analyze(input_grid, output_grid)
    if params is not None:
        intermediate = op.apply(input_grid, params)
        if not np.array_equal(intermediate, output_grid):
            # Op produces a different transformation
            return (intermediate, params)
    
    return None


def find_2step_composition_smart(train_pairs: List[Tuple[np.ndarray, np.ndarray]]) -> Optional[OperatorComposition]:
    """
    Smart 2-step composition search:
    
    For each operator op1:
    1. Apply op1 to all training inputs (with analyze-derived params)
    2. Get intermediate grids
    3. For each operator op2:
       - Try op2.analyze(intermediate, expected_output) for all examples
       - If all work, we found a composition!
    """
    
    for op1 in OPERATORS:
        # Try op1 on first example to see what it does
        inp0, out0 = train_pairs[0]
        
        # Get params for op1 (try analyze with various targets)
        # We don't know the intermediate target, so try:
        # 1. op1.analyze(inp0, out0) - might give transformation
        # 2. If that produces something != out0, that's an intermediate
        
        params1_first = op1.analyze(inp0, out0)
        if params1_first is None:
            continue
        
        intermediate0 = op1.apply(inp0, params1_first)
        
        # If intermediate == output, op1 already solves it (not a composition)
        if np.array_equal(intermediate0, out0):
            continue
        
        # Now try to find op2 that goes intermediate → output
        for op2 in OPERATORS:
            # Try op2.analyze on all examples with intermediate
            params1_list = []
            params2_list = []
            all_valid = True
            
            for inp, expected_out in train_pairs:
                # Get params for op1 on this example
                # Problem: We used analyze(inp, out) but that's not right
                # We need analyze(inp, ???) where ??? is unknown intermediate
                
                # Better approach: Use same params1 from first example
                # This assumes op1 has same params across examples
                
                intermediate = op1.apply(inp, params1_first)
                
                # Now try op2.analyze(intermediate, expected_out)
                params2 = op2.analyze(intermediate, expected_out)
                if params2 is None:
                    all_valid = False
                    break
                
                params1_list.append(params1_first)
                params2_list.append(params2)
            
            if not all_valid:
                continue
            
            # Merge params
            merged1 = merge_operator_params(op1, params1_list)
            merged2 = merge_operator_params(op2, params2_list)
            
            if merged1 is None or merged2 is None:
                continue
            
            # Validate with apply
            valid = True
            for inp, expected_out in train_pairs:
                try:
                    intermediate = op1.apply(inp, merged1)
                    result = op2.apply(intermediate, merged2)
                    if not np.array_equal(result, expected_out):
                        valid = False
                        break
                except:
                    valid = False
                    break
            
            if valid:
                return OperatorComposition([op1, op2], [merged1, merged2])
    
    return None


def exhaustive_2step_search(train_pairs: List[Tuple[np.ndarray, np.ndarray]], verbose: bool = False) -> Optional[OperatorComposition]:
    """
    Exhaustive search for 2-step compositions with parameter exploration
    
    For each (op1, op2) pair:
    - Try to find params for op1 that create useful intermediates
    - Try to find params for op2 that complete the transformation
    """
    
    total_pairs = len(OPERATORS) * len(OPERATORS)
    checked = 0
    
    for op1 in OPERATORS:
        for op2 in OPERATORS:
            checked += 1
            if verbose and checked % 20 == 0:
                print(f"  Checking {checked}/{total_pairs}: {op1.name} → {op2.name}", end='\r')
            
            # For each training example, try to find valid params
            compositions_per_example = []
            
            for inp, expected_out in train_pairs:
                found = False
                
                # Strategy: Try op1 with various "intermediate targets"
                # We generate candidate intermediates by trying op1.analyze with different reference outputs
                
                # Approach 1: Try op1's natural transformation
                # Just apply op1 with params derived from analyzing input vs output
                params1_guess = op1.analyze(inp, expected_out)
                if params1_guess is not None:
                    intermediate = op1.apply(inp, params1_guess)
                    
                    # Check if this intermediate can reach output via op2
                    params2 = op2.analyze(intermediate, expected_out)
                    if params2 is not None:
                        # Validate
                        result = op2.apply(intermediate, params2)
                        if np.array_equal(result, expected_out):
                            compositions_per_example.append((params1_guess, params2))
                            found = True
                            break
                
                if not found:
                    break
            
            # Check if we found compositions for all examples
            if len(compositions_per_example) == len(train_pairs):
                # Try to merge parameters
                params1_list = [p[0] for p in compositions_per_example]
                params2_list = [p[1] for p in compositions_per_example]
                
                merged1 = merge_operator_params(op1, params1_list)
                merged2 = merge_operator_params(op2, params2_list)
                
                if merged1 is not None and merged2 is not None:
                    # Final validation
                    valid = True
                    for inp, expected_out in train_pairs:
                        try:
                            intermediate = op1.apply(inp, merged1)
                            result = op2.apply(intermediate, merged2)
                            if not np.array_equal(result, expected_out):
                                valid = False
                                break
                        except:
                            valid = False
                            break
                    
                    if valid:
                        if verbose:
                            print(f"\n✓ Found: {op1.name} → {op2.name}")
                        return OperatorComposition([op1, op2], [merged1, merged2])
    
    if verbose:
        print()
    return None


def test_task_with_composition(task_id: str, task_data: Dict, verbose: bool = True) -> Optional[OperatorComposition]:
    """Test if a task can be solved with 2-step composition"""
    
    train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
                   for ex in task_data['train']]
    
    if verbose:
        print(f"Testing {task_id} with 2-step composition...")
    
    composition = exhaustive_2step_search(train_pairs, verbose=verbose)
    
    if composition:
        if verbose:
            print(f"✓ Solved with: {composition.name}")
        return composition
    else:
        if verbose:
            print(f"✗ No 2-step composition found")
        return None


if __name__ == "__main__":
    # Test on ac2e8ecf
    with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
        data = json.load(f)
    
    task_id = 'ac2e8ecf'
    task = data[task_id]
    
    print(f"\n{'='*60}")
    print(f"Testing 2-Step Composition on {task_id}")
    print(f"{'='*60}\n")
    
    result = test_task_with_composition(task_id, task, verbose=True)
    
    if result:
        print(f"\n✓ SUCCESS: {result.name}")
        print(f"Parameters:")
        for i, (op, params) in enumerate(zip(result.operators, result.params_list), 1):
            print(f"  Step {i} ({op.name}): {params}")
    else:
        print(f"\n✗ No composition found")
        print("This task may require:")
        print("  - 3+ step composition")
        print("  - New primitive operators")
        print("  - Spatial reasoning primitives")
