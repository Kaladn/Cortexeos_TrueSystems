#!/usr/bin/env python3
"""
R.E.A.P.E.R. ONE-CLICK NETSTAT PROCESSOR
Simple script to process any netstat CSV through cognitive analysis

Usage:
    python3 run_reaper_netstat.py [csv_file]
    
If no CSV file is provided, it will create and process a sample file.

Author: R.E.A.P.E.R. Development Team
Version: 1.0
Date: June 16, 2025
"""

import sys
import os
from reaper_network_analyzer import NetworkCognitiveAnalyzer

def main():
    """One-click netstat processing"""
    print("🔥 R.E.A.P.E.R. ONE-CLICK NETSTAT PROCESSOR")
    print("=" * 55)
    
    # Determine CSV file to process
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        if not os.path.exists(csv_file):
            print(f"❌ Error: File '{csv_file}' not found")
            return
    else:
        csv_file = "sample_netstat.csv"
        if not os.path.exists(csv_file):
            print("📝 No CSV file provided, creating sample data...")
            from reaper_network_analyzer import create_sample_netstat_csv
            create_sample_netstat_csv()
    
    print(f"📂 Processing: {csv_file}")
    print("🧠 Initializing R.E.A.P.E.R. cognitive engine...")
    
    # Initialize analyzer
    analyzer = NetworkCognitiveAnalyzer()
    
    # Process the CSV
    print("🔍 Running cognitive analysis...")
    results = analyzer.process_netstat_csv(csv_file)
    
    # Display summary
    print(f"\\n📊 ANALYSIS SUMMARY")
    print("=" * 30)
    print(f"Total Events Processed: {len(results)}")
    
    # Count by threat level
    threat_counts = {}
    for result in results:
        threat_level = result['threat_classification']
        threat_counts[threat_level] = threat_counts.get(threat_level, 0) + 1
    
    for threat_level, count in threat_counts.items():
        emoji = {"AUTHENTIC": "✅", "SUSPICIOUS": "⚠️", "THREAT": "🚨", "CRITICAL": "💀"}
        print(f"{emoji.get(threat_level, '❓')} {threat_level}: {count}")
    
    # Show high-priority threats
    high_priority = [r for r in results if r['threat_classification'] in ['THREAT', 'CRITICAL']]
    if high_priority:
        print(f"\\n🚨 HIGH PRIORITY THREATS ({len(high_priority)}):")
        print("=" * 40)
        for threat in high_priority:
            print(f"🎯 {threat['process_name']} → {threat['remote_address']}:{threat['remote_port']}")
            print(f"   Level: {threat['threat_classification']} (Score: {threat['threat_level']:.3f})")
            print(f"   Recommendations:")
            for rec in threat['recommendations'][:3]:  # Show top 3 recommendations
                print(f"      {rec}")
            print()
    
    # Show anomaly summary
    summary = analyzer.get_anomaly_summary()
    if summary['total_anomalies'] > 0:
        print(f"📈 ANOMALY DETECTION SUMMARY:")
        print("=" * 35)
        for key, value in summary.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print(f"\\n💾 Results saved to database: {analyzer.db_path}")
    print("🎯 R.E.A.P.E.R. analysis complete!")
    print("💀 'Cognitive resonance reveals network truth' 💀")

if __name__ == "__main__":
    main()

