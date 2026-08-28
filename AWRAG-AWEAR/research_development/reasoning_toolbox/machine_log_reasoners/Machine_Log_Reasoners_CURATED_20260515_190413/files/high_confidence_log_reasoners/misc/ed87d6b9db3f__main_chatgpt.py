#!/usr/bin/env python3
"""
CompuCog ChatGPT Conversation Analyzer - CLI
Analyze ChatGPT conversation history for model changes and quality issues
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from adapters.chatgpt_adapter import ChatGPTAdapter
from core.engine import UnifiedEngine
from workers.conversation_analyzer import ConversationAnalyzer
from query.engine import QueryEngine, WindowQuery


def cmd_analyze_chatgpt(args):
    """Complete ChatGPT conversation analysis pipeline"""
    print(f"\n{'='*60}")
    print(f"COMPUCOG CHATGPT CONVERSATION ANALYZER")
    print(f"{'='*60}")
    
    # Step 1: Ingest HTML
    print(f"\nStep 1/4: Ingesting ChatGPT HTML export")
    adapter = ChatGPTAdapter(
        genome_path=args.genome or "genomes/chatgpt_conversation.json",
        output_dir="data/symbols"
    )
    event_count = adapter.ingest(args.source, args.entity)
    print(f"✓ Ingested {event_count} events")
    
    # Step 2: Process windows
    print(f"\nStep 2/4: Processing conversation windows")
    engine = UnifiedEngine(
        domain="chatgpt",
        data_dir="data",
        window_size=args.window_size or 6,
        top_k=args.top_k or 5
    )
    window_count = engine.process()
    print(f"✓ Created {window_count} windows")
    
    # Step 3: Analyze patterns
    print(f"\nStep 3/4: Analyzing conversation patterns")
    analyzer = ConversationAnalyzer(domain="chatgpt", data_dir="data")
    report = analyzer.analyze(args.entity or Path(args.source).stem)
    
    # Step 4: Display results
    print(f"\nStep 4/4: Analysis Results")
    print(f"\n{'='*60}")
    print(f"CONVERSATION ANALYSIS REPORT")
    print(f"{'='*60}")
    print(f"\nEntity: {report['entity']}")
    print(f"Total Windows: {report['total_windows']}")
    print(f"\nSummary: {report['summary']}")
    
    # Model changes
    if report['model_changes']:
        print(f"\n📊 MODEL CHANGES ({len(report['model_changes'])} detected):")
        for change in report['model_changes']:
            print(f"  • {change['from_model']} → {change['to_model']} at timestamp {change['timestamp']}")
    
    # Quality drops
    if report['quality_drops']:
        print(f"\n⚠️  QUALITY DROPS ({len(report['quality_drops'])} detected):")
        for drop in report['quality_drops']:
            print(f"  • {drop['from_quality']} → {drop['to_quality']} at timestamp {drop['timestamp']}")
    
    # Conversation breaks
    if report['conversation_breaks']:
        print(f"\n🔴 CONVERSATION BREAKS ({len(report['conversation_breaks'])} detected):")
        for break_event in report['conversation_breaks']:
            print(f"  • {break_event['type']} at timestamp {break_event['timestamp']}")
    
    # Model distribution
    if report['model_distribution']:
        print(f"\n📈 MODEL DISTRIBUTION:")
        for model, count in report['model_distribution'].items():
            print(f"  • {model}: {count} occurrences")
    
    # Quality distribution
    if report['quality_distribution']:
        print(f"\n📈 QUALITY DISTRIBUTION:")
        for quality, count in report['quality_distribution'].items():
            print(f"  • {quality}: {count} occurrences")
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*60}")
    
    # Save report if requested
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Report saved to: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="CompuCog ChatGPT Conversation Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze ChatGPT HTML export
  python main_chatgpt.py --source chatgpt_export.html
  
  # Analyze with custom entity name
  python main_chatgpt.py --source chatgpt_export.html --entity "my_conversation"
  
  # Save report to JSON
  python main_chatgpt.py --source chatgpt_export.html --output report.json
        """
    )
    
    parser.add_argument("--source", required=True, help="Path to ChatGPT HTML export file")
    parser.add_argument("--entity", help="Conversation name/ID (default: filename)")
    parser.add_argument("--genome", help="Genome file path (default: genomes/chatgpt_conversation.json)")
    parser.add_argument("--window-size", type=int, default=6, help="Window size (default: 6)")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K symbols (default: 5)")
    parser.add_argument("--output", help="Save report to JSON file")
    
    args = parser.parse_args()
    
    # Run analysis
    cmd_analyze_chatgpt(args)


if __name__ == "__main__":
    main()
