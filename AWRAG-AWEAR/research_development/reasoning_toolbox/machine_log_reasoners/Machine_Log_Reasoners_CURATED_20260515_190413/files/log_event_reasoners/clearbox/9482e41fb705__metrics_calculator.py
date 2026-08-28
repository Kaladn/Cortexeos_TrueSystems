"""
Cognitive Metrics Calculator
Calculates aggregate metrics and investment verdicts
"""

import numpy as np


class MetricsCalculator:
    """Calculates cognitive metrics from analysis results"""
    
    def __init__(self, config):
        self.config = config
    
    def calculate(self, capsules, causal_results, patterns):
        """
        Calculate all cognitive metrics
        
        Args:
            capsules: List of capsule dictionaries
            causal_results: Causal analysis results
            patterns: Detected patterns
        
        Returns:
            dict: Calculated metrics and verdict
        """
        # Extract consistency scores
        consistencies = [causal_results[c['index']]['consistency'] for c in capsules]
        avg_consistency = np.mean(consistencies)
        
        # Calculate volatility
        volatilities = [abs(c['price_change']) for c in capsules if c['price_change'] != 0]
        avg_volatility = np.mean(volatilities) if volatilities else 0
        
        # Calculate rates
        pattern_break_rate = (len(patterns['pattern_breaks']) / len(capsules)) * 100
        anomaly_rate = (len(patterns['anomalies']) / len(capsules)) * 100
        
        # Determine verdict and risk
        verdict, risk, grade = self._determine_verdict(
            avg_consistency, avg_volatility, pattern_break_rate, anomaly_rate
        )
        
        return {
            'avg_consistency': avg_consistency,
            'avg_volatility': avg_volatility,
            'pattern_break_rate': pattern_break_rate,
            'anomaly_rate': anomaly_rate,
            'num_pattern_breaks': len(patterns['pattern_breaks']),
            'num_causal_chains': len(patterns['causal_chains']),
            'num_anomalies': len(patterns['anomalies']),
            'verdict': verdict,
            'risk': risk,
            'grade': grade
        }
    
    def _determine_verdict(self, consistency, volatility, break_rate, anomaly_rate):
        """Determine investment verdict based on metrics"""
        if consistency > 0.6:
            verdict = "STABLE - High causal predictability"
            risk = "LOW"
            grade = "A (Strong Buy)"
        elif consistency > 0.4:
            verdict = "MODERATE - Some causal structure"
            risk = "MEDIUM"
            grade = "B (Buy)"
        elif consistency > 0.25:
            verdict = "VOLATILE - Weak causal structure"
            risk = "HIGH"
            grade = "C (Hold)"
        else:
            verdict = "CHAOTIC - Defies causal prediction"
            risk = "EXTREME"
            grade = "D (Avoid)"
        
        return verdict, risk, grade
