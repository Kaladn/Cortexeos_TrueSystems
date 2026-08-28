"""
Patent Signature Matcher

Purpose:
  Loads Activision patent signatures and matches operator detections
  against documented manipulation methods.

Components:
  - Signature loader (JSONL parser)
  - Pattern matcher (detection → signature)
  - Confidence calculator
  - Citation generator

Usage:
  from patent_matcher import PatentMatcher
  
  matcher = PatentMatcher("gaming/signatures/activision_patents.jsonl")
  match = matcher.match_signature("hit_registration", detection_data)
  
  if match:
      print(f"Patent: {match['patent_number']}")
      print(f"Citation: {match['citation']}")
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class PatentMatcher:
    """
    Loads and matches patent signatures against operator detections.
    """
    
    def __init__(self, signature_path: str):
        self.signature_path = Path(signature_path)
        self.signatures: List[Dict] = []
        self._load_signatures()
    
    def _load_signatures(self):
        """Load patent signatures from JSONL file"""
        if not self.signature_path.exists():
            print(f"[!] Patent signature file not found: {self.signature_path}")
            return
        
        with open(self.signature_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    sig = json.loads(line)
                    self.signatures.append(sig)
        
        print(f"[+] Loaded {len(self.signatures)} patent signatures")
    
    def get_signatures_for_operator(self, operator_name: str) -> List[Dict]:
        """Get all signatures that apply to a specific operator"""
        return [
            sig for sig in self.signatures 
            if sig.get('compucog_operator') == operator_name
        ]
    
    def match_signature(self, operator_name: str, detection_data: Dict) -> Optional[Dict]:
        """
        Match detection data against patent signatures.
        
        Args:
            operator_name: Name of operator (e.g., "hit_registration")
            detection_data: Detection metrics from operator
        
        Returns:
            Patent match dict with signature_id, confidence, citation, etc.
            None if no match found.
        """
        operator_sigs = self.get_signatures_for_operator(operator_name)
        
        if not operator_sigs:
            return None
        
        best_match = None
        best_confidence = 0.0
        
        for sig in operator_sigs:
            confidence = self._calculate_match_confidence(sig, detection_data)
            
            if confidence > best_confidence and confidence >= sig.get('confidence_threshold', 0.5):
                best_confidence = confidence
                best_match = {
                    'signature_id': sig['signature_id'],
                    'patent_number': sig['patent_number'],
                    'patent_paragraph': sig.get('patent_paragraph', ''),
                    'manipulation_method': sig['manipulation_method'],
                    'citation': sig['citation'],
                    'evidence_type': sig.get('evidence_type', 'FORENSIC'),
                    'match_confidence': confidence,
                    'detection_pattern': sig['detection_pattern']
                }
        
        return best_match
    
    def _calculate_match_confidence(self, signature: Dict, detection_data: Dict) -> float:
        """
        Calculate confidence that detection matches patent signature.
        
        Pattern-specific matching logic based on signature detection_pattern.
        """
        pattern = signature.get('detection_pattern', '')
        
        # Hit registration tolerance variance
        if pattern == 'hit_tolerance_variance':
            ghost_ratio = detection_data.get('ghost_ratio', 0.0)
            threshold = signature.get('threshold', 0.15)
            
            if ghost_ratio > threshold:
                # Confidence scales with how far above threshold
                confidence = min(1.0, ghost_ratio / 0.5)  # Max at 50% ghost ratio
                return confidence
            return 0.0
        
        # Spawn proximity bias
        elif pattern == 'spawn_proximity_bias':
            spawn_bias = detection_data.get('spawn_bias_score', 0.0)
            threshold = signature.get('threshold', 0.30)
            
            if spawn_bias > threshold:
                confidence = min(1.0, (spawn_bias - threshold) / (1.0 - threshold))
                return confidence
            return 0.0
        
        # Damage multiplier variance
        elif pattern == 'damage_multiplier_variance':
            damage_variance = detection_data.get('damage_variance_pct', 0.0)
            threshold = signature.get('threshold', 0.10)
            
            if abs(damage_variance) > threshold:
                confidence = min(1.0, abs(damage_variance) / 0.30)
                return confidence
            return 0.0
        
        # Reward multiplier variance
        elif pattern == 'reward_multiplier_variance':
            reward_variance = detection_data.get('reward_variance_pct', 0.0)
            threshold = signature.get('threshold', 0.20)
            
            if abs(reward_variance) > threshold:
                confidence = min(1.0, abs(reward_variance) / 0.40)
                return confidence
            return 0.0
        
        # Skill disparity after store visit
        elif pattern == 'skill_disparity_after_store_visit':
            skill_gap = detection_data.get('skill_gap_score', 0.0)
            threshold = signature.get('threshold', 0.40)
            
            if skill_gap > threshold:
                confidence = min(1.0, (skill_gap - threshold) / (1.0 - threshold))
                return confidence
            return 0.0
        
        # Performance spike after purchase
        elif pattern == 'performance_spike_after_purchase':
            perf_delta = detection_data.get('performance_delta', 0.0)
            threshold = signature.get('threshold', 0.25)
            
            if perf_delta > threshold:
                confidence = min(1.0, perf_delta / 0.50)
                return confidence
            return 0.0
        
        # Opponent difficulty inverse to recent performance (EOMM rubber-banding)
        elif pattern == 'opponent_difficulty_inverse_to_recent_performance':
            rubber_band_score = detection_data.get('rubber_band_score', 0.0)
            threshold = signature.get('threshold', 0.35)
            
            if rubber_band_score > threshold:
                confidence = min(1.0, (rubber_band_score - threshold) / (1.0 - threshold))
                return confidence
            return 0.0
        
        # Default: no match
        return 0.0
    
    def get_all_signatures(self) -> List[Dict]:
        """Return all loaded signatures"""
        return self.signatures
    
    def get_signature_by_id(self, signature_id: str) -> Optional[Dict]:
        """Get specific signature by ID"""
        for sig in self.signatures:
            if sig.get('signature_id') == signature_id:
                return sig
        return None
