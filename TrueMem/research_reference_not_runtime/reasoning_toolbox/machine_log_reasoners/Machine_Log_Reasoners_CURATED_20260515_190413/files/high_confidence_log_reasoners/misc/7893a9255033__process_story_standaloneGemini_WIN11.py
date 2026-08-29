#!/usr/bin/env python3
"""
Process a story through the standalone contextual lattice generator.
This script uses the 6-1-6 Relation Model to create positional word relationships
and generate concept clouds based on the narrative.

MODIFIED for Windows 11, interactive paths, and YAML-based word filtering.
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

# --- MODIFICATION START ---
# Added 'yaml' import. You may need to install it: pip install PyYAML
try:
    import yaml
except ImportError:
    print("PyYAML not found. Please install it using: pip install PyYAML")
    sys.exit(1)
# --- MODIFICATION END ---

# Import standalone modules (ensure these .py files are in the same directory)
from standalone_context_parser import ContextWindowParser, DirectionalSemanticResonance, ContextCloudManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class StoryAnalyzer:
    """
    Analyzes a story using the 6-1-6 context window model to generate
    positional word relationships and concept clouds.
    """
    
    # --- MODIFICATION START ---
    # Changed default output directory to a Windows-friendly path.
    def __init__(self, output_dir: str = "C:\\story_analysis"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "plots"), exist_ok=True)
        
        # Initialize components
        self.context_parser = ContextWindowParser(window_size=6, top_k=5)
        
        # Focus words are now managed dynamically, not hardcoded.
        self.focus_words = []
        
        # Results storage
        self.results = {}
    
    def process_story(self, story_path: str, include_words: List[str], exclude_words: List[str]):
        """Process the story and generate contextual lattice."""
        logger.info(f"Processing story: {story_path}")
        
        # Read the story
        with open(story_path, 'r') as f:
            story_text = f.read()
        
        # Parse the text
        self.context_parser.parse_text(story_text)
        self.context_parser.finalize()

        # ---
        # Determine the final list of focus words based on YAML config
        # ---
        all_story_words = self.context_parser.context_map.keys()
        
        # If an include list is provided, use it. Otherwise, use all words from the story.
        if include_words:
            base_words = set(include_words)
            logger.info(f"Focusing on {len(base_words)} words from 'include_words' list.")
        else:
            base_words = set(all_story_words)
            logger.info("No 'include_words' list found. Analyzing all unique words from the text.")

        words_to_exclude = set(exclude_words)
        if words_to_exclude:
             logger.info(f"Excluding {len(words_to_exclude)} words from 'exclude_words' list.")

        # The final focus words are the base set minus the excluded words.
        self.focus_words = sorted(list(base_words - words_to_exclude))
        
        if not self.focus_words:
            logger.error("No focus words left to analyze after filtering. Exiting.")
            return
        # --- MODIFICATION END ---
            
        # Initialize resonance
        self.resonance = DirectionalSemanticResonance(self.context_parser)
        
        # Initialize cloud manager
        self.cloud_manager = ContextCloudManager(self.context_parser, self.resonance)
        
        # Build context clouds
        self.cloud_manager.build_context_clouds(threshold=0.3)
        
        # Analyze context windows
        self._analyze_context_windows()
        
        # Analyze directional resonance
        self._analyze_directional_resonance()
        
        # Analyze context clouds
        self._analyze_context_clouds()
        
        # Export results
        self._export_results()
        
        logger.info("Story processing complete")
    
    def _analyze_context_windows(self):
        """Analyze context windows for focus words."""
        logger.info("Analyzing context windows")
        
        results = {}
        
        # Get context windows for focus words
        for word in self.focus_words:
            context = self.context_parser.get_context(word)
            if context:
                results[word] = context
        
        # Save results
        self.results["context_windows"] = results
        
        logger.info(f"Context windows analyzed for {len(results)} focus words")
    
    def _analyze_directional_resonance(self):
        """Analyze directional resonance between focus words."""
        logger.info("Analyzing directional resonance")
        
        results = {}
        
        # Calculate resonance between focus words
        for word1 in self.focus_words:
            word_results = {}
            for word2 in self.focus_words:
                if word1 != word2:
                    score = self.resonance.compute_directional_resonance(word1, word2)
                    if score > 0:
                        word_results[word2] = score
            
            if word_results:
                results[word1] = word_results
        
        # Save results
        self.results["directional_resonance"] = results
        
        # Create resonance heatmap
        self._create_resonance_heatmap(results)
        
        logger.info(f"Directional resonance analyzed for {len(results)} focus words")
    
    def _create_resonance_heatmap(self, resonance_results):
        """Create a heatmap of resonance between focus words."""
        # Get all words with resonance data
        words = [word for word in self.focus_words if word in resonance_results]
        
        if not words or len(words) < 2: # Heatmap needs at least 2 words
            logger.warning("Not enough resonance data to create a heatmap.")
            return
        
        # Create matrix of resonance values
        matrix = np.zeros((len(words), len(words)))
        for i, word1 in enumerate(words):
            for j, word2 in enumerate(words):
                if word1 != word2 and word2 in resonance_results.get(word1, {}):
                    matrix[i, j] = resonance_results[word1][word2]
        
        # Create heatmap
        plt.figure(figsize=(12, 10))
        plt.imshow(matrix, cmap='viridis')
        plt.colorbar(label='Resonance Strength')
        plt.title('Directional Resonance Between Focus Words')
        plt.xticks(range(len(words)), words, rotation=90)
        plt.yticks(range(len(words)), words)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "plots", "resonance_heatmap.png"))
        plt.close()
    
    def _analyze_context_clouds(self):
        """Analyze context clouds for focus words."""
        logger.info("Analyzing context clouds")
        
        results = {}
        
        # Get clouds for focus words
        for word in self.focus_words:
            cloud = self.cloud_manager.get_cloud(word)
            strengths = self.cloud_manager.get_cloud_with_strengths(word)
            
            if cloud:
                results[word] = {
                    "cloud_members": list(cloud),
                    "cloud_strengths": strengths
                }
        
        # Save results
        self.results["context_clouds"] = results
        
        # Create cloud size distribution
        cloud_sizes = [len(cloud) for cloud in self.cloud_manager.clouds.values() if len(cloud) > 0]
        if cloud_sizes:
            plt.figure(figsize=(10, 6))
            plt.hist(cloud_sizes, bins=10)
            plt.title("Context Cloud Size Distribution")
            plt.xlabel("Cloud Size")
            plt.ylabel("Frequency")
            plt.savefig(os.path.join(self.output_dir, "plots", "cloud_size_distribution.png"))
            plt.close()
        
        logger.info(f"Context clouds analyzed for {len(results)} focus words")
    
    def _export_results(self):
        """Export all results to files."""
        logger.info("Exporting results")
        
        # Export context map
        self.context_parser.export_context_map(os.path.join(self.output_dir, "context_map.json"))
        
        # Export context clouds
        self.cloud_manager.export_clouds(os.path.join(self.output_dir, "context_clouds.json"))
        
        # Export analysis results
        with open(os.path.join(self.output_dir, "analysis_results.json"), "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate summary report
        self._generate_summary_report()
        
        logger.info(f"Results exported to {self.output_dir}")
    
    def _generate_summary_report(self):
        # This function remains largely the same, but will now use the dynamic focus_words.
        # It's already robust enough to handle cases where results are empty.
        logger.info("Generating summary report")
        
        total_words = len(self.context_parser.context_map)
        total_relationships = sum(len(p) for p in self.context_parser.context_map.values())
        total_clouds = len(self.cloud_manager.clouds)
        cloud_sizes = [len(c) for c in self.cloud_manager.clouds.values() if len(c) > 0]
        avg_cloud_size = sum(cloud_sizes) / len(cloud_sizes) if cloud_sizes else 0
        
        report = f"""# Story Analysis Report

## Summary Statistics
- **Total Unique Words Analyzed**: {total_words}
- **Total Context Relationships**: {total_relationships}
- **Total Context Clouds**: {total_clouds}
- **Average Cloud Size**: {avg_cloud_size:.2f}
"""
        
        if self.results.get("context_windows"):
            report += "\n## Focus Words Context Windows\n"
            for word in list(self.results["context_windows"].keys())[:5]: # Show top 5
                report += f"\n### '{word}' Context Window\n"
                context = self.results["context_windows"][word]
                report += "**Left Context:** " + ", ".join(context.get('-1',[])) + "\n"
                report += "**Right Context:** " + ", ".join(context.get('1',[])) + "\n"
        
        if self.results.get("directional_resonance"):
            report += "\n## Top 10 Directional Resonance Pairs\n"
            all_pairs = []
            for word1, resonances in self.results["directional_resonance"].items():
                for word2, score in resonances.items():
                    all_pairs.append((word1, word2, score))
            all_pairs.sort(key=lambda x: x[2], reverse=True)
            for word1, word2, score in all_pairs[:10]:
                report += f"- '{word1}' → '{word2}': {score:.4f}\n"

        if self.results.get("context_clouds"):
            report += "\n## Top 5 Largest Context Clouds\n"
            cloud_sizes_list = sorted(
                self.results["context_clouds"].items(),
                key=lambda item: len(item[1]["cloud_members"]),
                reverse=True
            )
            for word, data in cloud_sizes_list[:5]:
                size = len(data["cloud_members"])
                report += f"\n### '{word}' Cloud (Size: {size})\n"
                members = data["cloud_members"]
                report += f"Members: {', '.join(members[:10])}"
                if len(members) > 10:
                    report += f", and {len(members) - 10} more."
                report += "\n"
        
        report += "\n## Conclusion\n"
        report += "The 6-1-6 Relation Model successfully created a contextual lattice for the story."

        with open(os.path.join(self.output_dir, "summary_report.md"), "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Summary report generated")


# --- MODIFICATION START ---
# Replaced argparse with interactive input() for main execution.
def main():
    """Main function to process the story."""
    print("--- Story Context Analyzer ---")

    # 1. Get story file path
    story_path = input("Enter the full path to the story file (e.g., C:\\Users\\YourUser\\Documents\\story.txt): ")
    if not os.path.exists(story_path):
        logger.error(f"Story file not found at: {story_path}")
        return

    # 2. Get YAML config file path
    yaml_path = input("Enter the full path to your word config YAML file (e.g., C:\\Users\\YourUser\\Documents\\config.yml): ")
    if not os.path.exists(yaml_path):
        logger.error(f"YAML config file not found at: {yaml_path}")
        return
        
    # 3. Get output directory
    default_output = "C:\\story_analysis"
    output_dir = input(f"Enter the path for the output directory (press Enter to use '{default_output}'): ")
    if not output_dir:
        output_dir = default_output

    # Load words from YAML configuration
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Use .get() to avoid errors if keys are missing
        include_words = config.get('include_words', [])
        exclude_words = config.get('exclude_words', [])
        
        # Validate that they are lists
        if not isinstance(include_words, list) or not isinstance(exclude_words, list):
            logger.error("YAML file must contain 'include_words' and 'exclude_words' as lists (e.g., using '- word').")
            return

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to read or process YAML file: {e}")
        return

    analyzer = StoryAnalyzer(output_dir=output_dir)
    analyzer.process_story(story_path, include_words, exclude_words)

# --- MODIFICATION END ---


if __name__ == "__main__":
    main()