"""
Bloom Module
Handles bloom node processing with UUID assignment and advanced analytics
"""

import uuid
import json
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict
import statistics

class BloomModule:
    """Handles processing of bloom nodes in the cascade"""
    
    def __init__(self):
        self.bloom_registry = {}
        self.analytics_cache = {}
        self._register_default_bloom_functions()
    
    def _register_default_bloom_functions(self):
        """Register default bloom processing functions"""
        self.bloom_functions = {
            'bloom_genome': self._bloom_genome_advanced,
            'bloom_auto': self._bloom_auto_advanced,
            'bloom_text': self._bloom_text_advanced,
            'bloom_pattern': self._bloom_pattern_advanced,
            'bloom_frequency': self._bloom_frequency_advanced
        }
    
    def process_bloom_node(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a bloom node with UUID assignment
        
        Args:
            data: Input data for the bloom node
            node_info: Information about the node (position, level, etc.)
            config: Configuration parameters
            
        Returns:
            Processed bloom result with UUID
        """
        # Generate unique UUID for this bloom node
        bloom_uuid = str(uuid.uuid4())
        
        # Determine bloom function to use
        bloom_function_name = config.get('bloom_function', 'bloom_auto')
        
        if bloom_function_name in self.bloom_functions:
            bloom_function = self.bloom_functions[bloom_function_name]
        else:
            bloom_function = self.bloom_functions['bloom_auto']
        
        # Process the data
        processed_data, confidence, analytics = bloom_function(data, node_info, config)
        
        # Create bloom result
        bloom_result = {
            'bloom_uuid': bloom_uuid,
            'node_info': node_info,
            'input_data': data,
            'processed_data': processed_data,
            'confidence': confidence,
            'analytics': analytics,
            'function_used': bloom_function_name,
            'timestamp': self._get_timestamp(),
            'metadata': {
                'data_length': len(data),
                'processing_level': node_info.get('level', 0),
                'position': node_info.get('position', 0)
            }
        }
        
        # Cache for potential reuse
        self.bloom_registry[bloom_uuid] = bloom_result
        
        return bloom_result
    
    def _bloom_genome_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced genomic bloom processing"""
        # Nucleotide composition analysis
        composition = self._analyze_nucleotide_composition(data)
        
        # Pattern detection
        patterns = self._detect_genomic_patterns(data)
        
        # Structural analysis
        structure = self._analyze_genomic_structure(data)
        
        # Quality metrics
        quality = self._calculate_genomic_quality(data, composition, patterns)
        
        # Motif detection
        motifs = self._detect_motifs(data)
        
        processed_data = {
            'sequence': data,
            'composition': composition,
            'patterns': patterns,
            'structure': structure,
            'motifs': motifs,
            'quality_score': quality['overall_score'],
            'bloom_type': 'genomic_advanced'
        }
        
        analytics = {
            'gc_content': composition.get('gc_content', 0),
            'complexity_score': quality.get('complexity', 0),
            'pattern_density': len(patterns) / len(data) if data else 0,
            'motif_count': len(motifs),
            'entropy': quality.get('entropy', 0)
        }
        
        confidence = self._calculate_genomic_confidence(quality, patterns, motifs)
        
        return processed_data, confidence, analytics
    
    def _bloom_auto_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced auto-detection bloom processing"""
        # Character analysis
        char_analysis = self._analyze_characters(data)
        
        # Pattern detection
        patterns = self._detect_general_patterns(data)
        
        # Statistical analysis
        stats = self._calculate_statistics(data)
        
        # Entropy calculation
        entropy = self._calculate_entropy(data)
        
        # Data type detection
        detected_type = self._detect_data_type(data, char_analysis, patterns)
        
        processed_data = {
            'data': data,
            'detected_type': detected_type,
            'character_analysis': char_analysis,
            'patterns': patterns,
            'statistics': stats,
            'entropy': entropy,
            'bloom_type': 'auto_advanced'
        }
        
        analytics = {
            'data_type_confidence': detected_type.get('confidence', 0),
            'pattern_complexity': len(patterns) / len(data) if data else 0,
            'entropy_score': entropy,
            'unique_ratio': char_analysis.get('unique_ratio', 0)
        }
        
        confidence = self._calculate_auto_confidence(detected_type, patterns, entropy)
        
        return processed_data, confidence, analytics
    
    def _bloom_text_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced text bloom processing"""
        # Linguistic analysis
        linguistic = self._analyze_linguistic_features(data)
        
        # Semantic patterns
        semantic = self._detect_semantic_patterns(data)
        
        # Text quality metrics
        quality = self._calculate_text_quality(data, linguistic)
        
        processed_data = {
            'text': data,
            'linguistic_features': linguistic,
            'semantic_patterns': semantic,
            'quality_metrics': quality,
            'bloom_type': 'text_advanced'
        }
        
        analytics = {
            'readability_score': quality.get('readability', 0),
            'semantic_density': len(semantic) / len(data.split()) if data.split() else 0,
            'linguistic_complexity': linguistic.get('complexity', 0)
        }
        
        confidence = self._calculate_text_confidence(linguistic, semantic, quality)
        
        return processed_data, confidence, analytics
    
    def _bloom_pattern_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced pattern-focused bloom processing"""
        # Multi-scale pattern detection
        patterns = {
            'micro': self._detect_micro_patterns(data),
            'macro': self._detect_macro_patterns(data),
            'recursive': self._detect_recursive_patterns(data)
        }
        
        # Pattern relationships
        relationships = self._analyze_pattern_relationships(patterns)
        
        # Pattern evolution (if multiple levels available)
        evolution = self._analyze_pattern_evolution(data, node_info)
        
        processed_data = {
            'data': data,
            'multi_scale_patterns': patterns,
            'pattern_relationships': relationships,
            'pattern_evolution': evolution,
            'bloom_type': 'pattern_advanced'
        }
        
        analytics = {
            'pattern_diversity': len(set(str(p) for scale in patterns.values() for p in scale)),
            'relationship_strength': relationships.get('strength', 0),
            'evolution_score': evolution.get('score', 0)
        }
        
        confidence = self._calculate_pattern_confidence(patterns, relationships, evolution)
        
        return processed_data, confidence, analytics
    
    def _bloom_frequency_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced frequency-based bloom processing"""
        # Multi-level frequency analysis
        frequencies = {
            'character': self._analyze_character_frequencies(data),
            'ngram': self._analyze_ngram_frequencies(data),
            'word': self._analyze_word_frequencies(data) if ' ' in data else {}
        }
        
        # Frequency patterns
        freq_patterns = self._detect_frequency_patterns(frequencies)
        
        # Statistical distributions
        distributions = self._analyze_frequency_distributions(frequencies)
        
        processed_data = {
            'data': data,
            'frequencies': frequencies,
            'frequency_patterns': freq_patterns,
            'distributions': distributions,
            'bloom_type': 'frequency_advanced'
        }
        
        analytics = {
            'frequency_entropy': distributions.get('entropy', 0),
            'pattern_regularity': freq_patterns.get('regularity', 0),
            'distribution_skew': distributions.get('skew', 0)
        }
        
        confidence = self._calculate_frequency_confidence(frequencies, freq_patterns, distributions)
        
        return processed_data, confidence, analytics
    
    # Helper methods for genomic analysis
    def _analyze_nucleotide_composition(self, sequence: str) -> Dict[str, Any]:
        """Analyze nucleotide composition"""
        sequence = sequence.upper()
        composition = {'A': 0, 'T': 0, 'G': 0, 'C': 0, 'N': 0, 'other': 0}
        
        for char in sequence:
            if char in composition:
                composition[char] += 1
            else:
                composition['other'] += 1
        
        total = len(sequence)
        if total > 0:
            percentages = {k: (v / total) * 100 for k, v in composition.items()}
            gc_content = (composition['G'] + composition['C']) / total
            at_content = (composition['A'] + composition['T']) / total
        else:
            percentages = composition
            gc_content = at_content = 0
        
        return {
            'counts': composition,
            'percentages': percentages,
            'gc_content': gc_content,
            'at_content': at_content,
            'total_length': total
        }
    
    def _detect_genomic_patterns(self, sequence: str) -> List[Dict[str, Any]]:
        """Detect genomic patterns"""
        patterns = []
        
        # Tandem repeats
        for length in range(2, min(20, len(sequence) // 3)):
            for i in range(len(sequence) - length * 2):
                motif = sequence[i:i + length]
                if sequence[i + length:i + length * 2] == motif:
                    patterns.append({
                        'type': 'tandem_repeat',
                        'motif': motif,
                        'position': i,
                        'length': length,
                        'copies': 2
                    })
        
        # Palindromes
        for length in range(4, min(20, len(sequence) // 2)):
            for i in range(len(sequence) - length):
                substr = sequence[i:i + length]
                reverse_complement = self._reverse_complement(substr)
                if substr == reverse_complement:
                    patterns.append({
                        'type': 'palindrome',
                        'sequence': substr,
                        'position': i,
                        'length': length
                    })
        
        return patterns
    
    def _reverse_complement(self, sequence: str) -> str:
        """Get reverse complement of DNA sequence"""
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
        return ''.join(complement.get(base, base) for base in reversed(sequence.upper()))
    
    def _analyze_genomic_structure(self, sequence: str) -> Dict[str, Any]:
        """Analyze genomic structure"""
        # Sliding window analysis
        window_size = min(50, len(sequence) // 10) if len(sequence) > 10 else len(sequence)
        gc_windows = []
        
        for i in range(0, len(sequence) - window_size + 1, window_size // 2):
            window = sequence[i:i + window_size]
            gc_count = window.upper().count('G') + window.upper().count('C')
            gc_content = gc_count / len(window) if window else 0
            gc_windows.append(gc_content)
        
        return {
            'window_size': window_size,
            'gc_windows': gc_windows,
            'gc_variance': statistics.variance(gc_windows) if len(gc_windows) > 1 else 0,
            'gc_mean': statistics.mean(gc_windows) if gc_windows else 0
        }
    
    def _calculate_genomic_quality(self, sequence: str, composition: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate genomic quality metrics"""
        # Complexity based on nucleotide distribution
        total = composition['total_length']
        if total == 0:
            return {'overall_score': 0, 'complexity': 0, 'entropy': 0}
        
        # Calculate entropy
        entropy = 0
        for count in composition['counts'].values():
            if count > 0:
                p = count / total
                entropy -= p * (p.bit_length() - 1) if p > 0 else 0
        
        # Complexity score
        unique_chars = sum(1 for count in composition['counts'].values() if count > 0)
        complexity = unique_chars / 4.0  # Normalize by max possible nucleotides
        
        # Pattern diversity
        pattern_diversity = len(set(p['type'] for p in patterns)) / 3.0  # Normalize by known pattern types
        
        overall_score = (entropy + complexity + pattern_diversity) / 3.0
        
        return {
            'overall_score': overall_score,
            'complexity': complexity,
            'entropy': entropy,
            'pattern_diversity': pattern_diversity
        }
    
    def _detect_motifs(self, sequence: str) -> List[Dict[str, Any]]:
        """Detect known genomic motifs"""
        motifs = []
        
        # Common motifs
        known_motifs = {
            'TATA': r'TATAAA',
            'CAAT': r'CCAAT',
            'GC_box': r'GGGCGG',
            'start_codon': r'ATG',
            'stop_codon': r'(TAA|TAG|TGA)'
        }
        
        import re
        for motif_name, pattern in known_motifs.items():
            matches = list(re.finditer(pattern, sequence.upper()))
            for match in matches:
                motifs.append({
                    'name': motif_name,
                    'sequence': match.group(),
                    'position': match.start(),
                    'length': len(match.group())
                })
        
        return motifs
    
    def _calculate_genomic_confidence(self, quality: Dict[str, Any], patterns: List[Dict[str, Any]], motifs: List[Dict[str, Any]]) -> float:
        """Calculate confidence for genomic analysis"""
        base_confidence = quality.get('overall_score', 0) * 0.4
        pattern_confidence = min(0.3, len(patterns) * 0.05)
        motif_confidence = min(0.3, len(motifs) * 0.1)
        
        return min(1.0, base_confidence + pattern_confidence + motif_confidence)
    
    # Helper methods for general analysis
    def _analyze_characters(self, data: str) -> Dict[str, Any]:
        """Analyze character distribution"""
        char_counts = Counter(data)
        total = len(data)
        
        return {
            'total_characters': total,
            'unique_characters': len(char_counts),
            'character_frequencies': dict(char_counts.most_common(10)),
            'unique_ratio': len(char_counts) / total if total > 0 else 0,
            'most_common': char_counts.most_common(1)[0] if char_counts else None
        }
    
    def _detect_general_patterns(self, data: str) -> List[str]:
        """Detect general patterns in data"""
        patterns = []
        
        # Find repeated substrings
        for length in range(2, min(10, len(data) // 3)):
            seen = set()
            for i in range(len(data) - length + 1):
                substring = data[i:i + length]
                if substring in seen:
                    if substring not in patterns:
                        patterns.append(substring)
                else:
                    seen.add(substring)
        
        return patterns
    
    def _calculate_statistics(self, data: str) -> Dict[str, Any]:
        """Calculate basic statistics"""
        if not data:
            return {}
        
        char_codes = [ord(c) for c in data]
        
        return {
            'length': len(data),
            'mean_char_code': statistics.mean(char_codes),
            'median_char_code': statistics.median(char_codes),
            'char_code_variance': statistics.variance(char_codes) if len(char_codes) > 1 else 0
        }
    
    def _calculate_entropy(self, data: str) -> float:
        """Calculate Shannon entropy"""
        if not data:
            return 0
        
        char_counts = Counter(data)
        total = len(data)
        entropy = 0
        
        for count in char_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * (p.bit_length() - 1)
        
        return entropy
    
    def _detect_data_type(self, data: str, char_analysis: Dict[str, Any], patterns: List[str]) -> Dict[str, Any]:
        """Detect the type of data"""
        # Simple heuristics for data type detection
        if all(c.upper() in 'ATGCN' for c in data if c.isalpha()):
            return {'type': 'genomic', 'confidence': 0.9}
        elif data.replace(' ', '').replace('\n', '').replace('\t', '').isalnum():
            return {'type': 'text', 'confidence': 0.7}
        elif any(c.isdigit() for c in data):
            return {'type': 'mixed', 'confidence': 0.6}
        else:
            return {'type': 'unknown', 'confidence': 0.3}
    
    def _calculate_auto_confidence(self, detected_type: Dict[str, Any], patterns: List[str], entropy: float) -> float:
        """Calculate confidence for auto-detection"""
        type_confidence = detected_type.get('confidence', 0) * 0.4
        pattern_confidence = min(0.3, len(patterns) * 0.05)
        entropy_confidence = min(0.3, entropy / 4.0)  # Normalize entropy
        
        return min(1.0, type_confidence + pattern_confidence + entropy_confidence)
    
    # Additional helper methods would continue here...
    def _analyze_linguistic_features(self, text: str) -> Dict[str, Any]:
        """Analyze linguistic features of text"""
        words = text.split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            'avg_sentence_length': sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0,
            'complexity': len(set(words)) / len(words) if words else 0
        }
    
    def _detect_semantic_patterns(self, text: str) -> List[str]:
        """Detect semantic patterns in text"""
        # Simple semantic pattern detection
        patterns = []
        words = text.lower().split()
        
        # Look for repeated phrases
        for length in range(2, min(5, len(words))):
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i + length])
                if text.lower().count(phrase) > 1 and phrase not in patterns:
                    patterns.append(phrase)
        
        return patterns
    
    def _calculate_text_quality(self, text: str, linguistic: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate text quality metrics"""
        # Simple readability approximation
        avg_word_length = linguistic.get('avg_word_length', 0)
        avg_sentence_length = linguistic.get('avg_sentence_length', 0)
        
        # Flesch-like readability score (simplified)
        readability = max(0, 100 - (avg_word_length * 10 + avg_sentence_length * 2))
        
        return {
            'readability': readability / 100.0,  # Normalize to 0-1
            'coherence': linguistic.get('complexity', 0)
        }
    
    def _calculate_text_confidence(self, linguistic: Dict[str, Any], semantic: List[str], quality: Dict[str, Any]) -> float:
        """Calculate confidence for text analysis"""
        linguistic_confidence = min(0.4, linguistic.get('complexity', 0))
        semantic_confidence = min(0.3, len(semantic) * 0.1)
        quality_confidence = quality.get('readability', 0) * 0.3
        
        return min(1.0, linguistic_confidence + semantic_confidence + quality_confidence)
    
    # Pattern analysis methods
    def _detect_micro_patterns(self, data: str) -> List[str]:
        """Detect micro-scale patterns (2-5 characters)"""
        patterns = []
        for length in range(2, 6):
            for i in range(len(data) - length + 1):
                pattern = data[i:i + length]
                if data.count(pattern) > 1 and pattern not in patterns:
                    patterns.append(pattern)
        return patterns
    
    def _detect_macro_patterns(self, data: str) -> List[str]:
        """Detect macro-scale patterns (6+ characters)"""
        patterns = []
        for length in range(6, min(20, len(data) // 3)):
            for i in range(len(data) - length + 1):
                pattern = data[i:i + length]
                if data.count(pattern) > 1 and pattern not in patterns:
                    patterns.append(pattern)
        return patterns
    
    def _detect_recursive_patterns(self, data: str) -> List[Dict[str, Any]]:
        """Detect recursive/nested patterns"""
        # Simplified recursive pattern detection
        recursive_patterns = []
        
        for base_length in range(2, 8):
            for i in range(len(data) - base_length * 2):
                base_pattern = data[i:i + base_length]
                # Look for the pattern repeated with variations
                for j in range(i + base_length, len(data) - base_length):
                    if data[j:j + base_length] == base_pattern:
                        recursive_patterns.append({
                            'base_pattern': base_pattern,
                            'positions': [i, j],
                            'spacing': j - i
                        })
                        break
        
        return recursive_patterns
    
    def _analyze_pattern_relationships(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relationships between patterns"""
        # Simple relationship analysis
        all_patterns = []
        for scale_patterns in patterns.values():
            all_patterns.extend(scale_patterns)
        
        # Calculate overlap and similarity
        overlaps = 0
        total_comparisons = 0
        
        for i, p1 in enumerate(all_patterns):
            for p2 in all_patterns[i + 1:]:
                total_comparisons += 1
                if isinstance(p1, str) and isinstance(p2, str):
                    if p1 in p2 or p2 in p1:
                        overlaps += 1
        
        strength = overlaps / total_comparisons if total_comparisons > 0 else 0
        
        return {
            'strength': strength,
            'total_patterns': len(all_patterns),
            'overlapping_patterns': overlaps
        }
    
    def _analyze_pattern_evolution(self, data: str, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how patterns evolve across levels"""
        # Simplified evolution analysis
        level = node_info.get('level', 0)
        position = node_info.get('position', 0)
        
        # Evolution score based on level and position
        evolution_score = min(1.0, (level + 1) * 0.2 + position * 0.1)
        
        return {
            'score': evolution_score,
            'level': level,
            'position': position
        }
    
    def _calculate_pattern_confidence(self, patterns: Dict[str, Any], relationships: Dict[str, Any], evolution: Dict[str, Any]) -> float:
        """Calculate confidence for pattern analysis"""
        pattern_count = sum(len(p) for p in patterns.values())
        pattern_confidence = min(0.4, pattern_count * 0.02)
        relationship_confidence = relationships.get('strength', 0) * 0.3
        evolution_confidence = evolution.get('score', 0) * 0.3
        
        return min(1.0, pattern_confidence + relationship_confidence + evolution_confidence)
    
    # Frequency analysis methods
    def _analyze_character_frequencies(self, data: str) -> Dict[str, int]:
        """Analyze character frequencies"""
        return dict(Counter(data))
    
    def _analyze_ngram_frequencies(self, data: str) -> Dict[str, Dict[str, int]]:
        """Analyze n-gram frequencies"""
        ngrams = {}
        for n in range(2, 5):
            ngrams[f'{n}-gram'] = {}
            for i in range(len(data) - n + 1):
                ngram = data[i:i + n]
                ngrams[f'{n}-gram'][ngram] = ngrams[f'{n}-gram'].get(ngram, 0) + 1
        return ngrams
    
    def _analyze_word_frequencies(self, data: str) -> Dict[str, int]:
        """Analyze word frequencies"""
        words = data.split()
        return dict(Counter(words))
    
    def _detect_frequency_patterns(self, frequencies: Dict[str, Any]) -> Dict[str, Any]:
        """Detect patterns in frequency distributions"""
        # Analyze character frequency patterns
        char_freqs = frequencies.get('character', {})
        if char_freqs:
            most_common = max(char_freqs.values())
            least_common = min(char_freqs.values())
            regularity = 1.0 - (most_common - least_common) / most_common if most_common > 0 else 0
        else:
            regularity = 0
        
        return {
            'regularity': regularity,
            'distribution_type': 'uniform' if regularity > 0.8 else 'skewed'
        }
    
    def _analyze_frequency_distributions(self, frequencies: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze frequency distributions"""
        char_freqs = list(frequencies.get('character', {}).values())
        
        if not char_freqs:
            return {'entropy': 0, 'skew': 0}
        
        # Calculate entropy
        total = sum(char_freqs)
        entropy = 0
        for freq in char_freqs:
            if freq > 0:
                p = freq / total
                entropy -= p * (p.bit_length() - 1)
        
        # Calculate skew (simplified)
        mean_freq = statistics.mean(char_freqs)
        skew = sum((f - mean_freq) ** 3 for f in char_freqs) / len(char_freqs) if char_freqs else 0
        
        return {
            'entropy': entropy,
            'skew': skew,
            'mean_frequency': mean_freq
        }
    
    def _calculate_frequency_confidence(self, frequencies: Dict[str, Any], freq_patterns: Dict[str, Any], distributions: Dict[str, Any]) -> float:
        """Calculate confidence for frequency analysis"""
        freq_diversity = len(frequencies.get('character', {})) / 256.0  # Normalize by max possible chars
        pattern_confidence = freq_patterns.get('regularity', 0) * 0.3
        distribution_confidence = min(0.4, distributions.get('entropy', 0) / 8.0)  # Normalize entropy
        
        return min(1.0, freq_diversity * 0.3 + pattern_confidence + distribution_confidence)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def get_bloom_by_uuid(self, bloom_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve bloom result by UUID"""
        return self.bloom_registry.get(bloom_uuid)
    
    def get_all_bloom_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all bloom results"""
        return self.bloom_registry.copy()
    
    def register_custom_bloom_function(self, name: str, function):
        """Register a custom bloom function"""
        self.bloom_functions[name] = function

