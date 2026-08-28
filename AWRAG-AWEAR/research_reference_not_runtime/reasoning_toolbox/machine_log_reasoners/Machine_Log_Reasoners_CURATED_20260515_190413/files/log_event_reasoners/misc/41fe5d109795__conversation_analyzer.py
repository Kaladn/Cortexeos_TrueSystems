"""
CompuCog Conversation Analyzer
Detects model changes, quality drops, and conversation breaks in ChatGPT history
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, Counter
from datetime import datetime


class ConversationAnalyzer:
    """
    Analyzes ChatGPT conversation patterns to detect:
    - Model version changes
    - Quality degradation
    - Conversation breaks
    - Temporal patterns
    """
    
    def __init__(self, domain: str, data_dir: str = "data"):
        self.domain = domain
        self.data_dir = Path(data_dir)
        
        # File paths
        self.windows_file = self.data_dir / "windows" / f"{domain}_windows.jsonl"
        self.analysis_file = self.data_dir / "analysis" / f"{domain}_conversation_analysis.jsonl"
        
        # Analysis results
        self.model_changes = []
        self.quality_drops = []
        self.conversation_breaks = []
        
        # Statistics
        self.stats = {
            "windows_analyzed": 0,
            "model_changes_detected": 0,
            "quality_drops_detected": 0,
            "breaks_detected": 0
        }
    
    def analyze(self, entity: str) -> Dict:
        """
        Analyze conversation for model changes and quality issues.
        
        Args:
            entity: Conversation ID
        
        Returns:
            Analysis report dict
        """
        print(f"[ConversationAnalyzer] Analyzing conversation: {entity}")
        
        if not self.windows_file.exists():
            print(f"[ConversationAnalyzer] No windows file found: {self.windows_file}")
            return {"error": "No windows data available"}
        
        # Load windows for this entity
        windows = self._load_windows(entity)
        
        if not windows:
            print(f"[ConversationAnalyzer] No windows found for entity: {entity}")
            return {"error": f"No windows for entity {entity}"}
        
        # Detect model changes
        self._detect_model_changes(windows)
        
        # Detect quality drops
        self._detect_quality_drops(windows)
        
        # Detect conversation breaks
        self._detect_conversation_breaks(windows)
        
        # Generate report
        report = self._generate_report(entity, windows)
        
        # Save analysis
        self._save_analysis(report)
        
        print(f"[ConversationAnalyzer] Analysis complete. Stats: {self.stats}")
        return report
    
    def _load_windows(self, entity: str) -> List[Dict]:
        """Load windows for specific entity"""
        windows = []
        
        with open(self.windows_file, 'r') as f:
            for line in f:
                window = json.loads(line)
                if window.get('entity') == entity:
                    windows.append(window)
                    self.stats["windows_analyzed"] += 1
        
        # Sort by timestamp
        windows.sort(key=lambda w: w.get('timestamp', 0))
        return windows
    
    def _detect_model_changes(self, windows: List[Dict]):
        """
        Detect when model version changes in conversation.
        
        Pattern: model_GPT4 → model_GPT4O indicates model switch
        """
        prev_model = None
        
        for window in windows:
            # Extract model from center symbol
            center = window.get('center_symbol', '')
            
            if center.startswith('model_'):
                current_model = center.replace('model_', '')
                
                if prev_model and prev_model != current_model:
                    # Model change detected
                    change_event = {
                        'timestamp': window.get('timestamp'),
                        'from_model': prev_model,
                        'to_model': current_model,
                        'window_index': windows.index(window)
                    }
                    self.model_changes.append(change_event)
                    self.stats["model_changes_detected"] += 1
                    print(f"[ConversationAnalyzer] Model change detected: {prev_model} → {current_model}")
                
                prev_model = current_model
    
    def _detect_quality_drops(self, windows: List[Dict]):
        """
        Detect quality degradation patterns.
        
        Pattern: quality_GOOD → quality_ERROR indicates quality drop
        """
        quality_history = []
        
        for window in windows:
            center = window.get('center_symbol', '')
            
            if center.startswith('quality_'):
                quality = center.replace('quality_', '')
                quality_history.append({
                    'timestamp': window.get('timestamp'),
                    'quality': quality,
                    'window_index': windows.index(window)
                })
        
        # Detect drops (GOOD → ERROR or GOOD → INCOMPLETE)
        for i in range(1, len(quality_history)):
            prev = quality_history[i-1]
            curr = quality_history[i]
            
            if prev['quality'] == 'GOOD' and curr['quality'] in ['ERROR', 'INCOMPLETE']:
                drop_event = {
                    'timestamp': curr['timestamp'],
                    'from_quality': prev['quality'],
                    'to_quality': curr['quality'],
                    'window_index': curr['window_index']
                }
                self.quality_drops.append(drop_event)
                self.stats["quality_drops_detected"] += 1
                print(f"[ConversationAnalyzer] Quality drop detected: {prev['quality']} → {curr['quality']}")
    
    def _detect_conversation_breaks(self, windows: List[Dict]):
        """
        Detect conversation flow interruptions.
        
        Pattern: role_USER → role_USER (no assistant response)
        """
        role_history = []
        
        for window in windows:
            center = window.get('center_symbol', '')
            
            if center.startswith('role_'):
                role = center.replace('role_', '')
                role_history.append({
                    'timestamp': window.get('timestamp'),
                    'role': role,
                    'window_index': windows.index(window)
                })
        
        # Detect breaks (USER → USER)
        for i in range(1, len(role_history)):
            prev = role_history[i-1]
            curr = role_history[i]
            
            if prev['role'] == 'USER' and curr['role'] == 'USER':
                break_event = {
                    'timestamp': curr['timestamp'],
                    'type': 'missing_response',
                    'window_index': curr['window_index']
                }
                self.conversation_breaks.append(break_event)
                self.stats["breaks_detected"] += 1
                print(f"[ConversationAnalyzer] Conversation break detected at timestamp {curr['timestamp']}")
    
    def _generate_report(self, entity: str, windows: List[Dict]) -> Dict:
        """Generate analysis report"""
        # Count symbol frequencies
        symbol_counts = Counter()
        for window in windows:
            symbol_counts[window.get('center_symbol', '')] += 1
        
        # Extract model distribution
        model_dist = {k: v for k, v in symbol_counts.items() if k.startswith('model_')}
        
        # Extract quality distribution
        quality_dist = {k: v for k, v in symbol_counts.items() if k.startswith('quality_')}
        
        # Build report
        report = {
            'entity': entity,
            'timestamp': int(datetime.now().timestamp()),
            'total_windows': len(windows),
            'model_changes': self.model_changes,
            'quality_drops': self.quality_drops,
            'conversation_breaks': self.conversation_breaks,
            'model_distribution': model_dist,
            'quality_distribution': quality_dist,
            'statistics': self.stats,
            'summary': self._generate_summary()
        }
        
        return report
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary"""
        summary_parts = []
        
        if self.model_changes:
            summary_parts.append(f"Detected {len(self.model_changes)} model changes")
        
        if self.quality_drops:
            summary_parts.append(f"Detected {len(self.quality_drops)} quality drops")
        
        if self.conversation_breaks:
            summary_parts.append(f"Detected {len(self.conversation_breaks)} conversation breaks")
        
        if not summary_parts:
            return "No significant issues detected"
        
        return ". ".join(summary_parts) + "."
    
    def _save_analysis(self, report: Dict):
        """Save analysis report to file"""
        self.analysis_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.analysis_file, 'a') as f:
            f.write(json.dumps(report) + '\n')
    
    def get_statistics(self) -> Dict:
        """Return analysis statistics"""
        return self.stats


if __name__ == "__main__":
    # Test the analyzer
    analyzer = ConversationAnalyzer(domain="chatgpt")
    report = analyzer.analyze(entity="test_conversation")
    
    print(f"\nAnalysis Report:")
    print(json.dumps(report, indent=2))
