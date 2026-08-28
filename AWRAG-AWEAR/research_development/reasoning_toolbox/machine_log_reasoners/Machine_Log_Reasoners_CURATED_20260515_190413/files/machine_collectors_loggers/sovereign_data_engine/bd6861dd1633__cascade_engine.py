"""
Cascade Engine Module - ACTUALLY FAST VERSION
Simple, optimized N-1-N processing that actually works
"""

import uuid
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import time

@dataclass
class CascadeResult:
    """Represents a result from cascade processing"""
    node_id: str
    node_type: str
    level: int
    position: int
    data: str
    processed_data: Any
    function_applied: str
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class CascadeEngine:
    """ACTUALLY FAST N-1-N cascade processing engine"""
    
    def __init__(self):
        self.results = []
        self.function_registry = {}
        self._register_default_functions()
        
        # Performance tracking
        self.stats = {
            'total_positions': 0,
            'processing_time': 0,
            'positions_per_second': 0
        }
    
    def _register_default_functions(self):
        """Register default processing functions"""
        self.function_registry = {
            'anchor_genome': self._anchor_genome_function,
            'bloom_genome': self._bloom_genome_function,
            'anchor_auto': self._anchor_auto_function,
            'bloom_auto': self._bloom_auto_function,
            'anchor_text': self._anchor_text_function,
            'bloom_text': self._bloom_text_function
        }
    
    def process(self, data: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process data through the cascade engine - FAST VERSION
        """
        start_time = time.time()
        
        # Clear previous state
        self.results = []
        
        print(f"🚀 Processing {len(data):,} characters with FAST engine...")
        
        left_width = config.get('left_width', 10)
        anchor_width = config.get('anchor_width', 1)
        right_width = config.get('right_width', 10)
        
        segment_size = left_width + anchor_width + right_width
        max_positions = len(data) - segment_size + 1
        
        if max_positions <= 0:
            print("❌ Data too small for configured segment size")
            return []
        
        # SIMPLE FAST PROCESSING - NO MULTIPROCESSING BULLSHIT
        results = []
        
        # Sample positions for speed (every 100th position for large files)
        step_size = max(1, max_positions // 1000) if len(data) > 10000 else 1
        positions_to_process = list(range(0, max_positions, step_size))
        
        print(f"📊 Processing {len(positions_to_process):,} positions (step size: {step_size})")
        
        processed_count = 0
        for i, pos in enumerate(positions_to_process):
            # Show progress every 100 positions
            if i % 100 == 0:
                progress = (i / len(positions_to_process)) * 100
                print(f"⚡ Progress: {progress:.1f}% ({i:,}/{len(positions_to_process):,})")
            
            # Extract segment
            segment = data[pos:pos + segment_size]
            if len(segment) < segment_size:
                break
            
            # Split into left-anchor-right
            left_data = segment[:left_width] if left_width > 0 else ""
            anchor_data = segment[left_width:left_width + anchor_width] if anchor_width > 0 else ""
            right_data = segment[left_width + anchor_width:] if right_width > 0 else ""
            
            # Process each part FAST
            if anchor_data:
                anchor_result = self._process_segment_fast('anchor', anchor_data, pos + left_width, config)
                if anchor_result:
                    results.append(anchor_result)
                    processed_count += 1
            
            if left_data:
                left_result = self._process_segment_fast('bloom', left_data, pos, config)
                if left_result:
                    results.append(left_result)
                    processed_count += 1
            
            if right_data:
                right_result = self._process_segment_fast('bloom', right_data, pos + left_width + anchor_width, config)
                if right_result:
                    results.append(right_result)
                    processed_count += 1
        
        # Calculate performance stats
        end_time = time.time()
        self.stats['processing_time'] = end_time - start_time
        self.stats['total_positions'] = processed_count
        self.stats['positions_per_second'] = processed_count / max(self.stats['processing_time'], 0.001)
        
        print(f"✅ Processing complete!")
        print(f"⚡ Time: {self.stats['processing_time']:.2f} seconds")
        print(f"📊 Processed: {processed_count:,} segments")
        print(f"🔥 Performance: {self.stats['positions_per_second']:,.0f} segments/second")
        
        return results
    
    def _process_segment_fast(self, segment_type: str, data: str, position: int, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single segment FAST"""
        if not data:
            return None
        
        # Determine which function to apply
        if segment_type == 'anchor':
            function_name = config.get('anchor_function', 'anchor_auto')
        else:  # bloom
            function_name = config.get('bloom_function', 'bloom_auto')
        
        # Apply function
        if function_name in self.function_registry:
            function = self.function_registry[function_name]
            processed_data, confidence = function(data, config)
        else:
            # Fallback to identity function
            processed_data = data
            confidence = 0.5
            function_name = 'identity'
        
        # Create result dictionary
        result = {
            'node_id': str(uuid.uuid4()),
            'node_type': segment_type,
            'level': 0,
            'position': position,
            'data': data,
            'processed_data': processed_data,
            'function_applied': function_name,
            'confidence': confidence,
            'metadata': {
                'data_length': len(data)
            }
        }
        
        return result
    
    # FAST processing functions
    def _anchor_text_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST text anchor processing"""
        if not data:
            return {'text': '', 'anchor_type': 'text'}, 0.0
        
        # Super fast text analysis
        is_letter = data.isalpha()
        is_digit = data.isdigit()
        is_punct = data in '.,!?;:"()[]{}' 
        is_space = data.isspace()
        
        result = {
            'text': data,
            'is_letter': is_letter,
            'is_digit': is_digit,
            'is_punctuation': is_punct,
            'is_space': is_space,
            'anchor_type': 'text'
        }
        
        confidence = 0.8 if is_letter else (0.6 if is_punct else 0.4)
        return result, confidence
    
    def _bloom_text_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST text bloom processing"""
        if not data:
            return {'text': '', 'bloom_type': 'text'}, 0.0
        
        # Super fast analysis
        word_count = len(data.split())
        char_count = len(data)
        has_space = ' ' in data
        has_punct = any(c in '.,!?;:"()[]{}' for c in data)
        
        result = {
            'text': data,
            'word_count': word_count,
            'character_count': char_count,
            'has_space': has_space,
            'has_punctuation': has_punct,
            'bloom_type': 'text'
        }
        
        confidence = 0.7 if word_count > 0 else 0.3
        return result, confidence
    
    def _anchor_auto_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST auto anchor processing"""
        if not data:
            return {'data': '', 'anchor_type': 'auto'}, 0.0
        
        # Super fast analysis
        unique_chars = len(set(data))
        total_chars = len(data)
        complexity = unique_chars / total_chars if total_chars > 0 else 0
        
        result = {
            'data': data,
            'unique_chars': unique_chars,
            'total_chars': total_chars,
            'complexity': complexity,
            'anchor_type': 'auto'
        }
        
        confidence = min(0.8, complexity * 2)
        return result, confidence
    
    def _bloom_auto_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST auto bloom processing"""
        if not data:
            return {'data': '', 'bloom_type': 'auto'}, 0.0
        
        # Super fast analysis
        unique_chars = len(set(data))
        total_chars = len(data)
        has_repeats = len(data) != len(set(data))
        
        result = {
            'data': data,
            'unique_chars': unique_chars,
            'total_chars': total_chars,
            'has_repeats': has_repeats,
            'bloom_type': 'auto'
        }
        
        confidence = 0.6 if has_repeats else 0.4
        return result, confidence
    
    def _anchor_genome_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST genomic anchor processing"""
        if not data:
            return {'sequence': '', 'anchor_type': 'genomic'}, 0.0
        
        # Super fast nucleotide analysis
        data_upper = data.upper()
        gc_count = data_upper.count('G') + data_upper.count('C')
        total_count = len(data)
        gc_content = gc_count / total_count if total_count > 0 else 0
        
        result = {
            'sequence': data,
            'gc_content': gc_content,
            'length': total_count,
            'anchor_type': 'genomic'
        }
        
        confidence = 0.8 if 0.3 <= gc_content <= 0.7 else 0.5
        return result, confidence
    
    def _bloom_genome_function(self, data: str, config: Dict[str, Any]) -> Tuple[Any, float]:
        """FAST genomic bloom processing"""
        if not data:
            return {'sequence': '', 'bloom_type': 'genomic'}, 0.0
        
        # Super fast genomic analysis
        data_upper = data.upper()
        has_cpg = 'CG' in data_upper
        has_poly_a = 'AAA' in data_upper
        has_poly_t = 'TTT' in data_upper
        
        result = {
            'sequence': data,
            'has_cpg_sites': has_cpg,
            'has_poly_a': has_poly_a,
            'has_poly_t': has_poly_t,
            'length': len(data),
            'bloom_type': 'genomic'
        }
        
        confidence = 0.7 if (has_cpg or has_poly_a or has_poly_t) else 0.5
        return result, confidence

