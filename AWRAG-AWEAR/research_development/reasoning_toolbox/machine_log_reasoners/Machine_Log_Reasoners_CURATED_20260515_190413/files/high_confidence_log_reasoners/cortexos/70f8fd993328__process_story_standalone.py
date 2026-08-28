#!/usr/bin/env python3
"""
Process "The Basement" story through the standalone contextual lattice generator.
This script uses the 6-1-6 Relation Model to create positional word relationships
and generate concept clouds based on the narrative.
"""

import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

# Import standalone modules
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
    
    def __init__(self, output_dir: str = "/home/ubuntu/basement_analysis"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "plots"), exist_ok=True)
        
        # Initialize components
        self.context_parser = ContextWindowParser(window_size=6, top_k=5)
        
        # Key words to focus on for detailed analysis
        self.focus_words = [
            "ashley", "mom", "frank", "basement", "creature", "creatures", 
            "fear", "dream", "dreams", "evil", "dark", "darkness", "lightning",
            "thunder", "itchy", "scared", "flashlight", "window"
        ]
        
        # Results storage
        self.results = {}
    
    def process_story(self, story_path: str):
        """Process the story and generate contextual lattice."""
        logger.info(f"Processing story: {story_path}")
        
        # Read the story
        with open(story_path, 'r') as f:
            story_text = f.read()
        
        # Parse the text
        self.context_parser.parse_text(story_text)
        self.context_parser.finalize()
        
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
        
        if not words:
            logger.warning("No resonance data to create heatmap")
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
        """Generate a summary report of the analysis."""
        logger.info("Generating summary report")
        
        # Count total words in context map
        total_words = len(self.context_parser.context_map)
        
        # Count total context relationships
        total_relationships = sum(
            len(positions) for positions in self.context_parser.context_map.values()
        )
        
        # Count total clouds
        total_clouds = len(self.cloud_manager.clouds)
        
        # Calculate average cloud size
        cloud_sizes = [len(cloud) for cloud in self.cloud_manager.clouds.values() if len(cloud) > 0]
        avg_cloud_size = sum(cloud_sizes) / len(cloud_sizes) if cloud_sizes else 0
        
        # Generate report
        report = f"""# The Basement - Contextual Lattice Analysis

## Summary Statistics

- **Total Words Analyzed**: {total_words}
- **Total Context Relationships**: {total_relationships}
- **Total Context Clouds**: {total_clouds}
- **Average Cloud Size**: {avg_cloud_size:.2f}

## Focus Words Analysis

### Context Windows
The following focus words were analyzed with the 6-1-6 context window model:

"""
        
        # Add focus words with context windows
        focus_words_with_context = [
            word for word in self.focus_words 
            if word in self.results.get("context_windows", {})
        ]
        
        for word in focus_words_with_context[:5]:  # Show top 5 for brevity
            report += f"### '{word}' Context Window\n\n"
            context = self.results["context_windows"][word]
            
            # Show left context
            report += "**Left Context (Previous Words):**\n\n"
            for pos in sorted([p for p in context.keys() if int(p) < 0]):
                report += f"Position {pos}: {', '.join(context[pos])}\n\n"
            
            # Show right context
            report += "**Right Context (Following Words):**\n\n"
            for pos in sorted([p for p in context.keys() if int(p) > 0]):
                report += f"Position {pos}: {', '.join(context[pos])}\n\n"
            
            report += "---\n\n"
        
        # Add resonance information
        report += "## Directional Resonance\n\n"
        report += "The following pairs of words have the strongest resonance:\n\n"
        
        # Find top resonance pairs
        all_pairs = []
        for word1, resonances in self.results.get("directional_resonance", {}).items():
            for word2, score in resonances.items():
                all_pairs.append((word1, word2, score))
        
        # Sort by resonance score
        all_pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Show top 10 pairs
        for word1, word2, score in all_pairs[:10]:
            report += f"- '{word1}' → '{word2}': {score:.4f}\n"
        
        report += "\n## Context Clouds\n\n"
        report += "The following focus words have the largest context clouds:\n\n"
        
        # Find words with largest clouds
        cloud_sizes = [
            (word, len(data["cloud_members"]))
            for word, data in self.results.get("context_clouds", {}).items()
        ]
        
        # Sort by cloud size
        cloud_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Show top 5 clouds
        for word, size in cloud_sizes[:5]:
            report += f"### '{word}' Cloud (Size: {size})\n\n"
            cloud_members = self.results["context_clouds"][word]["cloud_members"]
            report += f"Members: {', '.join(cloud_members[:10])}"
            if len(cloud_members) > 10:
                report += f" and {len(cloud_members) - 10} more"
            report += "\n\n"
        
        report += "## Conclusion\n\n"
        report += """The 6-1-6 Relation Model has successfully created a contextual lattice for "The Basement" story.
This model captures the positional relationships between words and builds concept clouds based on these relationships.
The directional resonance between words reflects the semantic structure of the narrative, with stronger connections
between words that appear in similar contexts.

The next step would be to implement the Binary Cell Structure for efficient storage of this contextual data,
which will enable more sophisticated semantic analysis and reasoning."""
        
        # Write report to file
        with open(os.path.join(self.output_dir, "summary_report.md"), "w") as f:
            f.write(report)
        
        logger.info("Summary report generated")


def main():
    """Main function to process the story."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process story through contextual lattice generator")
    parser.add_argument("--story", type=str, default="/home/ubuntu/upload/The Basement.txt", help="Path to story file")
    parser.add_argument("--output-dir", type=str, default="/home/ubuntu/basement_analysis", help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    analyzer = StoryAnalyzer(output_dir=args.output_dir)
    analyzer.process_story(args.story)


if __name__ == "__main__":
    main()
