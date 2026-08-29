#!/usr/bin/env python3
"""
Standalone Context Window Parser for the 6-1-6 Relation Model.
This module implements the core functionality needed for contextual lattice generation
without dependencies on the full CortexOS infrastructure.
"""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple

class ContextWindowParser:
    """
    Parses text to build 6-1-6 context windows for each word.
    Each context window tracks the top 5 words that appear in each position
    relative to the target word.
    """
    
    def __init__(self, window_size: int = 6, top_k: int = 5):
        self.window_size = window_size
        self.top_k = top_k
        self.context_map: Dict[str, Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._raw_counts: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words, converting to lowercase."""
        return re.findall(r"\b\w+\b", text.lower())

    def parse_text(self, text: str):
        """
        Parse text to build context windows.
        For each word, track the words that appear in positions -6 to +6 around it.
        """
        tokens = self.tokenize(text)
        for i in range(self.window_size, len(tokens) - self.window_size):
            center_word = tokens[i]
            for offset in range(-self.window_size, self.window_size + 1):
                if offset == 0:
                    continue
                context_word = tokens[i + offset]
                self._raw_counts[center_word][offset][context_word] += 1

    def finalize(self):
        """
        Finalize context windows by keeping only the top_k words for each position.
        """
        for word, position_map in self._raw_counts.items():
            for position, counter in position_map.items():
                top_words = [w for w, _ in counter.most_common(self.top_k)]
                self.context_map[word][position] = top_words

    def get_context(self, word: str) -> Dict[int, List[str]]:
        """Get the context window for a word."""
        return self.context_map.get(word, {})

    def export_context_map(self, path: str):
        """Export the context map to a JSON file."""
        import json
        # Convert defaultdict to regular dict for JSON serialization
        export_map = {}
        for word, positions in self.context_map.items():
            export_map[word] = {str(pos): words for pos, words in positions.items()}
            
        with open(path, 'w') as f:
            json.dump(export_map, f, indent=2)


class DirectionalSemanticResonance:
    """
    Implements directional semantic resonance based on the 6-1-6 context window model.
    This calculates how strongly words resonate with each other based on their
    positional relationships.
    """
    
    def __init__(self, context_parser: ContextWindowParser):
        self.parser = context_parser
        self.position_weights = {
            # Left context weights (closer words have higher influence)
            -1: 1.0, -2: 0.9, -3: 0.7, -4: 0.5, -5: 0.3, -6: 0.2,
            # Right context weights (closer words have higher influence)
            1: 1.0, 2: 0.9, 3: 0.7, 4: 0.5, 5: 0.3, 6: 0.2
        }
    
    def compute_directional_resonance(self, word: str, context_word: str) -> float:
        """
        Computes the directional resonance between two words based on their
        positional relationships in the context window.
        
        Args:
            word: The center word
            context_word: The word to check for resonance
            
        Returns:
            A resonance score between 0.0 and 1.0
        """
        word_context = self.parser.get_context(word)
        if not word_context:
            return 0.0
            
        total_resonance = 0.0
        total_weight = 0.0
        
        # Check each position in the context window
        for position, weight in self.position_weights.items():
            if position in word_context and context_word in word_context[position]:
                # Calculate position-based resonance
                position_index = word_context[position].index(context_word)
                # Words at the top of the list have higher resonance
                position_resonance = 1.0 - (position_index / len(word_context[position]))
                total_resonance += position_resonance * weight
                total_weight += weight
                
        # Normalize the resonance score
        if total_weight > 0:
            return total_resonance / total_weight
        return 0.0
    
    def get_contextual_boost(self, word: str, context_words: List[str], threshold: float = 0.1) -> float:
        """
        Calculates the total resonance boost for a word based on a list of context words.
        
        Args:
            word: The word to boost
            context_words: List of words in the current context
            threshold: Minimum resonance threshold to consider
            
        Returns:
            A boost value between 0.0 and 1.0
        """
        if not context_words:
            return 0.0
            
        total_boost = 0.0
        for context_word in context_words:
            resonance = self.compute_directional_resonance(word, context_word)
            if resonance >= threshold:
                total_boost += resonance
                
        # Cap the boost at 1.0
        return min(total_boost, 1.0)


class ContextCloudManager:
    """
    Manages concept clouds based on the 6-1-6 context window model.
    This groups words into clouds based on their semantic relationships.
    """
    
    def __init__(self, context_parser: ContextWindowParser, resonance: DirectionalSemanticResonance):
        self.parser = context_parser
        self.resonance = resonance
        self.clouds = defaultdict(set)
        self.cloud_strengths = defaultdict(dict)
    
    def build_context_clouds(self, threshold: float = 0.3):
        """
        Builds context clouds based on the 6-1-6 context window model.
        
        Args:
            threshold: Minimum resonance threshold for cloud membership
        """
        # Get all words in the context map
        all_words = set(self.parser.context_map.keys())
        
        # Build clouds for each word
        for word in all_words:
            # Find related words with resonance above threshold
            for other_word in all_words:
                if word == other_word:
                    continue
                    
                resonance = self.resonance.compute_directional_resonance(word, other_word)
                if resonance >= threshold:
                    self.clouds[word].add(other_word)
                    self.cloud_strengths[word][other_word] = resonance
    
    def get_cloud(self, word: str) -> Set[str]:
        """
        Gets the context cloud for a word.
        
        Args:
            word: The word to get the cloud for
            
        Returns:
            A set of related words
        """
        return self.clouds.get(word, set())
    
    def get_cloud_with_strengths(self, word: str) -> Dict[str, float]:
        """
        Gets the context cloud for a word with resonance strengths.
        
        Args:
            word: The word to get the cloud for
            
        Returns:
            A dictionary mapping related words to resonance strengths
        """
        return self.cloud_strengths.get(word, {})
    
    def export_clouds(self, path: str):
        """
        Exports all context clouds to a JSON file.
        
        Args:
            path: Path to save the JSON file
        """
        import json
        # Convert sets to lists for JSON serialization
        export_clouds = {}
        for word, cloud in self.clouds.items():
            export_clouds[word] = {
                "members": list(cloud),
                "strengths": self.cloud_strengths[word]
            }
            
        with open(path, 'w') as f:
            json.dump(export_clouds, f, indent=2)
