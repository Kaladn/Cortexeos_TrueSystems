"""
Global Scan Module
Performs pre-analysis on massive datasets to identify patterns
"""

import random
import statistics
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict

class GlobalScanner:
    """Performs global scanning and pattern detection on large datasets"""
    
    def __init__(self):
        self.patterns = {}
        self.statistics = {}
        self.recommendations = {}
    
    def perform_global_scan(self, data: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform global scan on dataset
        
        Args:
            data: Input data string
            config: Scan configuration
            
        Returns:
            Scan results and recommendations
        """
        print("\n--- Starting Global Scan ---")
        
        sample_size = config.get('scan_sample_size', 10000)
        window_size = config.get('scan_window_size', 100)
        threshold = config.get('pattern_threshold', 0.1)
        
        # Sample data if too large
        if len(data) > sample_size:
            print(f"Sampling {sample_size} characters from {len(data)} total characters")
            data_sample = self._sample_data(data, sample_size)
        else:
            data_sample = data
        
        # Perform various analyses
        results = {
            'data_length': len(data),
            'sample_length': len(data_sample),
            'character_analysis': self._analyze_characters(data_sample),
            'pattern_analysis': self._analyze_patterns(data_sample, window_size),
            'entropy_analysis': self._analyze_entropy(data_sample, window_size),
            'repetition_analysis': self._analyze_repetitions(data_sample),
            'recommendations': self._generate_recommendations(data_sample, threshold)
        }
        
        self._print_scan_results(results)
        return results
    
    def _sample_data(self, data: str, sample_size: int) -> str:
        """Sample data using multiple strategies"""
        if len(data) <= sample_size:
            return data
        
        # Use multiple sampling strategies
        strategies = [
            self._random_sample,
            self._systematic_sample,
            self._stratified_sample
        ]
        
        samples = []
        chunk_size = sample_size // len(strategies)
        
        for strategy in strategies:
            sample = strategy(data, chunk_size)
            samples.append(sample)
        
        return ''.join(samples)
    
    def _random_sample(self, data: str, size: int) -> str:
        """Random sampling"""
        if len(data) <= size:
            return data
        indices = random.sample(range(len(data)), size)
        return ''.join(data[i] for i in sorted(indices))
    
    def _systematic_sample(self, data: str, size: int) -> str:
        """Systematic sampling"""
        if len(data) <= size:
            return data
        step = len(data) // size
        return ''.join(data[i] for i in range(0, len(data), step))[:size]
    
    def _stratified_sample(self, data: str, size: int) -> str:
        """Stratified sampling by position"""
        if len(data) <= size:
            return data
        
        # Divide data into strata (beginning, middle, end)
        third = len(data) // 3
        strata = [
            data[:third],
            data[third:2*third],
            data[2*third:]
        ]
        
        samples = []
        per_stratum = size // len(strata)
        
        for stratum in strata:
            if len(stratum) <= per_stratum:
                samples.append(stratum)
            else:
                step = len(stratum) // per_stratum
                samples.append(''.join(stratum[i] for i in range(0, len(stratum), step))[:per_stratum])
        
        return ''.join(samples)
    
    def _analyze_characters(self, data: str) -> Dict[str, Any]:
        """Analyze character distribution"""
        char_counts = Counter(data)
        total_chars = len(data)
        
        return {
            'total_characters': total_chars,
            'unique_characters': len(char_counts),
            'character_frequencies': dict(char_counts.most_common(10)),
            'character_distribution': {char: count/total_chars for char, count in char_counts.items()},
            'most_common': char_counts.most_common(1)[0] if char_counts else None
        }
    
    def _analyze_patterns(self, data: str, window_size: int) -> Dict[str, Any]:
        """Analyze patterns in data"""
        patterns = defaultdict(int)
        
        # Analyze n-grams of various sizes
        ngram_analysis = {}
        for n in range(2, min(6, window_size + 1)):
            ngrams = [data[i:i+n] for i in range(len(data) - n + 1)]
            ngram_counts = Counter(ngrams)
            ngram_analysis[f'{n}-grams'] = {
                'total': len(ngrams),
                'unique': len(ngram_counts),
                'most_common': ngram_counts.most_common(5)
            }
        
        return {
            'ngram_analysis': ngram_analysis,
            'pattern_density': self._calculate_pattern_density(data, window_size)
        }
    
    def _analyze_entropy(self, data: str, window_size: int) -> Dict[str, Any]:
        """Analyze entropy across data"""
        import math
        
        # Calculate overall entropy
        char_counts = Counter(data)
        total = len(data)
        entropy = -sum((count/total) * math.log2(count/total) for count in char_counts.values())
        
        # Calculate windowed entropy
        window_entropies = []
        for i in range(0, len(data) - window_size + 1, window_size // 2):
            window = data[i:i + window_size]
            window_counts = Counter(window)
            window_total = len(window)
            if window_total > 0:
                window_entropy = -sum((count/window_total) * math.log2(count/window_total) 
                                    for count in window_counts.values())
                window_entropies.append(window_entropy)
        
        return {
            'overall_entropy': entropy,
            'windowed_entropies': window_entropies,
            'entropy_variance': statistics.variance(window_entropies) if len(window_entropies) > 1 else 0,
            'low_entropy_regions': [i for i, e in enumerate(window_entropies) if e < entropy * 0.8]
        }
    
    def _analyze_repetitions(self, data: str) -> Dict[str, Any]:
        """Analyze repetitive patterns"""
        # Find tandem repeats
        repeats = {}
        for length in range(2, min(20, len(data) // 10)):
            for i in range(len(data) - length * 2):
                pattern = data[i:i + length]
                if data[i + length:i + length * 2] == pattern:
                    if pattern not in repeats:
                        repeats[pattern] = []
                    repeats[pattern].append(i)
        
        return {
            'tandem_repeats': {pattern: len(positions) for pattern, positions in repeats.items()},
            'repeat_density': len(repeats) / len(data) if data else 0
        }
    
    def _calculate_pattern_density(self, data: str, window_size: int) -> List[float]:
        """Calculate pattern density across windows"""
        densities = []
        for i in range(0, len(data) - window_size + 1, window_size // 2):
            window = data[i:i + window_size]
            unique_chars = len(set(window))
            density = unique_chars / len(window) if window else 0
            densities.append(density)
        return densities
    
    def _generate_recommendations(self, data: str, threshold: float) -> Dict[str, Any]:
        """Generate recommendations for N-1-N configuration"""
        char_analysis = self._analyze_characters(data)
        
        # Recommend anchor width based on most common patterns
        anchor_width = 1  # Default
        if char_analysis['unique_characters'] < 10:
            anchor_width = 2  # More specific anchor for low diversity
        
        # Recommend left/right widths based on pattern analysis
        data_length = len(data)
        if data_length < 1000:
            left_width = right_width = min(10, data_length // 10)
        elif data_length < 10000:
            left_width = right_width = min(50, data_length // 100)
        else:
            left_width = right_width = min(100, data_length // 1000)
        
        # Recommend cascade depth based on data complexity
        unique_ratio = char_analysis['unique_characters'] / len(data) if data else 0
        if unique_ratio > 0.8:
            cascade_depth = 2  # High diversity - shallow cascade
        elif unique_ratio > 0.5:
            cascade_depth = 3  # Medium diversity
        else:
            cascade_depth = 4  # Low diversity - deeper cascade
        
        return {
            'recommended_left_width': left_width,
            'recommended_right_width': right_width,
            'recommended_anchor_width': anchor_width,
            'recommended_cascade_depth': cascade_depth,
            'confidence_score': self._calculate_confidence(char_analysis),
            'reasoning': self._generate_reasoning(char_analysis, unique_ratio)
        }
    
    def _calculate_confidence(self, char_analysis: Dict[str, Any]) -> float:
        """Calculate confidence in recommendations"""
        # Simple confidence based on data characteristics
        total_chars = char_analysis['total_characters']
        unique_chars = char_analysis['unique_characters']
        
        if total_chars < 100:
            return 0.3  # Low confidence for small datasets
        elif total_chars < 1000:
            return 0.6  # Medium confidence
        else:
            return 0.9  # High confidence for large datasets
    
    def _generate_reasoning(self, char_analysis: Dict[str, Any], unique_ratio: float) -> List[str]:
        """Generate reasoning for recommendations"""
        reasoning = []
        
        if unique_ratio > 0.8:
            reasoning.append("High character diversity suggests shallow cascade depth")
        elif unique_ratio < 0.2:
            reasoning.append("Low character diversity suggests deeper cascade depth")
        
        if char_analysis['total_characters'] > 10000:
            reasoning.append("Large dataset allows for wider N-1-N windows")
        else:
            reasoning.append("Small dataset requires narrower N-1-N windows")
        
        return reasoning
    
    def _print_scan_results(self, results: Dict[str, Any]) -> None:
        """Print formatted scan results"""
        print("\n--- Global Scan Results ---")
        print(f"Data Length: {results['data_length']:,} characters")
        print(f"Sample Length: {results['sample_length']:,} characters")
        
        char_analysis = results['character_analysis']
        print(f"\nCharacter Analysis:")
        print(f"  Unique Characters: {char_analysis['unique_characters']}")
        print(f"  Most Common: {char_analysis['most_common']}")
        
        recommendations = results['recommendations']
        print(f"\nRecommendations (Confidence: {recommendations['confidence_score']:.1%}):")
        print(f"  Left Width: {recommendations['recommended_left_width']}")
        print(f"  Anchor Width: {recommendations['recommended_anchor_width']}")
        print(f"  Right Width: {recommendations['recommended_right_width']}")
        print(f"  Cascade Depth: {recommendations['recommended_cascade_depth']}")
        
        if recommendations['reasoning']:
            print(f"  Reasoning:")
            for reason in recommendations['reasoning']:
                print(f"    - {reason}")
    
    def create_targeted_config(self, scan_results: Dict[str, Any], data_file: str) -> Dict[str, Any]:
        """Create targeted configuration from scan results"""
        recommendations = scan_results['recommendations']
        
        config = {
            'data_type': 'auto_detected',
            'data_file': data_file,
            'left_width': recommendations['recommended_left_width'],
            'right_width': recommendations['recommended_right_width'],
            'anchor_width': recommendations['recommended_anchor_width'],
            'cascade_depth': recommendations['recommended_cascade_depth'],
            'anchor_function': 'anchor_auto',
            'bloom_function': 'bloom_auto',
            'scan_results': scan_results
        }
        
        return config

