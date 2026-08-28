# File: resonance_engine.py

import math

class ResonanceEngine:
    def __init__(self, schema_data=None, proximity_window=6, confidence_threshold=0.8):
        self.schema = schema_data if schema_data else {}
        self.proximity_window = proximity_window
        self.confidence_threshold = confidence_threshold

    def process(self, parsed_events):
        """
        Process parsed lawful cognition events into resonance chains.
        """
        resonance_output = []

        for idx, event in enumerate(parsed_events):
            chain = self.build_resonance_chain(parsed_events, idx)
            resonance_output.append({
                "time_anchor": event['time_anchor'],
                "chain_strength": chain['strength'],
                "contextual_resonance": chain['context_window'],
            })

        return resonance_output

    def build_resonance_chain(self, events, center_idx):
        """
        Build 6-1-6 resonance proximity window chain.
        """
        window = []
        start_idx = max(0, center_idx - self.proximity_window)
        end_idx = min(len(events), center_idx + self.proximity_window + 1)

        # Collect surrounding resonance signals
        for i in range(start_idx, end_idx):
            distance = abs(center_idx - i)
            weight = self.compute_weight(distance)
            window.append({
                "distance": distance,
                "weight": weight,
                "event": events[i]
            })

        # Simple strength sum — future lawful weighting will replace this
        total_strength = sum(w['weight'] for w in window)

        return {
            "strength": round(total_strength, 5),
            "context_window": window
        }

    def compute_weight(self, distance):
        """
        Simple lawful weight curve — closer events carry more resonance.
        """
        if distance == 0:
            return 1.0
        return round(1.0 / (distance + 1), 5)
