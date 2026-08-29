"""
Bidirectional Causal Validation
Implements CRSA-616 forward and backward validation
"""

import numpy as np


class CausalAnalyzer:
    """Performs bidirectional causal validation on capsules"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze(self, capsules):
        """
        Perform bidirectional causal validation
        
        For each capsule:
        1. Backward validation: Does anchor follow from previous pattern?
        2. Forward validation: Does next pattern follow from anchor?
        3. Calculate causal consistency score (0=chaos, 1=predictable)
        4. Generate NCV-73 (Nightmare Capsule Vector)
        
        Args:
            capsules: List of capsule dictionaries
        
        Returns:
            dict: Causal analysis results per capsule index
        """
        results = {}
        
        for capsule in capsules:
            consistency = self._calculate_consistency(capsule)
            ncv_73 = self._generate_ncv_73(capsule)
            
            results[capsule['index']] = {
                'consistency': consistency,
                'ncv_73': ncv_73,
                'backward_score': self._backward_validation(capsule),
                'forward_score': self._forward_validation(capsule)
            }
            
            # Store NCV-73 in capsule for graph building
            capsule['ncv_73'] = ncv_73
        
        return results
    
    def _calculate_consistency(self, capsule):
        """Calculate causal consistency score"""
        backward = self._backward_validation(capsule)
        forward = self._forward_validation(capsule)
        return (backward + forward) / 2.0
    
    def _backward_validation(self, capsule):
        """Does anchor follow from previous pattern?"""
        if len(capsule['prev_positions']) < 3:
            return 0.5  # Insufficient data
        
        # Calculate previous price changes
        prev_changes = []
        for i in range(len(capsule['prev_positions']) - 1):
            change = ((capsule['prev_positions'][i]['close'] - 
                      capsule['prev_positions'][i+1]['close']) / 
                      capsule['prev_positions'][i+1]['close']) * 100
            prev_changes.append(change)
        
        if not prev_changes:
            return 0.5
        
        prev_avg = np.mean(prev_changes)
        prev_std = np.std(prev_changes) if len(prev_changes) > 1 else 1.0
        
        # How consistent is anchor with previous pattern?
        if prev_std > 0:
            score = 1.0 / (1.0 + abs(capsule['price_change'] - prev_avg) / prev_std)
        else:
            score = 1.0 if abs(capsule['price_change'] - prev_avg) < 1.0 else 0.0
        
        return score
    
    def _forward_validation(self, capsule):
        """Does next pattern follow from anchor?"""
        if len(capsule['next_positions']) < 3:
            return 0.5  # Insufficient data
        
        # Calculate next price changes
        next_changes = []
        for i in range(len(capsule['next_positions']) - 1):
            change = ((capsule['next_positions'][i]['close'] - 
                      capsule['next_positions'][i+1]['close']) / 
                      capsule['next_positions'][i+1]['close']) * 100
            next_changes.append(change)
        
        if not next_changes:
            return 0.5
        
        next_avg = np.mean(next_changes)
        next_std = np.std(next_changes) if len(next_changes) > 1 else 1.0
        
        # How consistent is next pattern with anchor?
        if next_std > 0:
            score = 1.0 / (1.0 + abs(next_avg - capsule['price_change']) / next_std)
        else:
            score = 1.0 if abs(next_avg - capsule['price_change']) < 1.0 else 0.0
        
        return score
    
    def _generate_ncv_73(self, capsule):
        """
        Generate NCV-73 (Nightmare Capsule Vector)
        73-dimensional vector representing causal context
        
        Dimensions:
        - 36 previous possibilities (6 positions × 6 branches)
        - 1 anchor position
        - 36 next possibilities (6 positions × 6 branches)
        
        Args:
            capsule: Capsule dictionary
        
        Returns:
            numpy.ndarray: 73-dimensional NCV vector
        """
        ncv = []
        
        # Previous 36 dimensions (6 positions with 6 features each)
        for pos in capsule['prev_positions']:
            ncv.extend([
                pos['close'],
                pos['volume'],
                pos['high'] - pos['low'],  # Range
                (pos['close'] - pos['open']) / pos['open'] if pos['open'] > 0 else 0,  # Change
                pos['high'] / pos['close'] if pos['close'] > 0 else 1,  # High ratio
                pos['low'] / pos['close'] if pos['close'] > 0 else 1   # Low ratio
            ])
        
        # Pad if fewer than 6 previous positions
        while len(ncv) < 36:
            ncv.append(0.0)
        
        # Anchor dimension (1)
        ncv.append(capsule['anchor']['close'])
        
        # Next 36 dimensions (6 positions with 6 features each)
        for pos in capsule['next_positions']:
            ncv.extend([
                pos['close'],
                pos['volume'],
                pos['high'] - pos['low'],
                (pos['close'] - pos['open']) / pos['open'] if pos['open'] > 0 else 0,
                pos['high'] / pos['close'] if pos['close'] > 0 else 1,
                pos['low'] / pos['close'] if pos['close'] > 0 else 1
            ])
        
        # Pad if fewer than 6 next positions
        while len(ncv) < 73:
            ncv.append(0.0)
        
        return np.array(ncv[:73])  # Ensure exactly 73 dimensions
