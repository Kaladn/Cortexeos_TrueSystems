"""
Composition Solver — Layer 1

Uses META-COMP-ENGINE with COLOR-ENGINE integration.
Only runs on tasks that baseline solver fails.

Adds new solves on top of baseline without regression risk.
"""
import numpy as np
from typing import Optional, Dict, List
from pathlib import Path
import sys

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.meta_comp_engine import MetaCompEngine


class CompositionSolver:
    """
    Layer 1: Multi-step composition solver using META-COMP-ENGINE.
    
    Features:
    - COLOR-ENGINE Phase 1: Global color mappings (fast path)
    - Macro execution (known Math-DSL solutions)
    - Single operators
    - 2-step compositions
    - 3-step compositions (optional)
    
    Performance: 2 baseline + COLOR-ENGINE unlocks (target: +2-5)
    """
    
    def __init__(self, operators: List):
        """
        Args:
            operators: List of ArcOperator instances
        """
        self.operators = operators
        
        # Initialize META-COMP-ENGINE with all engines enabled
        math_dsl_path = Path(__file__).parent.parent / "manual_math_dsl_complete.jsonl"
        self.meta_engine = MetaCompEngine(
            operators=operators,
            prior_ranker=None,
            math_dsl_path=math_dsl_path if math_dsl_path.exists() else None,
            use_color_engine=True,    # Enable COLOR-ENGINE Phase 1
            use_pattern_engine=True,  # Enable PATTERN-ENGINE Phases 1-2
            use_comp_engine=True      # Enable COMP-ENGINE Phase 1
        )
    
    def solve(self, task: Dict) -> Optional[Dict]:
        """
        Solve task using META-COMP-ENGINE with COLOR-ENGINE.
        
        Execution order:
        1. Macros (known solutions from Math-DSL)
        2. COMP-ENGINE Phase 1 (masked tiling)
        3. COLOR-ENGINE Phase 1 (global color mappings)
        4. Single operators
        5. 2-step compositions
        
        Args:
            task: ARC task dict with 'train' and 'test' keys
        
        Returns:
            Solution dict with operator chain and test outputs, or None
        """
        # Use META-COMP-ENGINE (includes all features)
        result = self.meta_engine.solve_task(
            task_id=task.get('task_id', 'unknown'),
            task=task,
            task_features=None,
            try_3step=False  # Keep 3-step disabled for production
        )
        
        if result:
            # Handle both formats: mixer returns "operators", color_engine returns "operator_chain"
            operators = result.get('operator_chain', result.get('operators', []))
            
            # Convert to expected format
            return {
                "rule_type": "composition" if len(operators) > 1 else "single",
                "operators": operators,
                "configs": {},  # META-COMP-ENGINE doesn't expose configs
                "test_outputs": result.get('predictions', result.get('test_outputs', []))
            }
        
        return None
