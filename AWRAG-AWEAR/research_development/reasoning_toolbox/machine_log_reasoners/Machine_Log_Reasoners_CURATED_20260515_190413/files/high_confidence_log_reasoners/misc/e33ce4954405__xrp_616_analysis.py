#!/usr/bin/env python3
"""
XRP (Ripple) - 6-1-6 Cognitive Substrate Analysis
Applies temporal capsule analysis to cryptocurrency data
"""

import sys
sys.path.append('/opt/.manus/.sandbox-runtime')
from data_api import ApiClient
import json
import statistics
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# Import the analysis functions from AERT script
exec(open('/home/ubuntu/aert_616_analysis.py').read().replace('if __name__ == "__main__":', 'if False:'))

def fetch_xrp_data():
    """Fetch XRP historical data"""
    client = ApiClient()
    
    print("=" * 80)
    print("XRP (RIPPLE) - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS")
    print("=" * 80)
    
    try:
        print("\n[1/6] Fetching XRP historical data...")
        response = client.call_api('YahooFinance/get_stock_chart', query={
            'symbol': 'XRP-USD',  # XRP/USD pair
            'region': 'US',
            'interval': '1d',
            'range': 'max',  # Maximum available history
            'includeAdjustedClose': True
        })
        
        if not response or 'chart' not in response or 'result' not in response['chart']:
            print("ERROR: No data returned from API")
            return None
            
        result = response['chart']['result'][0]
        meta = result['meta']
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        
        print(f"✓ Retrieved {len(timestamps)} trading days of data")
        print(f"  Date Range: {datetime.fromtimestamp(timestamps[0]).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(timestamps[-1]).strftime('%Y-%m-%d')}")
        
        # Save raw data
        with open('/home/ubuntu/xrp_full_history.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("✓ Saved to xrp_full_history.json")
        
        return result, timestamps, quotes, meta
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def analyze_xrp():
    """Run full 6-1-6 analysis on XRP"""
    
    # Fetch data
    data = fetch_xrp_data()
    if not data:
        return
    
    result, timestamps, quotes, meta = data
    
    # Build 6-1-6 capsules
    print("\n[2/6] Building 6-1-6 temporal capsules...")
    capsules = build_616_capsules(timestamps, quotes)
    print(f"✓ Built {len(capsules)} temporal capsules")
    
    # Detect patterns
    print("\n[3/6] Detecting causal patterns and anomalies...")
    patterns = detect_patterns(capsules)
    print(f"✓ Detected {len(patterns['major_breaks'])} pattern breaks")
    print(f"✓ Detected {len(patterns['causal_chains'])} causal chains")
    print(f"✓ Detected {len(patterns['anomalies'])} anomalies")
    
    # Calculate statistics
    print("\n[4/6] Calculating cognitive metrics...")
    
    # Overall causal consistency
    consistencies = [c['metrics']['causal_consistency'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
    avg_consistency = statistics.mean(consistencies) if consistencies else 0
    
    # Volatility
    volatilities = [c['metrics']['volatility'] for c in capsules]
    avg_volatility = statistics.mean(volatilities) if volatilities else 0
    
    # Pattern break rate
    break_rate = len(patterns['major_breaks']) / len(capsules) if capsules else 0
    
    # Anomaly rate
    anomaly_rate = len(patterns['anomalies']) / len(capsules) if capsules else 0
    
    stats = {
        'avg_consistency': avg_consistency,
        'avg_volatility': avg_volatility,
        'break_rate': break_rate,
        'anomaly_rate': anomaly_rate,
        'total_capsules': len(capsules),
        'pattern_breaks': len(patterns['major_breaks']),
        'causal_chains': len(patterns['causal_chains']),
        'anomalies': len(patterns['anomalies'])
    }
    
    print(f"  Average Causal Consistency: {avg_consistency:.3f}")
    print(f"  Average Volatility: {avg_volatility*100:.2f}%")
    print(f"  Pattern Break Rate: {break_rate*100:.1f}%")
    print(f"  Anomaly Rate: {anomaly_rate*100:.1f}%")
    
    # Generate report
    print("\n[5/6] Generating cognitive analysis report...")
    generate_xrp_report(capsules, patterns, meta, stats)
    
    # Create visualization
    print("\n[6/6] Creating cognitive substrate vision chart...")
    create_xrp_visualization(capsules, patterns, timestamps, quotes, meta)
    
    print("\n" + "=" * 80)
    print("XRP ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Report: XRP_616_COGNITIVE_ANALYSIS.md")
    print(f"Chart: XRP_616_VISION.png")
    print("=" * 80)
    
    return stats

def generate_xrp_report(capsules, patterns, meta, stats):
    """Generate XRP-specific 6-1-6 report"""
    
    report = []
    report.append("# XRP (RIPPLE) - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Capsules:** {len(capsules)}")
    report.append(f"**Current Price:** ${meta['regularMarketPrice']:.4f}")
    
    report.append("\n---\n")
    report.append("## COGNITIVE METRICS SUMMARY")
    report.append(f"\n**Average Causal Consistency:** {stats['avg_consistency']:.3f} (0=chaos, 1=predictable)")
    report.append(f"**Average Daily Volatility:** {stats['avg_volatility']*100:.2f}%")
    report.append(f"**Pattern Break Rate:** {stats['break_rate']*100:.1f}% of trading days")
    report.append(f"**Anomaly Rate:** {stats['anomaly_rate']*100:.1f}% of trading days")
    
    # Verdict based on consistency
    if stats['avg_consistency'] < 0.3:
        verdict = "CHAOTIC - Defies causal prediction"
        risk = "EXTREME"
    elif stats['avg_consistency'] < 0.5:
        verdict = "UNSTABLE - Low predictability"
        risk = "HIGH"
    elif stats['avg_consistency'] < 0.7:
        verdict = "MODERATE - Some predictable patterns"
        risk = "MEDIUM"
    else:
        verdict = "STABLE - Consistent causal patterns"
        risk = "LOW-MEDIUM"
    
    report.append(f"\n**Cognitive Verdict:** {verdict}")
    report.append(f"**Risk Level:** {risk}")
    
    report.append("\n---\n")
    report.append("## PATTERN DETECTION SUMMARY")
    report.append(f"\n**Major Pattern Breaks:** {len(patterns['major_breaks'])} events")
    report.append(f"**Causal Chains:** {len(patterns['causal_chains'])} sequences")
    report.append(f"**Causal Anomalies:** {len(patterns['anomalies'])} events")
    
    # Major breaks
    if patterns['major_breaks']:
        report.append("\n---\n")
        report.append("## MAJOR PATTERN BREAKS (>20% Deviation)")
        report.append("\n| Date | Type | Break Magnitude | Price |")
        report.append("|------|------|-----------------|-------|")
        for event in patterns['major_breaks'][-15:]:  # Last 15 events
            report.append(f"| {event['date'].strftime('%Y-%m-%d')} | {event['type']} | {event['break_magnitude']*100:+.1f}% | ${event['price']:.4f} |")
    
    # Causal chains
    if patterns['causal_chains']:
        report.append("\n---\n")
        report.append("## CAUSAL CHAINS (Consistent Momentum Sequences)")
        report.append("\n| Start Date | End Date | Length (Days) | Avg Momentum |")
        report.append("|------------|----------|---------------|--------------|")
        for chain in patterns['causal_chains']:
            report.append(f"| {chain['start_date'].strftime('%Y-%m-%d')} | {chain['end_date'].strftime('%Y-%m-%d')} | {chain['length']} | {chain['avg_momentum']*100:+.2f}% |")
    
    report.append("\n---\n")
    report.append("## COMPARISON TO AERT (Stock)")
    report.append("\nXRP vs AERT Cognitive Metrics:")
    report.append("\n| Metric | XRP | AERT | Winner |")
    report.append("|--------|-----|------|--------|")
    report.append(f"| Causal Consistency | {stats['avg_consistency']:.3f} | ~0.25 | {'XRP' if stats['avg_consistency'] > 0.25 else 'AERT'} |")
    report.append(f"| Pattern Break Rate | {stats['break_rate']*100:.1f}% | 28.1% | {'XRP' if stats['break_rate'] < 0.281 else 'AERT'} |")
    report.append(f"| Anomaly Rate | {stats['anomaly_rate']*100:.1f}% | 70.0% | {'XRP' if stats['anomaly_rate'] < 0.70 else 'AERT'} |")
    report.append(f"| Causal Chains | {len(patterns['causal_chains'])} | 2 | {'XRP' if len(patterns['causal_chains']) > 2 else 'AERT'} |")
    
    report.append("\n---\n")
    report.append("## COGNITIVE SUBSTRATE INSIGHTS")
    report.append("\n**What the 6-1-6 Analysis Reveals:**")
    report.append("\n1. **Causal Consistency** measures how predictable XRP's price movements are")
    report.append("2. **Pattern Breaks** indicate external shocks (SEC news, adoption announcements, market crashes)")
    report.append("3. **Causal Chains** show periods where XRP follows predictable momentum")
    report.append("4. **Anomalies** flag moments where consequence defies expectation")
    
    if stats['avg_consistency'] > 0.5:
        report.append("\n**XRP shows HIGHER causal consistency than AERT, suggesting:**")
        report.append("- More predictable price behavior")
        report.append("- Stronger market structure")
        report.append("- Better risk/reward profile for technical analysis")
    else:
        report.append("\n**XRP shows LOW causal consistency, suggesting:**")
        report.append("- Highly reactive to external news")
        report.append("- Speculative trading dominates")
        report.append("- Difficult to predict with traditional methods")
    
    # Save report
    report_text = '\n'.join(report)
    with open('/home/ubuntu/XRP_616_COGNITIVE_ANALYSIS.md', 'w') as f:
        f.write(report_text)
    
    print("✓ XRP 6-1-6 Cognitive Analysis Report saved")

def create_xrp_visualization(capsules, patterns, timestamps, quotes, meta):
    """Create XRP cognitive substrate vision chart"""
    
    # Prepare data
    dates = [datetime.fromtimestamp(t) for t in timestamps]
    closes = [quotes['close'][i] if quotes['close'][i] else None for i in range(len(timestamps))]
    
    # Create figure
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle('XRP (Ripple) - 6-1-6 Cognitive Substrate Analysis', fontsize=16, fontweight='bold')
    
    # Subplot 1: Price with pattern breaks
    ax1.plot(dates, closes, color='#FF6B35', linewidth=1.5, label='Price')
    ax1.set_ylabel('Price (USD)', fontsize=12)
    ax1.set_title('Price Timeline with Pattern Breaks', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')  # Log scale for crypto
    
    # Highlight major breaks
    for event in patterns['major_breaks']:
        color = '#06D6A0' if event['type'] == 'SPIKE' else '#EF476F'
        ax1.axvline(event['date'], color=color, alpha=0.5, linewidth=1.5, linestyle='--')
        ax1.scatter(event['date'], event['price'], color=color, s=80, zorder=5, edgecolors='black', linewidth=1)
    
    # Subplot 2: Causal consistency
    capsule_dates = [c['anchor']['date'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
    consistencies = [c['metrics']['causal_consistency'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
    
    ax2.plot(capsule_dates, consistencies, color='#FF6B35', linewidth=1.5, label='Causal Consistency')
    ax2.axhline(0.7, color='#06D6A0', linestyle='--', alpha=0.5, label='High Consistency')
    ax2.axhline(0.3, color='#EF476F', linestyle='--', alpha=0.5, label='Low Consistency')
    ax2.fill_between(capsule_dates, 0, consistencies, alpha=0.3, color='#FF6B35')
    ax2.set_ylabel('Causal Consistency', fontsize=12)
    ax2.set_title('6-1-6 Causal Consistency (0=Chaos, 1=Predictable)', fontsize=14)
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # Subplot 3: Volume
    volumes = [quotes['volume'][i] if quotes['volume'][i] else 0 for i in range(len(timestamps))]
    ax3.bar(dates, volumes, color='#004E89', alpha=0.6, width=1.0)
    ax3.set_ylabel('Volume', fontsize=12)
    ax3.set_title('Trading Volume', fontsize=14)
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.YearLocator())
    plt.xticks(rotation=45)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#06D6A0', label='Spike (>20% up)'),
        Patch(facecolor='#EF476F', label='Crash (>20% down)')
    ]
    ax1.legend(handles=legend_elements, loc='upper left')
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/XRP_616_VISION.png', dpi=300, bbox_inches='tight')
    print("✓ XRP cognitive substrate vision chart saved")

if __name__ == "__main__":
    analyze_xrp()
