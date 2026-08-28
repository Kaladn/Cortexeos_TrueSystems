"""
Baseline Solver — Layer 0

Original single-operator solver that achieves 56/1120 solves.
Uses permissive per-example testing (no config merging).

This is the SACRED baseline - modifications require careful validation.
"""
import numpy as np
from typing import Optional, Dict, List


class BaselineSolver:
    """
    Layer 0: Single-operator baseline solver.
    
    Tests each operator independently on all training examples.
    More permissive than infer_rule_for_task (no config merging).
    
    Performance: 56/1120 tasks (5.0%)
    """
    
    def __init__(self, operators: List):
        """
        Args:
            operators: List of ArcOperator instances
        """
        self.operators = operators
    
    def _test_operator_on_task(self, task_data: Dict, operator) -> bool:
        """
        Test if operator solves ALL training examples.
        
        This is the original baseline logic that produces 56 solves.
        Each training example is tested independently.
        
        Args:
            task_data: Task dict with 'train' key
            operator: ArcOperator instance
        
        Returns:
            True if operator solves all training examples
        """
        try:
            for example in task_data['train']:
                inp = np.array(example['input'])
                expected = np.array(example['output'])
                
                params = operator.analyze(inp, expected)
                if params is None:
                    return False
                
                result = operator.apply(inp, params)
                if result is None or not np.array_equal(result, expected):
                    return False
            return True
        except:
            return False
    
    def solve(self, task: Dict) -> Optional[Dict]:
        """
        Solve task using single operators.
        
        Args:
            task: ARC task dict with 'train' and 'test' keys
        
        Returns:
            Solution dict with operator name and test outputs, or None
        """
        # Try all operators in order
        for operator in self.operators:
            if self._test_operator_on_task(task, operator):
                # Found working operator - apply to test inputs
                test_outputs = []
                
                try:
                    for test_ex in task['test']:
                        inp = np.array(test_ex['input'])
                        
                        # Get params from first training example
                        train_inp = np.array(task['train'][0]['input'])
                        train_out = np.array(task['train'][0]['output'])
                        params = operator.analyze(train_inp, train_out)
                        
                        if params is None:
                            return None
                        
                        result = operator.apply(inp, params)
                        test_outputs.append(result.tolist() if result is not None else None)
                    
                    return {
                        "rule_type": "single",
                        "operator": operator.name,
                        "test_outputs": test_outputs
                    }
                except:
                    return None
        
        return None
