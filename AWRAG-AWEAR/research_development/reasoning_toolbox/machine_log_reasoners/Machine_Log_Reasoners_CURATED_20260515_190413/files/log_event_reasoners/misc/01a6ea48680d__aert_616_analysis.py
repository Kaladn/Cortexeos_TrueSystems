#!/usr/bin/env python3
"""
AERT Stock Analysis using 6-1-6 Cognitive Substrate Architecture
Applies temporal capsule analysis to detect causal patterns and anomalies
"""

import json
import statistics
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np

def load_data():
    """Load the AERT historical data"""
    with open('/home/ubuntu/aert_full_history.json', 'r') as f:
        data = json.load(f)
    return data

def build_616_capsules(timestamps, quotes):
    """Build 6-1-6 temporal capsules for each trading day"""
    
    capsules = []
    
    for i in range(len(timestamps)):
        # Extract anchor point
        anchor_date = datetime.fromtimestamp(timestamps[i])
        anchor_close = quotes['close'][i] if quotes['close'][i] else 0
        anchor_volume = quotes['volume'][i] if quotes['volume'][i] else 0
        anchor_high = quotes['high'][i] if quotes['high'][i] else 0
        anchor_low = quotes['low'][i] if quotes['low'][i] else 0
        
        if anchor_close == 0:
            continue
        
        # Extract 6 days before (causal context)
        before_context = []
        for j in range(max(0, i-6), i):
            if quotes['close'][j]:
                before_context.append({
                    'date': datetime.fromtimestamp(timestamps[j]),
                    'close': quotes['close'][j],
                    'volume': quotes['volume'][j] if quotes['volume'][j] else 0,
                    'high': quotes['high'][j] if quotes['high'][j] else 0,
                    'low': quotes['low'][j] if quotes['low'][j] else 0
                })
        
        # Extract 6 days after (consequence context)
        after_context = []
        for j in range(i+1, min(len(timestamps), i+7)):
            if quotes['close'][j]:
                after_context.append({
                    'date': datetime.fromtimestamp(timestamps[j]),
                    'close': quotes['close'][j],
                    'volume': quotes['volume'][j] if quotes['volume'][j] else 0,
                    'high': quotes['high'][j] if quotes['high'][j] else 0,
                    'low': quotes['low'][j] if quotes['low'][j] else 0
                })
        
        # Build capsule
        capsule = {
            'index': i,
            'anchor': {
                'date': anchor_date,
                'close': anchor_close,
                'volume': anchor_volume,
                'high': anchor_high,
                'low': anchor_low
            },
            'before': before_context,
            'after': after_context
        }
        
        # Calculate capsule metrics
        capsule['metrics'] = calculate_capsule_metrics(capsule)
        
        capsules.append(capsule)
    
    return capsules

def calculate_capsule_metrics(capsule):
    """Calculate cognitive metrics for a 6-1-6 capsule"""
    
    metrics = {}
    
    anchor = capsule['anchor']
    before = capsule['before']
    after = capsule['after']
    
    # Causal momentum (trend before anchor)
    if len(before) >= 2:
        before_prices = [d['close'] for d in before]
        before_trend = (before_prices[-1] - before_prices[0]) / before_prices[0]
        metrics['causal_momentum'] = before_trend
    else:
        metrics['causal_momentum'] = 0
    
    # Consequence momentum (trend after anchor)
    if len(after) >= 2:
        after_prices = [d['close'] for d in after]
        after_trend = (after_prices[-1] - after_prices[0]) / after_prices[0]
        metrics['consequence_momentum'] = after_trend
    else:
        metrics['consequence_momentum'] = 0
    
    # Volatility (price range relative to close)
    price_range = anchor['high'] - anchor['low']
    metrics['volatility'] = price_range / anchor['close'] if anchor['close'] > 0 else 0
    
    # Volume anomaly (current vs average of context)
    context_volumes = [d['volume'] for d in before + after if d['volume'] > 0]
    if context_volumes:
        avg_volume = statistics.mean(context_volumes)
        metrics['volume_anomaly'] = (anchor['volume'] - avg_volume) / avg_volume if avg_volume > 0 else 0
    else:
        metrics['volume_anomaly'] = 0
    
    # Pattern break (does anchor break the causal trend?)
    if len(before) >= 2:
        expected_price = before[-1]['close'] * (1 + metrics['causal_momentum'])
        actual_price = anchor['close']
        metrics['pattern_break'] = (actual_price - expected_price) / expected_price if expected_price > 0 else 0
    else:
        metrics['pattern_break'] = 0
    
    # Causal consistency (does consequence follow causal momentum?)
    if metrics['causal_momentum'] != 0:
        consistency = 1 - abs(metrics['consequence_momentum'] - metrics['causal_momentum']) / abs(metrics['causal_momentum'])
        metrics['causal_consistency'] = max(0, consistency)
    else:
        metrics['causal_consistency'] = 0
    
    return metrics

def detect_patterns(capsules):
    """Detect causal patterns and anomalies across all capsules"""
    
    patterns = {
        'major_breaks': [],
        'high_volatility': [],
        'volume_spikes': [],
        'causal_chains': [],
        'anomalies': []
    }
    
    for capsule in capsules:
        m = capsule['metrics']
        anchor = capsule['anchor']
        
        # Major pattern breaks (>20% deviation from expected)
        if abs(m['pattern_break']) > 0.20:
            patterns['major_breaks'].append({
                'date': anchor['date'],
                'break_magnitude': m['pattern_break'],
                'price': anchor['close'],
                'type': 'SPIKE' if m['pattern_break'] > 0 else 'CRASH'
            })
        
        # High volatility days (>10% intraday range)
        if m['volatility'] > 0.10:
            patterns['high_volatility'].append({
                'date': anchor['date'],
                'volatility': m['volatility'],
                'price': anchor['close']
            })
        
        # Volume spikes (>200% of context average)
        if m['volume_anomaly'] > 2.0:
            patterns['volume_spikes'].append({
                'date': anchor['date'],
                'volume_anomaly': m['volume_anomaly'],
                'volume': anchor['volume']
            })
        
        # Low causal consistency (consequence doesn't follow cause)
        if m['causal_consistency'] < 0.3 and len(capsule['before']) >= 3 and len(capsule['after']) >= 3:
            patterns['anomalies'].append({
                'date': anchor['date'],
                'consistency': m['causal_consistency'],
                'causal_momentum': m['causal_momentum'],
                'consequence_momentum': m['consequence_momentum']
            })
    
    # Detect causal chains (sequences of consistent momentum)
    chain = []
    for capsule in capsules:
        m = capsule['metrics']
        if m['causal_consistency'] > 0.7:
            chain.append(capsule)
        else:
            if len(chain) >= 5:  # Chain of 5+ days
                patterns['causal_chains'].append({
                    'start_date': chain[0]['anchor']['date'],
                    'end_date': chain[-1]['anchor']['date'],
                    'length': len(chain),
                    'avg_momentum': statistics.mean([c['metrics']['causal_momentum'] for c in chain])
                })
            chain = []
    
    return patterns

def generate_report(capsules, patterns):
    """Generate 6-1-6 cognitive analysis report"""
    
    report = []
    report.append("# AERT STOCK - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Capsules:** {len(capsules)}")
    
    report.append("\n---\n")
    report.append("## PATTERN DETECTION SUMMARY")
    report.append(f"\n**Major Pattern Breaks:** {len(patterns['major_breaks'])} events")
    report.append(f"**High Volatility Days:** {len(patterns['high_volatility'])} events")
    report.append(f"**Volume Spikes:** {len(patterns['volume_spikes'])} events")
    report.append(f"**Causal Chains:** {len(patterns['causal_chains'])} sequences")
    report.append(f"**Anomalies (Low Consistency):** {len(patterns['anomalies'])} events")
    
    # Major breaks
    if patterns['major_breaks']:
        report.append("\n---\n")
        report.append("## MAJOR PATTERN BREAKS (>20% Deviation)")
        report.append("\n| Date | Type | Break Magnitude | Price |")
        report.append("|------|------|-----------------|-------|")
        for event in patterns['major_breaks'][-10:]:
            report.append(f"| {event['date'].strftime('%Y-%m-%d')} | {event['type']} | {event['break_magnitude']*100:+.1f}% | ${event['price']:.2f} |")
    
    # Causal chains
    if patterns['causal_chains']:
        report.append("\n---\n")
        report.append("## CAUSAL CHAINS (Consistent Momentum Sequences)")
        report.append("\n| Start Date | End Date | Length (Days) | Avg Momentum |")
        report.append("|------------|----------|---------------|--------------|")
        for chain in patterns['causal_chains']:
            report.append(f"| {chain['start_date'].strftime('%Y-%m-%d')} | {chain['end_date'].strftime('%Y-%m-%d')} | {chain['length']} | {chain['avg_momentum']*100:+.2f}% |")
    
    # Anomalies
    if patterns['anomalies']:
        report.append("\n---\n")
        report.append("## CAUSAL ANOMALIES (Consequence Doesn't Follow Cause)")
        report.append("\n| Date | Consistency | Causal Momentum | Consequence Momentum |")
        report.append("|------|-------------|-----------------|----------------------|")
        for anomaly in patterns['anomalies'][-10:]:
            report.append(f"| {anomaly['date'].strftime('%Y-%m-%d')} | {anomaly['consistency']:.2f} | {anomaly['causal_momentum']*100:+.1f}% | {anomaly['consequence_momentum']*100:+.1f}% |")
    
    report.append("\n---\n")
    report.append("## COGNITIVE SUBSTRATE INSIGHTS")
    report.append("\n**What the 6-1-6 Analysis Reveals:**")
    report.append("\n1. **Pattern Breaks** indicate external shocks or news events that disrupt causal flow")
    report.append("2. **Causal Chains** show periods of predictable behavior (momentum continues)")
    report.append("3. **Anomalies** flag moments where consequence defies expectation (manipulation or chaos)")
    report.append("4. **Volume Spikes** during pattern breaks suggest institutional activity")
    report.append("5. **Low Causal Consistency** across the dataset indicates a highly manipulated or chaotic stock")
    
    # Calculate overall causal consistency
    if capsules:
        consistencies = [c['metrics']['causal_consistency'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
        if consistencies:
            avg_consistency = statistics.mean(consistencies)
            report.append(f"\n**Overall Causal Consistency:** {avg_consistency:.2f} (0=chaos, 1=predictable)")
            
            if avg_consistency < 0.3:
                verdict = "CHAOTIC - This stock defies causal prediction"
            elif avg_consistency < 0.5:
                verdict = "UNSTABLE - Low predictability, high risk"
            elif avg_consistency < 0.7:
                verdict = "MODERATE - Some predictable patterns exist"
            else:
                verdict = "STABLE - Causal patterns are consistent"
            
            report.append(f"**Verdict:** {verdict}")
    
    # Save report
    report_text = '\n'.join(report)
    with open('/home/ubuntu/AERT_616_COGNITIVE_ANALYSIS.md', 'w') as f:
        f.write(report_text)
    
    print("✓ 6-1-6 Cognitive Analysis Report saved")
    
    return report_text

def create_visualization(capsules, patterns, timestamps, quotes):
    """Create cognitive substrate vision chart"""
    
    print("\nGenerating cognitive substrate vision chart...")
    
    # Prepare data
    dates = [datetime.fromtimestamp(t) for t in timestamps]
    closes = [quotes['close'][i] if quotes['close'][i] else None for i in range(len(timestamps))]
    
    # Create figure with multiple subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle('AERT Stock - 6-1-6 Cognitive Substrate Analysis', fontsize=16, fontweight='bold')
    
    # Subplot 1: Price with pattern breaks highlighted
    ax1.plot(dates, closes, color='#2E86AB', linewidth=1.5, label='Price')
    ax1.set_ylabel('Price ($)', fontsize=12)
    ax1.set_title('Price Timeline with Pattern Breaks', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Highlight major breaks
    for event in patterns['major_breaks']:
        color = '#06D6A0' if event['type'] == 'SPIKE' else '#EF476F'
        ax1.axvline(event['date'], color=color, alpha=0.6, linewidth=2, linestyle='--')
        ax1.scatter(event['date'], event['price'], color=color, s=100, zorder=5, edgecolors='black', linewidth=1.5)
    
    # Subplot 2: Causal consistency over time
    capsule_dates = [c['anchor']['date'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
    consistencies = [c['metrics']['causal_consistency'] for c in capsules if len(c['before']) >= 3 and len(c['after']) >= 3]
    
    ax2.plot(capsule_dates, consistencies, color='#118AB2', linewidth=1.5, label='Causal Consistency')
    ax2.axhline(0.7, color='#06D6A0', linestyle='--', alpha=0.5, label='High Consistency')
    ax2.axhline(0.3, color='#EF476F', linestyle='--', alpha=0.5, label='Low Consistency')
    ax2.fill_between(capsule_dates, 0, consistencies, alpha=0.3, color='#118AB2')
    ax2.set_ylabel('Causal Consistency', fontsize=12)
    ax2.set_title('6-1-6 Causal Consistency (0=Chaos, 1=Predictable)', fontsize=14)
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # Subplot 3: Volume with spikes highlighted
    volumes = [quotes['volume'][i] if quotes['volume'][i] else 0 for i in range(len(timestamps))]
    ax3.bar(dates, volumes, color='#073B4C', alpha=0.6, width=1.0)
    ax3.set_ylabel('Volume', fontsize=12)
    ax3.set_title('Trading Volume with Anomaly Spikes', fontsize=14)
    ax3.grid(True, alpha=0.3)
    
    # Highlight volume spikes
    for spike in patterns['volume_spikes']:
        ax3.axvline(spike['date'], color='#FFD60A', alpha=0.8, linewidth=2, linestyle='--')
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    
    # Add legend to ax1
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#06D6A0', label='Spike (>20% up)'),
        Patch(facecolor='#EF476F', label='Crash (>20% down)'),
        Patch(facecolor='#FFD60A', label='Volume Spike')
    ]
    ax1.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig('/home/ubuntu/AERT_616_VISION.png', dpi=300, bbox_inches='tight')
    print("✓ Cognitive substrate vision chart saved")
    
    return '/home/ubuntu/AERT_616_VISION.png'

def main():
    print("=" * 80)
    print("AERT - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS")
    print("=" * 80)
    
    # Load data
    print("\n[1/5] Loading historical data...")
    data = load_data()
    timestamps = data['timestamp']
    quotes = data['indicators']['quote'][0]
    print(f"✓ Loaded {len(timestamps)} trading days")
    
    # Build 6-1-6 capsules
    print("\n[2/5] Building 6-1-6 temporal capsules...")
    capsules = build_616_capsules(timestamps, quotes)
    print(f"✓ Built {len(capsules)} temporal capsules")
    
    # Detect patterns
    print("\n[3/5] Detecting causal patterns and anomalies...")
    patterns = detect_patterns(capsules)
    print(f"✓ Detected {len(patterns['major_breaks'])} pattern breaks")
    print(f"✓ Detected {len(patterns['causal_chains'])} causal chains")
    print(f"✓ Detected {len(patterns['anomalies'])} anomalies")
    
    # Generate report
    print("\n[4/5] Generating cognitive analysis report...")
    report = generate_report(capsules, patterns)
    
    # Create visualization
    print("\n[5/5] Creating cognitive substrate vision chart...")
    chart_path = create_visualization(capsules, patterns, timestamps, quotes)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Report: AERT_616_COGNITIVE_ANALYSIS.md")
    print(f"Chart: AERT_616_VISION.png")
    print("=" * 80)

if __name__ == "__main__":
    main()
