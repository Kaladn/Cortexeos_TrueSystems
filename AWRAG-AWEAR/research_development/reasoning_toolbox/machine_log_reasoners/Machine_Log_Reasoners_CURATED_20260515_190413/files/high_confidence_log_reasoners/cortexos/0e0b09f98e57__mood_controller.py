"""
Mood Controller module for CortexOS.
Manages system-wide mood state transitions and their effects on neural processing.
"""

import json
import time
import random
import logging
from datetime import datetime
from neuromodulation import Neuromodulator

class MoodController:
    """
    Controls system-wide mood states and transitions for CortexOS.
    Manages mood persistence, transitions, and effects on neural processing parameters.
    """
    def __init__(self, mood_to_color_file="mood_to_color.json", initial_mood="neutral"):
        self.neuromod = Neuromodulator()
        self.current_mood = initial_mood
        self.mood_start_time = time.time()
        self.mood_history = []
        self.mood_to_color = self._load_mood_to_color(mood_to_color_file)
        self.transition_probabilities = self._initialize_transition_matrix()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Log initial mood
        self.logger.info(f"Initialized with mood: {self.current_mood}")
        self._record_mood_change(self.current_mood, "initialization", 1.0)
        
    def _load_mood_to_color(self, mood_to_color_file):
        """Load mood-to-color mapping from JSON file."""
        try:
            with open(mood_to_color_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load mood colors from {mood_to_color_file}: {e}")
            # Fallback to basic colors
            return {
                "neutral": [1.0, 1.0, 1.0],
                "excited": [1.0, 0.6, 0.2],
                "focused": [0.2, 0.4, 0.8],
                "cautious": [0.8, 0.8, 0.2],
                "curious": [0.4, 0.8, 1.0]
            }
            
    def _initialize_transition_matrix(self):
        """Initialize mood transition probability matrix."""
        # Default transition probabilities
        transitions = {
            "neutral": {
                "neutral": 0.7,
                "curious": 0.1,
                "focused": 0.1,
                "excited": 0.05,
                "cautious": 0.05
            },
            "curious": {
                "curious": 0.6,
                "excited": 0.2,
                "neutral": 0.1,
                "focused": 0.05,
                "imaginative": 0.05
            },
            "focused": {
                "focused": 0.7,
                "neutral": 0.1,
                "alert": 0.1,
                "reflective": 0.05,
                "cautious": 0.05
            },
            "excited": {
                "excited": 0.6,
                "curious": 0.15,
                "impulsive": 0.1,
                "neutral": 0.1,
                "playful": 0.05
            },
            "cautious": {
                "cautious": 0.65,
                "alert": 0.15,
                "neutral": 0.1,
                "anxious": 0.05,
                "focused": 0.05
            },
            "alert": {
                "alert": 0.6,
                "cautious": 0.2,
                "focused": 0.1,
                "neutral": 0.05,
                "paranoid": 0.05
            },
            "reflective": {
                "reflective": 0.7,
                "neutral": 0.1,
                "focused": 0.1,
                "calm": 0.05,
                "dreamy": 0.05
            },
            "imaginative": {
                "imaginative": 0.6,
                "curious": 0.15,
                "dreamy": 0.1,
                "playful": 0.1,
                "neutral": 0.05
            },
            "impulsive": {
                "impulsive": 0.55,
                "excited": 0.2,
                "playful": 0.1,
                "aggressive": 0.1,
                "neutral": 0.05
            },
            "anxious": {
                "anxious": 0.6,
                "cautious": 0.15,
                "alert": 0.1,
                "paranoid": 0.1,
                "neutral": 0.05
            },
            "paranoid": {
                "paranoid": 0.5,
                "anxious": 0.2,
                "alert": 0.15,
                "cautious": 0.1,
                "neutral": 0.05
            },
            "dreamy": {
                "dreamy": 0.65,
                "imaginative": 0.15,
                "reflective": 0.1,
                "neutral": 0.05,
                "fatigued": 0.05
            },
            "playful": {
                "playful": 0.6,
                "excited": 0.15,
                "curious": 0.1,
                "impulsive": 0.1,
                "neutral": 0.05
            },
            "aggressive": {
                "aggressive": 0.55,
                "impulsive": 0.2,
                "alert": 0.1,
                "neutral": 0.1,
                "paranoid": 0.05
            },
            "calm": {
                "calm": 0.7,
                "neutral": 0.15,
                "reflective": 0.1,
                "dreamy": 0.05
            },
            "fatigued": {
                "fatigued": 0.6,
                "neutral": 0.2,
                "dreamy": 0.1,
                "calm": 0.1
            }
        }
        
        # Ensure all moods have transition probabilities
        for mood in self.neuromod.mood_configs.keys():
            if mood not in transitions:
                transitions[mood] = {"neutral": 0.3, mood: 0.7}
                
        return transitions
        
    def get_current_mood(self):
        """
        Get the current system mood state.
        
        Returns:
            dict: Current mood information
        """
        duration = time.time() - self.mood_start_time
        color = self.mood_to_color.get(self.current_mood, [1.0, 1.0, 1.0])
        
        return {
            "mood": self.current_mood,
            "duration": duration,
            "start_time": self.mood_start_time,
            "color": color,
            "params": self.neuromod.adjust_resonance_params(self.current_mood)
        }
        
    def set_mood(self, mood, reason="manual", confidence=1.0):
        """
        Set the system mood state.
        
        Args:
            mood (str): Target mood state
            reason (str): Reason for mood change
            confidence (float): Confidence level for this mood (0-1)
            
        Returns:
            bool: Success status
        """
        if mood not in self.neuromod.mood_configs:
            self.logger.warning(f"Invalid mood state: {mood}")
            return False
            
        # Record the mood change
        old_mood = self.current_mood
        self.current_mood = mood
        self.mood_start_time = time.time()
        
        self._record_mood_change(mood, reason, confidence)
        
        self.logger.info(f"Mood changed from {old_mood} to {mood} (reason: {reason}, confidence: {confidence:.2f})")
        return True
        
    def _record_mood_change(self, mood, reason, confidence):
        """Record mood change in history."""
        self.mood_history.append({
            "mood": mood,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "reason": reason,
            "confidence": confidence
        })
        
        # Limit history size
        if len(self.mood_history) > 100:
            self.mood_history = self.mood_history[-100:]
            
    def suggest_mood_transition(self, input_data=None):
        """
        Suggest a mood transition based on current state and optional input.
        
        Args:
            input_data (dict, optional): External data influencing mood
            
        Returns:
            dict: Suggested mood transition
        """
        current_mood = self.current_mood
        
        # Get transition probabilities for current mood
        if current_mood in self.transition_probabilities:
            transitions = self.transition_probabilities[current_mood]
        else:
            # Fallback to neutral transitions
            transitions = self.transition_probabilities["neutral"]
            
        # Apply any input data influences (stub for future enhancement)
        if input_data:
            # Example: Adjust probabilities based on input sentiment
            pass
            
        # Select next mood based on probabilities
        moods = list(transitions.keys())
        probabilities = list(transitions.values())
        
        # Normalize probabilities
        total = sum(probabilities)
        if total > 0:
            probabilities = [p/total for p in probabilities]
            
        next_mood = random.choices(moods, weights=probabilities, k=1)[0]
        confidence = transitions.get(next_mood, 0.5)
        
        return {
            "current_mood": current_mood,
            "suggested_mood": next_mood,
            "confidence": confidence,
            "reason": "probabilistic_transition"
        }
        
    def update_mood_based_on_input(self, input_type, input_data):
        """
        Update mood based on external input.
        
        Args:
            input_type (str): Type of input ('text', 'image', 'resonance', etc.)
            input_data (dict): Input data with relevant features
            
        Returns:
            dict: Mood update result
        """
        # Default: no change
        result = {
            "previous_mood": self.current_mood,
            "new_mood": self.current_mood,
            "changed": False,
            "confidence": 1.0,
            "reason": "no_change"
        }
        
        # Process different input types
        if input_type == "text":
            # Example: Text sentiment analysis
            if "sentiment" in input_data:
                sentiment = input_data["sentiment"]
                if sentiment > 0.7:
                    self.set_mood("excited", "high_positive_sentiment", sentiment)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "excited", 
                             "changed": True, "confidence": sentiment, "reason": "high_positive_sentiment"}
                elif sentiment > 0.3:
                    self.set_mood("curious", "positive_sentiment", sentiment)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "curious", 
                             "changed": True, "confidence": sentiment, "reason": "positive_sentiment"}
                elif sentiment < -0.7:
                    self.set_mood("cautious", "high_negative_sentiment", abs(sentiment))
                    result = {"previous_mood": result["previous_mood"], "new_mood": "cautious", 
                             "changed": True, "confidence": abs(sentiment), "reason": "high_negative_sentiment"}
                elif sentiment < -0.3:
                    self.set_mood("alert", "negative_sentiment", abs(sentiment))
                    result = {"previous_mood": result["previous_mood"], "new_mood": "alert", 
                             "changed": True, "confidence": abs(sentiment), "reason": "negative_sentiment"}
                    
        elif input_type == "resonance":
            # Example: Resonance pattern analysis
            if "pattern" in input_data:
                pattern = input_data["pattern"]
                if pattern == "high_novelty":
                    self.set_mood("curious", "novel_resonance_pattern", 0.8)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "curious", 
                             "changed": True, "confidence": 0.8, "reason": "novel_resonance_pattern"}
                elif pattern == "high_focus":
                    self.set_mood("focused", "focused_resonance_pattern", 0.9)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "focused", 
                             "changed": True, "confidence": 0.9, "reason": "focused_resonance_pattern"}
                    
        # Apply probabilistic transition if no change and enough time has passed
        if not result["changed"] and (time.time() - self.mood_start_time) > 300:  # 5 minutes
            suggestion = self.suggest_mood_transition()
            if suggestion["suggested_mood"] != self.current_mood:
                self.set_mood(
                    suggestion["suggested_mood"],
                    suggestion["reason"],
                    suggestion["confidence"]
                )
                result = {
                    "previous_mood": result["previous_mood"],
                    "new_mood": suggestion["suggested_mood"],
                    "changed": True,
                    "confidence": suggestion["confidence"],
                    "reason": suggestion["reason"]
                }
                
        return result
        
    def get_mood_history(self, limit=10):
        """
        Get recent mood history.
        
        Args:
            limit (int): Maximum number of history entries to return
            
        Returns:
            list: Recent mood history
        """
        return self.mood_history[-limit:]
        
    def export_mood_parameters(self):
        """
        Export current mood parameters for visualization and debugging.
        
        Returns:
            dict: Current mood parameters
        """
        mood_info = self.get_current_mood()
        params = mood_info["params"]
        
        return {
            "mood": mood_info["mood"],
            "color": mood_info["color"],
            "duration": mood_info["duration"],
            "k": params["k"],
            "threshold": params["threshold"],
            "decay": params["decay"],
            "phase_step": params["phase_step"],
            "base_frequency": params["base_frequency"]
        }
