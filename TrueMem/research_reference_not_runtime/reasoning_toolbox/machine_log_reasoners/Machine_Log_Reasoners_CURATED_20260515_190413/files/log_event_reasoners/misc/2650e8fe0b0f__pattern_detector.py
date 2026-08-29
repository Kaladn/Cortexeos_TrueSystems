"""
Pattern Detection Module
Detects pattern breaks, causal chains, and anomalies
"""


class PatternDetector:
    """Detects patterns and anomalies in capsule sequences"""
    
    def __init__(self, config):
        self.config = config
        self.pattern_break_threshold = config['analysis']['pattern_break_threshold']
        self.consistency_high = config['analysis']['causal_consistency_high']
        self.consistency_low = config['analysis']['causal_consistency_low']
        self.min_chain_length = config['analysis']['min_chain_length']
    
    def detect(self, capsules, causal_results):
        """
        Detect all patterns and anomalies
        
        Args:
            capsules: List of capsule dictionaries
            causal_results: Causal analysis results
        
        Returns:
            dict: Detected patterns including breaks, chains, and anomalies
        """
        pattern_breaks = self._detect_pattern_breaks(capsules)
        causal_chains = self._detect_causal_chains(capsules, causal_results)
        anomalies = self._detect_anomalies(capsules, causal_results)
        
        return {
            'pattern_breaks': pattern_breaks,
            'causal_chains': causal_chains,
            'anomalies': anomalies
        }
    
    def _detect_pattern_breaks(self, capsules):
        """Detect pattern breaks (>threshold% unexpected moves)"""
        pattern_breaks = []
        
        for capsule in capsules:
            if abs(capsule['price_change']) > self.pattern_break_threshold:
                pattern_breaks.append({
                    'date': capsule['date'],
                    'change': capsule['price_change'],
                    'type': 'spike' if capsule['price_change'] > 0 else 'crash'
                })
        
        return pattern_breaks
    
    def _detect_causal_chains(self, capsules, causal_results):
        """Detect sustained causal chains (predictable sequences)"""
        chains = []
        current_chain = []
        
        for capsule in capsules:
            consistency = causal_results[capsule['index']]['consistency']
            
            if consistency >= self.consistency_high:
                current_chain.append(capsule['date'])
            else:
                if len(current_chain) >= self.min_chain_length:
                    chains.append({
                        'start': current_chain[0],
                        'end': current_chain[-1],
                        'length': len(current_chain)
                    })
                current_chain = []
        
        # Check final chain
        if len(current_chain) >= self.min_chain_length:
            chains.append({
                'start': current_chain[0],
                'end': current_chain[-1],
                'length': len(current_chain)
            })
        
        return chains
    
    def _detect_anomalies(self, capsules, causal_results):
        """Detect causal anomalies (low consistency events)"""
        anomalies = []
        
        for capsule in capsules:
            consistency = causal_results[capsule['index']]['consistency']
            
            if consistency < self.consistency_low:
                anomalies.append({
                    'date': capsule['date'],
                    'consistency': consistency,
                    'price_change': capsule['price_change']
                })
        
        return anomalies
