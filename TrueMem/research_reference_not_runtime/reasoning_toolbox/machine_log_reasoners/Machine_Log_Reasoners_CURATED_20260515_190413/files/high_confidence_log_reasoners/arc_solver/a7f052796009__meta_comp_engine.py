"""
META-COMP-ENGINE: 3-Step Composition + Macro Execution

This extends the mixer to:
1. Try 3-step chains (29^3 = 24,389 combinations)
2. Execute macros from Math-DSL knowledge base
3. Use beam search to prune search space

Architecture:
- Try macros FIRST (fast path - use known solutions)
- Fallback to single ops (20 solves)
- Fallback to 2-step composition (1 solve)
- Fallback to 3-step composition (NEW - targeting +10-30 solves)

TARGET: 50-70 solves (5-7% coverage)
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import sys

# Add parent to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.mixer import CompositionMixer, PriorRanker


class MacroExecutor:
    """
    Executes known solution macros from Math-DSL knowledge base.
    
    Math-DSL format:
    {
        "task_id": "007bbfb7",
        "operators": ["self_masking_tiling"],
        "rule": "mathematical description..."
    }
    """
    
    def __init__(self, math_dsl_path: Path, operators: List):
        self.operators = {op.name: op for op in operators}
        self.macros = {}
        
        # Load Math-DSL rules (handle multi-line JSON)
        if math_dsl_path.exists():
            try:
                with open(math_dsl_path) as f:
                    content = f.read()
                    # Try parsing as multi-line JSON objects separated by newlines
                    # Split on }\n{ pattern to find object boundaries
                    entries = []
                    current_obj = ""
                    brace_count = 0
                    
                    for char in content:
                        current_obj += char
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0 and current_obj.strip():
                                try:
                                    rule = json.loads(current_obj.strip())
                                    self.macros[rule["task_id"]] = rule
                                except:
                                    pass
                                current_obj = ""
            except:
                pass  # If loading fails, just skip macros
        
        print(f"[OK] MacroExecutor loaded: {len(self.macros)} macros")
    
    def has_macro(self, task_id: str) -> bool:
        """Check if we have a known solution for this task."""
        return task_id in self.macros
    
    def execute_macro(self, task_id: str, task: Dict) -> Optional[Dict]:
        """
        Execute known macro solution for this task.
        
        Returns same format as mixer: 
        {"type": "macro", "operators": [...], "test_outputs": [...]}
        """
        if task_id not in self.macros:
            return None
        
        macro = self.macros[task_id]
        op_names = macro.get("operators", [])
        
        if not op_names:
            return None
        
        # Get operator instances
        ops = [self.operators.get(name) for name in op_names if name in self.operators]
        if len(ops) != len(op_names):
            return None  # Some operators not available
        
        train_examples = task.get("train", [])
        test_examples = task.get("test", [])
        
        if not train_examples:
            return None
        
        try:
            # Execute chain on training examples
            train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) 
                          for ex in train_examples]
            
            # Get configs by executing chain on first example
            configs = []
            inp0, out0 = train_pairs[0]
            
            if len(ops) == 1:
                # Single operator
                cfg = ops[0].analyze(inp0, out0)
                if cfg is None:
                    return None
                configs = [cfg]
                
                # Validate on all examples
                for inp, out in train_pairs:
                    result = ops[0].apply(inp, cfg)
                    if not np.array_equal(result, out):
                        return None
            
            else:
                # Multi-step chain - build intermediate states for all training examples
                # This is critical: we need to track what each op ACTUALLY produces
                all_intermediates = []
                
                for inp, out in train_pairs:
                    intermediates = [inp]  # Start with input
                    all_intermediates.append(intermediates)
                
                # Infer each operator's config by looking at what it needs to do
                for i, op in enumerate(ops):
                    # For each training example, what does this op need to transform?
                    example_states = []
                    for j, (inp, out) in enumerate(train_pairs):
                        current_state = all_intermediates[j][-1]  # Last intermediate
                        
                        if i == len(ops) - 1:
                            # Last op: should go from current_state to final output
                            target_state = out
                        else:
                            # Intermediate op: we don't know target yet, use full output for now
                            # The op will infer its own transformation
                            target_state = out
                        
                        example_states.append((current_state, target_state))
                    
                    # Analyze using FIRST example to get config
                    cfg = op.analyze(example_states[0][0], example_states[0][1])
                    if cfg is None:
                        return None
                    
                    configs.append(cfg)
                    
                    # Apply this op to all examples to get next intermediate state
                    for j in range(len(train_pairs)):
                        current_state = all_intermediates[j][-1]
                        next_state = op.apply(current_state, cfg)
                        all_intermediates[j].append(next_state)
                
                # Validate: final state should match output for all examples
                for j, (inp, out) in enumerate(train_pairs):
                    final_state = all_intermediates[j][-1]
                    if not np.array_equal(final_state, out):
                        return None
            
            # Apply to test inputs
            test_outputs = []
            for test_ex in test_examples:
                test_inp = np.array(test_ex["input"])
                result = test_inp
                for op, cfg in zip(ops, configs):
                    result = op.apply(result, cfg)
                test_outputs.append(result.tolist())
            
            return {
                "type": "macro",
                "operators": op_names,
                "configs": configs,
                "test_outputs": test_outputs
            }
        
        except Exception:
            return None


class MetaCompEngine:
    """
    META-COMP-ENGINE: The full composition orchestrator.
    
    Search order:
    1. Macros (known solutions from Math-DSL)
    2. COLOR-ENGINE (global color mapping - fast path)
    3. Single operators
    4. 2-step chains
    5. 3-step chains (NEW)
    """
    
    def __init__(self, operators: List, prior_ranker: Optional[PriorRanker] = None,
                 math_dsl_path: Optional[Path] = None,
                 use_color_engine: bool = True,
                 use_pattern_engine: bool = True,
                 use_comp_engine: bool = True):
        self.operators = operators
        self.prior_ranker = prior_ranker
        self.use_color_engine = use_color_engine
        self.use_pattern_engine = use_pattern_engine
        self.use_comp_engine = use_comp_engine
        
        # Initialize components
        self.mixer = CompositionMixer(operators, prior_ranker)
        self.macro_executor = MacroExecutor(math_dsl_path, operators) if math_dsl_path else None
        
        # Initialize COLOR-ENGINE Phase 1
        if use_color_engine:
            from arc_organ.color_engine import ColorEngine
            self.color_engine = ColorEngine(mapping_threshold=0.95)
        else:
            self.color_engine = None
        
        # Initialize PATTERN-ENGINE Phases 1-2
        if use_pattern_engine:
            from arc_organ.pattern_engine import PatternEngine
            self.pattern_engine = PatternEngine()
        else:
            self.pattern_engine = None
        
        # Initialize COMP-ENGINE Phase 1
        if use_comp_engine:
            from arc_organ.comp_engine import CompEngine
            self.comp_engine = CompEngine()
        else:
            self.comp_engine = None
        
        print(f"[OK] MetaCompEngine initialized: {len(operators)} operators, COLOR-ENGINE: {use_color_engine}, PATTERN-ENGINE: {use_pattern_engine}, COMP-ENGINE: {use_comp_engine}")
    
    def solve_task(self, task_id: str, task: Dict, 
                   task_features: Optional[Dict] = None,
                   try_3step: bool = False) -> Optional[Dict]:
        """
        Full solving pipeline with macro execution + 3-step search.
        
        Args:
            task_id: Task identifier for macro lookup
            task: Task dict with train/test
            task_features: Optional pre-computed features
            try_3step: Enable 3-step composition search (slow but powerful)
        
        Returns:
            Solution dict or None
        """
        # Step 1: Try macro (known solution) FIRST
        if self.macro_executor and self.macro_executor.has_macro(task_id):
            result = self.macro_executor.execute_macro(task_id, task)
            if result:
                return result
        
        # Step 2: Analyze patterns to guide search
        pattern_hints = None
        if self.pattern_engine:
            pattern_hints = self._analyze_patterns(task)
        
        # Step 3: Try COMP-ENGINE (masked tiling - fast path for specific patterns)
        if self.comp_engine:
            result = self._try_comp_engine(task)
            if result:
                return result
        
        # Step 4: Try COLOR-ENGINE (global color mapping - fast!)
        if self.color_engine:
            result = self._try_color_engine(task)
            if result:
                return result
        
        # Step 5: Try single operators + 2-step chains (via mixer)
        # Use pattern hints to filter/rank operators if available
        if pattern_hints and pattern_hints.get('operator_suggestions'):
            # TODO: Pass suggestions to mixer for guided search
            pass
        
        result = self.mixer.solve_task(task, task_features)
        if result:
            return result
        
        # Step 3: Try 3-step chains (NEW - expensive but powerful)
        if try_3step:
            result = self._try_3_step_composition(task, task_features)
            if result:
                return result
        
        return None
    
    def _try_comp_engine(self, task: Dict) -> Optional[Dict]:
        """
        Try COMP-ENGINE Phase 1: Masked tiling detection.
        
        If training examples show consistent masked tiling pattern,
        apply to test inputs.
        """
        train_examples = task.get("train", [])
        test_examples = task.get("test", [])
        
        if not train_examples or not test_examples:
            return None
        
        # Convert to numpy
        train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) 
                      for ex in train_examples]
        
        # Detect consistent masked tiling pattern
        hypothesis = self.comp_engine.analyze_training_examples(train_pairs)
        
        if hypothesis is None:
            return None
        
        # Got consistent pattern! Apply to test inputs
        test_predictions = []
        
        for test_ex in test_examples:
            test_input = np.array(test_ex["input"])
            
            # Apply masked tiling
            prediction = self.comp_engine.apply_masked_tiling(test_input, hypothesis)
            test_predictions.append(prediction.tolist())
        
        return {
            "task_id": task.get("task_id", "unknown"),
            "predictions": test_predictions,
            "operator_chain": [f"comp_engine_masked_tiling_{hypothesis.mask_type}"],
            "source": "comp_engine"
        }
    
    def _try_color_engine(self, task: Dict) -> Optional[Dict]:
        """
        Try COLOR-ENGINE Phase 1: Global color mapping detection.
        
        If all training examples have same shape transformation AND 
        consistent global color mapping, apply to test inputs.
        """
        train_examples = task.get("train", [])
        test_examples = task.get("test", [])
        
        if not train_examples or not test_examples:
            return None
        
        # Convert to numpy
        train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) 
                      for ex in train_examples]
        
        # Detect consistent color transformation
        hyps = self.color_engine.detect_color_transformations(train_pairs)
        
        if not hyps:
            return None
        
        # Got consistent mapping! Apply to test inputs
        mapping = hyps[0].mapping
        test_predictions = []
        
        for test_ex in test_examples:
            test_input = np.array(test_ex["input"])
            
            # Apply color map
            prediction = self.color_engine.apply_color_map(test_input, mapping)
            test_predictions.append(prediction.tolist())
        
        return {
            "task_id": task.get("task_id", "unknown"),
            "predictions": test_predictions,
            "operator_chain": ["color_engine_global_map"],
            "source": "color_engine"
        }
    
    def _analyze_patterns(self, task: Dict) -> Dict:
        """
        Analyze patterns in task using PATTERN-ENGINE.
        
        Returns hints for operator selection:
        - Detected symmetries
        - Tiling patterns
        - Suggested operators based on patterns
        """
        train_examples = task.get("train", [])
        if not train_examples:
            return {}
        
        hints = {
            'symmetries_input': [],
            'symmetries_output': [],
            'tiling_input': [],
            'tiling_output': [],
            'operator_suggestions': []
        }
        
        # Analyze first training example for patterns
        first_ex = train_examples[0]
        inp = np.array(first_ex['input'])
        out = np.array(first_ex['output'])
        
        # Detect symmetries
        sym_in = self.pattern_engine.detect_symmetry(inp)
        sym_out = self.pattern_engine.detect_symmetry(out)
        
        # Check if any symmetry detected (any boolean field is True)
        has_sym_in = any([sym_in.horizontal, sym_in.vertical, sym_in.diagonal_main, 
                          sym_in.diagonal_anti, sym_in.rotational_90, sym_in.rotational_180])
        has_sym_out = any([sym_out.horizontal, sym_out.vertical, sym_out.diagonal_main,
                           sym_out.diagonal_anti, sym_out.rotational_90, sym_out.rotational_180])
        
        if has_sym_in:
            hints['symmetries_input'].append(sym_in)
        if has_sym_out:
            hints['symmetries_output'].append(sym_out)
            
        # Detect tiling
        tiling_in = self.pattern_engine.detect_global_tiling(inp)
        tiling_out = self.pattern_engine.detect_global_tiling(out)
        
        if tiling_in:
            hints['tiling_input'] = tiling_in
        if tiling_out:
            hints['tiling_output'] = tiling_out
        
        # Generate operator suggestions based on patterns
        if has_sym_out and not has_sym_in:
            hints['operator_suggestions'].append('symmetry_completion')
        
        if tiling_out and not tiling_in:
            hints['operator_suggestions'].extend(['tiling_expand', 'block_expansion', 'repeat_operator'])
        
        if tiling_in and tiling_out:
            # Both have tiling - might be tiling transformation
            hints['operator_suggestions'].append('self_masking_tiling')
        
        return hints
    
    def _try_3_step_composition(self, task: Dict, 
                               task_features: Optional[Dict]) -> Optional[Dict]:
        """
        Try 3-step operator chains: op1 -> op2 -> op3.
        
        This is 29^3 = 24,389 combinations. We use smart pruning:
        1. Try operators ranked by prior (if available)
        2. Skip chains where intermediate steps already solve the task
        3. Limit to top N candidates per step
        """
        train_examples = task.get("train", [])
        test_examples = task.get("test", [])
        
        if not train_examples:
            return None
        
        train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) 
                      for ex in train_examples]
        
        # Get ranked operators (or use all)
        if self.prior_ranker and task_features:
            ranked_ops = self.prior_ranker.rank_operators(task_features, self.operators, k=20)
        else:
            ranked_ops = self.operators
        
        # Limit search space: try top 10 operators per position
        top_ops = ranked_ops[:10]
        
        # Try all 3-step combinations (limited to top_ops = 10^3 = 1000 chains)
        for op1 in top_ops:
            for op2 in top_ops:
                if op1 == op2:
                    continue
                
                for op3 in top_ops:
                    if op3 == op1 or op3 == op2:
                        continue
                    
                    try:
                        result = self._test_3_step_chain(op1, op2, op3, 
                                                        train_pairs, test_examples)
                        if result:
                            return result
                    except Exception:
                        continue
        
        return None
    
    def _test_3_step_chain(self, op1, op2, op3, 
                          train_pairs: List[Tuple],
                          test_examples: List) -> Optional[Dict]:
        """Test if op1 -> op2 -> op3 solves the task."""
        try:
            # Get op1 config
            inp0, out0 = train_pairs[0]
            cfg1 = op1.analyze(inp0, out0)
            if cfg1 is None:
                return None
            
            # Apply op1
            int1 = op1.apply(inp0, cfg1)
            if np.array_equal(int1, out0):
                return None  # Already solved, not a 3-step
            
            # Get op2 config
            cfg2 = op2.analyze(int1, out0)
            if cfg2 is None:
                return None
            
            # Apply op2
            int2 = op2.apply(int1, cfg2)
            if np.array_equal(int2, out0):
                return None  # Solved in 2 steps, not 3
            
            # Get op3 config
            cfg3 = op3.analyze(int2, out0)
            if cfg3 is None:
                return None
            
            # Validate full chain on ALL training examples
            for inp, out in train_pairs:
                step1 = op1.apply(inp, cfg1)
                step2 = op2.apply(step1, cfg2)
                step3 = op3.apply(step2, cfg3)
                if not np.array_equal(step3, out):
                    return None
            
            # Apply to test inputs
            test_outputs = []
            for test_ex in test_examples:
                test_inp = np.array(test_ex["input"])
                step1 = op1.apply(test_inp, cfg1)
                step2 = op2.apply(step1, cfg2)
                step3 = op3.apply(step2, cfg3)
                test_outputs.append(step3.tolist())
            
            return {
                "type": "composition_3step",
                "operators": [op1.name, op2.name, op3.name],
                "configs": [cfg1, cfg2, cfg3],
                "test_outputs": test_outputs
            }
        
        except Exception:
            return None


def main():
    """Test MetaCompEngine on training set."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from arc_organ.arc_operators import OPERATORS
    from arc_organ.feature_extractor import FeatureExtractor
    
    print("="*70)
    print("META-COMP-ENGINE TEST")
    print("="*70)
    print()
    
    # Load components
    feature_db_path = Path(__file__).parent.parent / "training_feature_database.json"
    math_dsl_path = Path(__file__).parent.parent / "arc_transformation_rules_math_dsl.jsonl"
    
    prior_ranker = PriorRanker(feature_db_path) if feature_db_path.exists() else None
    
    # Initialize engine
    engine = MetaCompEngine(OPERATORS, prior_ranker, math_dsl_path)
    
    # Load test tasks
    data_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(data_path) as f:
        challenges = json.load(f)
    
    extractor = FeatureExtractor()
    
    # Test on first 10 tasks
    for task_id in list(challenges.keys())[:10]:
        task = challenges[task_id]
        features = extractor.extract(task)
        
        result = engine.solve_task(task_id, task, features, try_3step=False)
        if result:
            op_str = " -> ".join(result["operators"])
            print(f"[{result['type']:15s}] {task_id}: {op_str}")
        else:
            print(f"[FAILED         ] {task_id}")


if __name__ == "__main__":
    main()
