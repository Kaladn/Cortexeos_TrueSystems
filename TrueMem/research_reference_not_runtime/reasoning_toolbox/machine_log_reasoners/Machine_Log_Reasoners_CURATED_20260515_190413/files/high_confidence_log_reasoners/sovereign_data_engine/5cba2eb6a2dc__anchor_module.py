"""
Anchor Module
Handles anchor node processing with UUID assignment and specialized analytics
"""

import uuid
import json
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict
import statistics

class AnchorModule:
    """Handles processing of anchor nodes in the cascade"""
    
    def __init__(self):
        self.anchor_registry = {}
        self.anchor_relationships = defaultdict(list)
        self._register_default_anchor_functions()
    
    def _register_default_anchor_functions(self):
        """Register default anchor processing functions"""
        self.anchor_functions = {
            'anchor_genome': self._anchor_genome_advanced,
            'anchor_auto': self._anchor_auto_advanced,
            'anchor_text': self._anchor_text_advanced,
            'anchor_structural': self._anchor_structural_advanced,
            'anchor_consensus': self._anchor_consensus_advanced
        }
    
    def process_anchor_node(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an anchor node with UUID assignment
        
        Args:
            data: Input data for the anchor node
            node_info: Information about the node (position, level, etc.)
            config: Configuration parameters
            
        Returns:
            Processed anchor result with UUID
        """
        # Generate unique UUID for this anchor node
        anchor_uuid = str(uuid.uuid4())
        
        # Determine anchor function to use
        anchor_function_name = config.get('anchor_function', 'anchor_auto')
        
        if anchor_function_name in self.anchor_functions:
            anchor_function = self.anchor_functions[anchor_function_name]
        else:
            anchor_function = self.anchor_functions['anchor_auto']
        
        # Process the data
        processed_data, confidence, analytics = anchor_function(data, node_info, config)
        
        # Create anchor result
        anchor_result = {
            'anchor_uuid': anchor_uuid,
            'node_info': node_info,
            'input_data': data,
            'processed_data': processed_data,
            'confidence': confidence,
            'analytics': analytics,
            'function_used': anchor_function_name,
            'timestamp': self._get_timestamp(),
            'metadata': {
                'data_length': len(data),
                'processing_level': node_info.get('level', 0),
                'position': node_info.get('position', 0),
                'anchor_strength': self._calculate_anchor_strength(data, processed_data)
            }
        }
        
        # Cache for potential reuse and relationship tracking
        self.anchor_registry[anchor_uuid] = anchor_result
        self._track_anchor_relationships(anchor_uuid, anchor_result)
        
        return anchor_result
    
    def _anchor_genome_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced genomic anchor processing"""
        # Core sequence analysis
        core_analysis = self._analyze_genomic_core(data)
        
        # Functional prediction
        function_prediction = self._predict_genomic_function(data, core_analysis)
        
        # Conservation analysis
        conservation = self._analyze_conservation(data)
        
        # Regulatory potential
        regulatory = self._analyze_regulatory_potential(data)
        
        # Structural features
        structure = self._analyze_genomic_anchor_structure(data)
        
        processed_data = {
            'sequence': data,
            'core_analysis': core_analysis,
            'function_prediction': function_prediction,
            'conservation_score': conservation,
            'regulatory_potential': regulatory,
            'structural_features': structure,
            'anchor_type': 'genomic_advanced'
        }
        
        analytics = {
            'functional_confidence': function_prediction.get('confidence', 0),
            'conservation_level': conservation.get('score', 0),
            'regulatory_strength': regulatory.get('strength', 0),
            'structural_stability': structure.get('stability', 0),
            'overall_importance': self._calculate_genomic_importance(core_analysis, function_prediction, conservation)
        }
        
        confidence = self._calculate_genomic_anchor_confidence(core_analysis, function_prediction, conservation, regulatory)
        
        return processed_data, confidence, analytics
    
    def _anchor_auto_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced auto-detection anchor processing"""
        # Central tendency analysis
        central_analysis = self._analyze_central_features(data)
        
        # Stability metrics
        stability = self._calculate_stability_metrics(data)
        
        # Information density
        info_density = self._calculate_information_density(data)
        
        # Anchor quality assessment
        quality = self._assess_anchor_quality(data, central_analysis, stability)
        
        # Context sensitivity
        context_sensitivity = self._analyze_context_sensitivity(data, node_info)
        
        processed_data = {
            'data': data,
            'central_features': central_analysis,
            'stability_metrics': stability,
            'information_density': info_density,
            'quality_assessment': quality,
            'context_sensitivity': context_sensitivity,
            'anchor_type': 'auto_advanced'
        }
        
        analytics = {
            'centrality_score': central_analysis.get('centrality', 0),
            'stability_index': stability.get('index', 0),
            'information_content': info_density.get('content', 0),
            'quality_score': quality.get('overall', 0),
            'context_dependence': context_sensitivity.get('dependence', 0)
        }
        
        confidence = self._calculate_auto_anchor_confidence(central_analysis, stability, quality)
        
        return processed_data, confidence, analytics
    
    def _anchor_text_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced text anchor processing"""
        # Semantic core analysis
        semantic_core = self._analyze_semantic_core(data)
        
        # Syntactic anchor points
        syntactic = self._identify_syntactic_anchors(data)
        
        # Discourse markers
        discourse = self._analyze_discourse_markers(data)
        
        # Thematic strength
        thematic = self._calculate_thematic_strength(data)
        
        processed_data = {
            'text': data,
            'semantic_core': semantic_core,
            'syntactic_anchors': syntactic,
            'discourse_markers': discourse,
            'thematic_strength': thematic,
            'anchor_type': 'text_advanced'
        }
        
        analytics = {
            'semantic_density': semantic_core.get('density', 0),
            'syntactic_stability': syntactic.get('stability', 0),
            'discourse_coherence': discourse.get('coherence', 0),
            'thematic_consistency': thematic.get('consistency', 0)
        }
        
        confidence = self._calculate_text_anchor_confidence(semantic_core, syntactic, discourse, thematic)
        
        return processed_data, confidence, analytics
    
    def _anchor_structural_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced structural anchor processing"""
        # Structural invariants
        invariants = self._identify_structural_invariants(data)
        
        # Symmetry analysis
        symmetry = self._analyze_structural_symmetry(data)
        
        # Hierarchical features
        hierarchy = self._analyze_hierarchical_structure(data, node_info)
        
        # Stability under transformation
        transformation_stability = self._test_transformation_stability(data)
        
        processed_data = {
            'data': data,
            'structural_invariants': invariants,
            'symmetry_analysis': symmetry,
            'hierarchical_features': hierarchy,
            'transformation_stability': transformation_stability,
            'anchor_type': 'structural_advanced'
        }
        
        analytics = {
            'invariant_strength': invariants.get('strength', 0),
            'symmetry_score': symmetry.get('score', 0),
            'hierarchical_depth': hierarchy.get('depth', 0),
            'stability_coefficient': transformation_stability.get('coefficient', 0)
        }
        
        confidence = self._calculate_structural_anchor_confidence(invariants, symmetry, hierarchy, transformation_stability)
        
        return processed_data, confidence, analytics
    
    def _anchor_consensus_advanced(self, data: str, node_info: Dict[str, Any], config: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Advanced consensus anchor processing using multiple methods"""
        # Run multiple anchor methods
        methods = ['auto', 'structural']
        if all(c.upper() in 'ATGCN' for c in data if c.isalpha()):
            methods.append('genome')
        if ' ' in data:
            methods.append('text')
        
        method_results = {}
        for method in methods:
            if f'anchor_{method}' in self.anchor_functions:
                try:
                    result, conf, analytics = self.anchor_functions[f'anchor_{method}'](data, node_info, config)
                    method_results[method] = {
                        'result': result,
                        'confidence': conf,
                        'analytics': analytics
                    }
                except:
                    continue
        
        # Consensus analysis
        consensus = self._build_consensus(method_results)
        
        # Confidence weighting
        weighted_confidence = self._calculate_weighted_confidence(method_results)
        
        # Agreement metrics
        agreement = self._calculate_method_agreement(method_results)
        
        processed_data = {
            'data': data,
            'method_results': method_results,
            'consensus': consensus,
            'agreement_metrics': agreement,
            'anchor_type': 'consensus_advanced'
        }
        
        analytics = {
            'method_count': len(method_results),
            'consensus_strength': consensus.get('strength', 0),
            'agreement_level': agreement.get('level', 0),
            'confidence_variance': agreement.get('confidence_variance', 0)
        }
        
        confidence = weighted_confidence
        
        return processed_data, confidence, analytics
    
    # Helper methods for genomic analysis
    def _analyze_genomic_core(self, sequence: str) -> Dict[str, Any]:
        """Analyze the core genomic features"""
        sequence = sequence.upper()
        
        # Nucleotide composition
        composition = Counter(sequence)
        total = len(sequence)
        
        # GC content
        gc_content = (composition.get('G', 0) + composition.get('C', 0)) / total if total > 0 else 0
        
        # Complexity (Shannon entropy)
        entropy = 0
        for count in composition.values():
            if count > 0:
                p = count / total
                entropy -= p * (p.bit_length() - 1)
        
        # Codon analysis (if length is multiple of 3)
        codons = {}
        if len(sequence) % 3 == 0:
            for i in range(0, len(sequence), 3):
                codon = sequence[i:i+3]
                codons[codon] = codons.get(codon, 0) + 1
        
        return {
            'composition': dict(composition),
            'gc_content': gc_content,
            'entropy': entropy,
            'codons': codons,
            'length': total
        }
    
    def _predict_genomic_function(self, sequence: str, core_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Predict genomic function based on sequence features"""
        # Simple function prediction based on patterns
        functions = []
        confidence = 0.5
        
        # Check for start/stop codons
        if 'ATG' in sequence:
            functions.append('protein_coding')
            confidence += 0.2
        
        if any(stop in sequence for stop in ['TAA', 'TAG', 'TGA']):
            functions.append('termination')
            confidence += 0.1
        
        # Check GC content for regulatory regions
        gc_content = core_analysis.get('gc_content', 0)
        if gc_content > 0.6:
            functions.append('regulatory')
            confidence += 0.15
        
        # Check for repetitive elements
        if len(set(sequence)) < len(sequence) * 0.5:
            functions.append('repetitive')
            confidence += 0.1
        
        return {
            'predicted_functions': functions,
            'confidence': min(1.0, confidence),
            'primary_function': functions[0] if functions else 'unknown'
        }
    
    def _analyze_conservation(self, sequence: str) -> Dict[str, Any]:
        """Analyze sequence conservation (simplified)"""
        # Simple conservation metric based on complexity
        unique_chars = len(set(sequence))
        total_chars = len(sequence)
        
        # Higher complexity suggests lower conservation
        complexity = unique_chars / total_chars if total_chars > 0 else 0
        conservation_score = 1.0 - complexity
        
        return {
            'score': conservation_score,
            'complexity': complexity,
            'unique_elements': unique_chars
        }
    
    def _analyze_regulatory_potential(self, sequence: str) -> Dict[str, Any]:
        """Analyze regulatory potential of sequence"""
        # Look for regulatory motifs
        regulatory_motifs = {
            'TATA': 'TATAAA',
            'CAAT': 'CCAAT',
            'GC_box': 'GGGCGG'
        }
        
        found_motifs = []
        for motif_name, motif_seq in regulatory_motifs.items():
            if motif_seq in sequence.upper():
                found_motifs.append(motif_name)
        
        # Calculate regulatory strength
        strength = len(found_motifs) / len(regulatory_motifs)
        
        return {
            'strength': strength,
            'found_motifs': found_motifs,
            'potential_class': 'high' if strength > 0.5 else 'medium' if strength > 0.2 else 'low'
        }
    
    def _analyze_genomic_anchor_structure(self, sequence: str) -> Dict[str, Any]:
        """Analyze structural features of genomic anchor"""
        # Palindrome detection
        palindromes = []
        for length in range(4, min(len(sequence), 20)):
            for i in range(len(sequence) - length + 1):
                substr = sequence[i:i+length]
                if substr == substr[::-1]:
                    palindromes.append(substr)
        
        # Tandem repeats
        repeats = []
        for rep_len in range(2, min(len(sequence) // 2, 10)):
            for i in range(len(sequence) - rep_len * 2):
                if sequence[i:i+rep_len] == sequence[i+rep_len:i+rep_len*2]:
                    repeats.append(sequence[i:i+rep_len])
        
        # Stability score
        stability = 1.0 - (len(palindromes) + len(repeats)) / len(sequence)
        
        return {
            'palindromes': palindromes,
            'tandem_repeats': repeats,
            'stability': max(0, stability)
        }
    
    def _calculate_genomic_importance(self, core_analysis: Dict[str, Any], function_prediction: Dict[str, Any], conservation: Dict[str, Any]) -> float:
        """Calculate overall genomic importance score"""
        entropy_score = core_analysis.get('entropy', 0) / 2.0  # Normalize
        function_score = function_prediction.get('confidence', 0)
        conservation_score = conservation.get('score', 0)
        
        return (entropy_score + function_score + conservation_score) / 3.0
    
    def _calculate_genomic_anchor_confidence(self, core_analysis: Dict[str, Any], function_prediction: Dict[str, Any], conservation: Dict[str, Any], regulatory: Dict[str, Any]) -> float:
        """Calculate confidence for genomic anchor"""
        base_confidence = 0.4
        
        # Add confidence based on various factors
        if core_analysis.get('entropy', 0) > 1.5:
            base_confidence += 0.2
        
        base_confidence += function_prediction.get('confidence', 0) * 0.2
        base_confidence += conservation.get('score', 0) * 0.1
        base_confidence += regulatory.get('strength', 0) * 0.1
        
        return min(1.0, base_confidence)
    
    # Helper methods for general analysis
    def _analyze_central_features(self, data: str) -> Dict[str, Any]:
        """Analyze central/core features of data"""
        if not data:
            return {'centrality': 0}
        
        # Character frequency analysis
        char_freq = Counter(data)
        most_common_char, max_freq = char_freq.most_common(1)[0]
        
        # Position analysis
        middle_pos = len(data) // 2
        middle_char = data[middle_pos] if data else ''
        
        # Centrality score
        centrality = max_freq / len(data) if data else 0
        
        return {
            'centrality': centrality,
            'most_common_char': most_common_char,
            'middle_char': middle_char,
            'frequency_distribution': dict(char_freq.most_common(5))
        }
    
    def _calculate_stability_metrics(self, data: str) -> Dict[str, Any]:
        """Calculate stability metrics for anchor"""
        if not data:
            return {'index': 0}
        
        # Variance in character codes
        char_codes = [ord(c) for c in data]
        variance = statistics.variance(char_codes) if len(char_codes) > 1 else 0
        
        # Stability index (lower variance = higher stability)
        max_variance = 255 ** 2  # Maximum possible variance for ASCII
        stability_index = 1.0 - (variance / max_variance)
        
        return {
            'index': max(0, stability_index),
            'variance': variance,
            'mean_char_code': statistics.mean(char_codes)
        }
    
    def _calculate_information_density(self, data: str) -> Dict[str, Any]:
        """Calculate information density"""
        if not data:
            return {'content': 0}
        
        # Shannon entropy
        char_freq = Counter(data)
        total = len(data)
        entropy = 0
        
        for count in char_freq.values():
            p = count / total
            if p > 0:
                entropy -= p * (p.bit_length() - 1)
        
        # Information content per character
        content = entropy / len(data) if data else 0
        
        return {
            'content': content,
            'entropy': entropy,
            'unique_chars': len(char_freq)
        }
    
    def _assess_anchor_quality(self, data: str, central_analysis: Dict[str, Any], stability: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall anchor quality"""
        centrality_score = central_analysis.get('centrality', 0)
        stability_score = stability.get('index', 0)
        
        # Length factor (optimal length around 3-10 characters)
        length_factor = 1.0
        if len(data) < 3:
            length_factor = 0.5
        elif len(data) > 10:
            length_factor = 0.8
        
        overall_quality = (centrality_score + stability_score) * length_factor / 2.0
        
        return {
            'overall': overall_quality,
            'centrality_component': centrality_score,
            'stability_component': stability_score,
            'length_factor': length_factor
        }
    
    def _analyze_context_sensitivity(self, data: str, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how sensitive the anchor is to context"""
        level = node_info.get('level', 0)
        position = node_info.get('position', 0)
        
        # Context dependence based on level and position
        level_dependence = level / 10.0  # Normalize
        position_dependence = min(1.0, position / 100.0)  # Normalize
        
        overall_dependence = (level_dependence + position_dependence) / 2.0
        
        return {
            'dependence': overall_dependence,
            'level_factor': level_dependence,
            'position_factor': position_dependence
        }
    
    def _calculate_auto_anchor_confidence(self, central_analysis: Dict[str, Any], stability: Dict[str, Any], quality: Dict[str, Any]) -> float:
        """Calculate confidence for auto anchor"""
        centrality_conf = central_analysis.get('centrality', 0) * 0.3
        stability_conf = stability.get('index', 0) * 0.4
        quality_conf = quality.get('overall', 0) * 0.3
        
        return centrality_conf + stability_conf + quality_conf
    
    # Text analysis methods
    def _analyze_semantic_core(self, text: str) -> Dict[str, Any]:
        """Analyze semantic core of text"""
        words = text.split()
        
        if not words:
            return {'density': 0}
        
        # Word frequency
        word_freq = Counter(words)
        
        # Semantic density (simplified)
        unique_words = len(word_freq)
        total_words = len(words)
        density = unique_words / total_words if total_words > 0 else 0
        
        return {
            'density': density,
            'unique_words': unique_words,
            'total_words': total_words,
            'most_frequent': word_freq.most_common(3)
        }
    
    def _identify_syntactic_anchors(self, text: str) -> Dict[str, Any]:
        """Identify syntactic anchor points"""
        # Simple syntactic analysis
        punctuation_count = sum(1 for c in text if c in '.,!?;:')
        word_count = len(text.split())
        
        # Stability based on punctuation density
        stability = punctuation_count / len(text) if text else 0
        
        return {
            'stability': stability,
            'punctuation_count': punctuation_count,
            'word_count': word_count
        }
    
    def _analyze_discourse_markers(self, text: str) -> Dict[str, Any]:
        """Analyze discourse markers"""
        # Common discourse markers
        markers = ['however', 'therefore', 'moreover', 'furthermore', 'nevertheless']
        
        found_markers = [marker for marker in markers if marker in text.lower()]
        coherence = len(found_markers) / len(markers)
        
        return {
            'coherence': coherence,
            'found_markers': found_markers,
            'marker_density': len(found_markers) / len(text.split()) if text.split() else 0
        }
    
    def _calculate_thematic_strength(self, text: str) -> Dict[str, Any]:
        """Calculate thematic strength"""
        words = text.lower().split()
        
        if not words:
            return {'consistency': 0}
        
        # Simple thematic consistency based on word repetition
        word_freq = Counter(words)
        repeated_words = sum(1 for count in word_freq.values() if count > 1)
        consistency = repeated_words / len(word_freq) if word_freq else 0
        
        return {
            'consistency': consistency,
            'repeated_words': repeated_words,
            'vocabulary_size': len(word_freq)
        }
    
    def _calculate_text_anchor_confidence(self, semantic_core: Dict[str, Any], syntactic: Dict[str, Any], discourse: Dict[str, Any], thematic: Dict[str, Any]) -> float:
        """Calculate confidence for text anchor"""
        semantic_conf = semantic_core.get('density', 0) * 0.3
        syntactic_conf = syntactic.get('stability', 0) * 0.2
        discourse_conf = discourse.get('coherence', 0) * 0.2
        thematic_conf = thematic.get('consistency', 0) * 0.3
        
        return semantic_conf + syntactic_conf + discourse_conf + thematic_conf
    
    # Structural analysis methods
    def _identify_structural_invariants(self, data: str) -> Dict[str, Any]:
        """Identify structural invariants"""
        # Character patterns that remain constant
        invariants = []
        
        # Look for repeated patterns
        for length in range(1, min(len(data) // 2, 5)):
            for i in range(len(data) - length + 1):
                pattern = data[i:i+length]
                if data.count(pattern) > 1:
                    invariants.append(pattern)
        
        # Remove duplicates
        invariants = list(set(invariants))
        
        # Strength based on invariant coverage
        coverage = sum(len(inv) * data.count(inv) for inv in invariants)
        strength = coverage / len(data) if data else 0
        
        return {
            'strength': min(1.0, strength),
            'invariants': invariants,
            'coverage': coverage
        }
    
    def _analyze_structural_symmetry(self, data: str) -> Dict[str, Any]:
        """Analyze structural symmetry"""
        if not data:
            return {'score': 0}
        
        # Check for palindromic symmetry
        is_palindrome = data == data[::-1]
        
        # Partial symmetry score
        matches = sum(1 for i, c in enumerate(data) if i < len(data) - 1 - i and c == data[-(i+1)])
        symmetry_score = (2 * matches) / len(data) if data else 0
        
        return {
            'score': symmetry_score,
            'is_palindrome': is_palindrome,
            'symmetric_positions': matches
        }
    
    def _analyze_hierarchical_structure(self, data: str, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze hierarchical structure"""
        level = node_info.get('level', 0)
        
        # Depth analysis based on nested patterns
        nested_depth = 0
        for i in range(len(data) - 1):
            if data[i] == data[i+1]:
                nested_depth += 1
        
        # Normalize depth
        normalized_depth = nested_depth / len(data) if data else 0
        
        return {
            'depth': normalized_depth,
            'level': level,
            'nested_patterns': nested_depth
        }
    
    def _test_transformation_stability(self, data: str) -> Dict[str, Any]:
        """Test stability under various transformations"""
        if not data:
            return {'coefficient': 0}
        
        # Test case transformation stability
        upper_data = data.upper()
        lower_data = data.lower()
        
        # Test reversal stability
        reversed_data = data[::-1]
        
        # Calculate stability coefficient
        case_stability = 1.0 if data.isalpha() else 0.5
        reversal_stability = 1.0 if data == reversed_data else 0.0
        
        overall_coefficient = (case_stability + reversal_stability) / 2.0
        
        return {
            'coefficient': overall_coefficient,
            'case_stable': case_stability == 1.0,
            'reversal_stable': reversal_stability == 1.0
        }
    
    def _calculate_structural_anchor_confidence(self, invariants: Dict[str, Any], symmetry: Dict[str, Any], hierarchy: Dict[str, Any], transformation_stability: Dict[str, Any]) -> float:
        """Calculate confidence for structural anchor"""
        invariant_conf = invariants.get('strength', 0) * 0.3
        symmetry_conf = symmetry.get('score', 0) * 0.2
        hierarchy_conf = hierarchy.get('depth', 0) * 0.2
        stability_conf = transformation_stability.get('coefficient', 0) * 0.3
        
        return invariant_conf + symmetry_conf + hierarchy_conf + stability_conf
    
    # Consensus methods
    def _build_consensus(self, method_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Build consensus from multiple method results"""
        if not method_results:
            return {'strength': 0}
        
        # Average confidence across methods
        confidences = [result['confidence'] for result in method_results.values()]
        avg_confidence = statistics.mean(confidences)
        
        # Consensus strength based on agreement
        confidence_variance = statistics.variance(confidences) if len(confidences) > 1 else 0
        strength = avg_confidence * (1.0 - confidence_variance)
        
        return {
            'strength': max(0, strength),
            'average_confidence': avg_confidence,
            'confidence_variance': confidence_variance
        }
    
    def _calculate_weighted_confidence(self, method_results: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted confidence from multiple methods"""
        if not method_results:
            return 0.0
        
        # Weight methods based on their individual confidence
        total_weight = 0
        weighted_sum = 0
        
        for method, result in method_results.items():
            confidence = result['confidence']
            weight = confidence  # Use confidence as weight
            weighted_sum += confidence * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_method_agreement(self, method_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate agreement between methods"""
        if len(method_results) < 2:
            return {'level': 1.0, 'confidence_variance': 0.0}
        
        confidences = [result['confidence'] for result in method_results.values()]
        
        # Agreement level (inverse of variance)
        confidence_variance = statistics.variance(confidences)
        agreement_level = 1.0 / (1.0 + confidence_variance)
        
        return {
            'level': agreement_level,
            'confidence_variance': confidence_variance,
            'method_count': len(method_results)
        }
    
    def _calculate_anchor_strength(self, input_data: str, processed_data: Dict[str, Any]) -> float:
        """Calculate the strength of an anchor"""
        # Simple anchor strength calculation
        if not input_data:
            return 0.0
        
        # Base strength on data length and complexity
        length_factor = min(1.0, len(input_data) / 10.0)
        complexity_factor = len(set(input_data)) / len(input_data) if input_data else 0
        
        return (length_factor + complexity_factor) / 2.0
    
    def _track_anchor_relationships(self, anchor_uuid: str, anchor_result: Dict[str, Any]):
        """Track relationships between anchors"""
        level = anchor_result['node_info'].get('level', 0)
        position = anchor_result['node_info'].get('position', 0)
        
        # Group anchors by level for relationship analysis
        self.anchor_relationships[level].append({
            'uuid': anchor_uuid,
            'position': position,
            'confidence': anchor_result['confidence']
        })
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def get_anchor_by_uuid(self, anchor_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve anchor result by UUID"""
        return self.anchor_registry.get(anchor_uuid)
    
    def get_all_anchor_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all anchor results"""
        return self.anchor_registry.copy()
    
    def get_anchor_relationships(self) -> Dict[int, List[Dict[str, Any]]]:
        """Get anchor relationships by level"""
        return dict(self.anchor_relationships)
    
    def register_custom_anchor_function(self, name: str, function):
        """Register a custom anchor function"""
        self.anchor_functions[name] = function

