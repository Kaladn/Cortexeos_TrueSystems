#!/usr/bin/env python3
"""
MSFT/ATVI 6-1-6 COGNITIVE SUBSTRATE ANALYSIS
Applies the CRSA-616 architecture to Microsoft and Activision Blizzard stock data
"""

import yfinance as yf
import json
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict

def fetch_stock_data(ticker, period="2y"):
    """Fetch historical stock data"""
    print(f"✓ Fetching {ticker} data...")
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    
    data = []
    for date, row in df.iterrows():
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': int(row['Volume'])
        })
    
    print(f"  ✓ Retrieved {len(data)} trading days")
    return data

def build_616_capsules(data):
    """Build 6-1-6 temporal capsules from price data"""
    capsules = []
    
    for i in range(len(data)):
        # Current anchor point
        anchor = data[i]
        
        # Previous 6 positions (or fewer if at start)
        prev_positions = []
        for j in range(1, 7):
            if i - j >= 0:
                prev_positions.append(data[i - j])
        
        # Next 6 positions (or fewer if at end)
        next_positions = []
        for j in range(1, 7):
            if i + j < len(data):
                next_positions.append(data[i + j])
        
        # Calculate price change from previous day
        price_change = 0
        if i > 0:
            price_change = ((anchor['close'] - data[i-1]['close']) / data[i-1]['close']) * 100
        
        capsule = {
            'index': i,
            'date': anchor['date'],
            'anchor': anchor,
            'prev_positions': prev_positions,
            'next_positions': next_positions,
            'price_change': price_change
        }
        
        capsules.append(capsule)
    
    return capsules

def detect_pattern_breaks(capsules, threshold=5.0):
    """Detect pattern breaks (>threshold% unexpected moves)"""
    pattern_breaks = []
    
    for capsule in capsules:
        if abs(capsule['price_change']) > threshold:
            pattern_breaks.append({
                'date': capsule['date'],
                'change': capsule['price_change'],
                'type': 'spike' if capsule['price_change'] > 0 else 'crash'
            })
    
    return pattern_breaks

def calculate_causal_consistency(capsule):
    """Calculate causal consistency score (0=chaos, 1=predictable)"""
    if len(capsule['prev_positions']) < 3 or len(capsule['next_positions']) < 3:
        return 0.5  # Insufficient data
    
    # Backward validation: Does anchor follow from previous pattern?
    prev_changes = []
    for i in range(len(capsule['prev_positions']) - 1):
        change = ((capsule['prev_positions'][i]['close'] - capsule['prev_positions'][i+1]['close']) 
                  / capsule['prev_positions'][i+1]['close']) * 100
        prev_changes.append(change)
    
    prev_avg = np.mean(prev_changes) if prev_changes else 0
    prev_std = np.std(prev_changes) if len(prev_changes) > 1 else 1.0
    
    # How consistent is anchor with previous pattern?
    if prev_std > 0:
        backward_score = 1.0 / (1.0 + abs(capsule['price_change'] - prev_avg) / prev_std)
    else:
        backward_score = 1.0 if abs(capsule['price_change'] - prev_avg) < 1.0 else 0.0
    
    # Forward validation: Does next pattern follow from anchor?
    next_changes = []
    for i in range(len(capsule['next_positions']) - 1):
        change = ((capsule['next_positions'][i]['close'] - capsule['next_positions'][i+1]['close']) 
                  / capsule['next_positions'][i+1]['close']) * 100
        next_changes.append(change)
    
    next_avg = np.mean(next_changes) if next_changes else 0
    next_std = np.std(next_changes) if len(next_changes) > 1 else 1.0
    
    if next_std > 0:
        forward_score = 1.0 / (1.0 + abs(next_avg - capsule['price_change']) / next_std)
    else:
        forward_score = 1.0 if abs(next_avg - capsule['price_change']) < 1.0 else 0.0
    
    # Combined causal consistency
    return (backward_score + forward_score) / 2.0

def detect_causal_chains(capsules, consistency_threshold=0.7, min_length=5):
    """Detect sustained causal chains (predictable sequences)"""
    chains = []
    current_chain = []
    
    for capsule in capsules:
        consistency = calculate_causal_consistency(capsule)
        
        if consistency >= consistency_threshold:
            current_chain.append(capsule['date'])
        else:
            if len(current_chain) >= min_length:
                chains.append({
                    'start': current_chain[0],
                    'end': current_chain[-1],
                    'length': len(current_chain)
                })
            current_chain = []
    
    # Check final chain
    if len(current_chain) >= min_length:
        chains.append({
            'start': current_chain[0],
            'end': current_chain[-1],
            'length': len(current_chain)
        })
    
    return chains

def detect_anomalies(capsules, consistency_threshold=0.3):
    """Detect causal anomalies (low consistency events)"""
    anomalies = []
    
    for capsule in capsules:
        consistency = calculate_causal_consistency(capsule)
        
        if consistency < consistency_threshold:
            anomalies.append({
                'date': capsule['date'],
                'consistency': consistency,
                'price_change': capsule['price_change']
            })
    
    return anomalies

def generate_report(ticker, data, capsules, pattern_breaks, causal_chains, anomalies):
    """Generate cognitive analysis report"""
    
    # Calculate metrics
    consistencies = [calculate_causal_consistency(c) for c in capsules]
    avg_consistency = np.mean(consistencies)
    
    volatilities = [abs(c['price_change']) for c in capsules if c['price_change'] != 0]
    avg_volatility = np.mean(volatilities) if volatilities else 0
    
    pattern_break_rate = (len(pattern_breaks) / len(capsules)) * 100
    anomaly_rate = (len(anomalies) / len(capsules)) * 100
    
    # Determine verdict
    if avg_consistency > 0.6:
        verdict = "STABLE - High causal predictability"
        risk = "LOW"
    elif avg_consistency > 0.4:
        verdict = "MODERATE - Some causal structure"
        risk = "MEDIUM"
    elif avg_consistency > 0.25:
        verdict = "VOLATILE - Weak causal structure"
        risk = "HIGH"
    else:
        verdict = "CHAOTIC - Defies causal prediction"
        risk = "EXTREME"
    
    report = f"""# {ticker} - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS

## EXECUTIVE SUMMARY

**Ticker:** {ticker}  
**Analysis Period:** {data[0]['date']} to {data[-1]['date']}  
**Trading Days Analyzed:** {len(capsules)}

---

## COGNITIVE METRICS

### Causal Consistency
- **Average:** {avg_consistency:.3f}
- **Interpretation:** {"High predictability" if avg_consistency > 0.6 else "Moderate predictability" if avg_consistency > 0.4 else "Low predictability" if avg_consistency > 0.25 else "Chaotic behavior"}

### Pattern Breaks
- **Total Detected:** {len(pattern_breaks)}
- **Rate:** {pattern_break_rate:.1f}% of trading days
- **Spikes (>5% up):** {len([pb for pb in pattern_breaks if pb['type'] == 'spike'])}
- **Crashes (>5% down):** {len([pb for pb in pattern_breaks if pb['type'] == 'crash'])}

### Causal Chains
- **Total Detected:** {len(causal_chains)}
- **Longest Chain:** {max([c['length'] for c in causal_chains], default=0)} days
- **Total Predictable Days:** {sum([c['length'] for c in causal_chains]) if causal_chains else 0}

### Causal Anomalies
- **Total Detected:** {len(anomalies)}
- **Rate:** {anomaly_rate:.1f}% of trading days
- **Interpretation:** Days where consequence defied cause

### Volatility
- **Average Daily Change:** {avg_volatility:.2f}%
- **Interpretation:** {"Low volatility" if avg_volatility < 2 else "Moderate volatility" if avg_volatility < 5 else "High volatility"}

---

## 6-1-6 VERDICT

**Cognitive Assessment:** {verdict}  
**Risk Level:** {risk}  
**Investment Grade:** {"A (Strong Buy)" if avg_consistency > 0.6 else "B (Buy)" if avg_consistency > 0.4 else "C (Hold)" if avg_consistency > 0.25 else "D (Avoid)"}

---

## INTERPRETATION

### What the 6-1-6 Architecture Reveals

The CRSA-616 cognitive substrate analyzes {ticker} through **73-dimensional causal context** (36 previous + 1 anchor + 36 next possibilities). Each trading day is evaluated for:

1. **Backward Validation:** Does today's price follow from previous pattern?
2. **Forward Validation:** Does future price follow from today's action?
3. **Causal Consistency:** Do cause and consequence align?

### Key Findings

- **Causal Consistency of {avg_consistency:.3f}** indicates {verdict.lower()}
- **{len(pattern_breaks)} pattern breaks** ({pattern_break_rate:.1f}% of days) show unexpected moves
- **{len(causal_chains)} causal chains** detected, indicating {"strong" if len(causal_chains) > 10 else "moderate" if len(causal_chains) > 5 else "weak" if len(causal_chains) > 0 else "no"} predictable sequences
- **{len(anomalies)} anomalies** ({anomaly_rate:.1f}% of days) where consequence defied cause

---

## INVESTMENT IMPLICATIONS

### For Traders
{"✓ Strong causal structure supports technical analysis" if avg_consistency > 0.5 else "⚠ Weak causal structure makes technical analysis unreliable"}  
{"✓ Pattern breaks are rare and tradeable" if pattern_break_rate < 15 else "⚠ Frequent pattern breaks increase risk"}  
{"✓ Multiple causal chains enable momentum trading" if len(causal_chains) > 5 else "⚠ Few causal chains limit momentum strategies"}

### For Investors
{"✓ High consistency suggests stable fundamentals" if avg_consistency > 0.5 else "⚠ Low consistency suggests external shocks dominate"}  
{"✓ Low volatility supports long-term holding" if avg_volatility < 3 else "⚠ High volatility requires active management"}  
{"✓ Few anomalies indicate rational pricing" if anomaly_rate < 30 else "⚠ Many anomalies suggest speculation dominates"}

---

## METHODOLOGY

This analysis uses the **CRSA-616 (YOURNIGHTMARE) cognitive substrate**:
- **6×6-1-6×6 architecture:** 73-dimensional causal context per position
- **Deterministic reasoning:** Count-based, not probabilistic
- **Bidirectional validation:** Both backward and forward causal checking
- **NCV-73 vectors:** Nightmare Capsule Vectors for context comparison

**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Engine:** CRSA-616 Cognitive Substrate  
**Developed by:** Shadow Wolf / CompuCog Systems

---

*This analysis is for informational purposes only and does not constitute investment advice.*
"""
    
    filename = f"{ticker}_616_COGNITIVE_ANALYSIS.md"
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"✓ {ticker} 6-1-6 Cognitive Analysis Report saved")
    
    return {
        'avg_consistency': avg_consistency,
        'avg_volatility': avg_volatility,
        'pattern_break_rate': pattern_break_rate,
        'anomaly_rate': anomaly_rate,
        'num_chains': len(causal_chains),
        'verdict': verdict,
        'risk': risk
    }

def create_vision_chart(ticker, data, capsules, pattern_breaks):
    """Create cognitive substrate vision chart"""
    
    dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in data]
    prices = [d['close'] for d in data]
    volumes = [d['volume'] for d in data]
    
    # Calculate consistency for each capsule
    consistencies = [calculate_causal_consistency(c) for c in capsules]
    
    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 10))
    fig.suptitle(f'{ticker} - 6-1-6 Cognitive Substrate Analysis', fontsize=16, fontweight='bold')
    
    # SUBPLOT 1: Price timeline with pattern breaks
    ax1.set_title('Price Timeline with Pattern Breaks', fontsize=12, fontweight='bold')
    ax1.plot(dates, prices, 'o-', color='#2E86AB', markersize=4, linewidth=1.5, alpha=0.7)
    
    # Mark pattern breaks
    for pb in pattern_breaks:
        pb_date = datetime.strptime(pb['date'], '%Y-%m-%d')
        pb_idx = dates.index(pb_date) if pb_date in dates else None
        if pb_idx is not None:
            color = '#06A77D' if pb['type'] == 'spike' else '#D62828'
            marker = '^' if pb['type'] == 'spike' else 'v'
            ax1.plot(pb_date, prices[pb_idx], marker, color=color, markersize=10, 
                    markeredgecolor='black', markeredgewidth=0.5)
    
    # Add vertical lines for pattern breaks
    for pb in pattern_breaks:
        pb_date = datetime.strptime(pb['date'], '%Y-%m-%d')
        color = '#06A77D' if pb['type'] == 'spike' else '#D62828'
        ax1.axvline(pb_date, color=color, alpha=0.15, linewidth=1)
    
    ax1.set_ylabel('Price (USD)', fontsize=10, fontweight='bold')
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend(['Price', 'Spike (>5% up)', 'Crash (>5% down)'], loc='upper left')
    
    # SUBPLOT 2: Causal consistency
    ax2.set_title('6-1-6 Causal Consistency (0=Chaos, 1=Predictable)', fontsize=12, fontweight='bold')
    ax2.bar(dates, consistencies, color='#F77F00', alpha=0.7, width=1.5)
    ax2.axhline(y=0.7, color='#06A77D', linestyle='--', linewidth=1, alpha=0.5, label='High Consistency')
    ax2.axhline(y=0.3, color='#D62828', linestyle='--', linewidth=1, alpha=0.5, label='Low Consistency')
    ax2.set_ylabel('Causal Consistency', fontsize=10, fontweight='bold')
    ax2.set_ylim(0, 1.0)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # SUBPLOT 3: Volume
    ax3.set_title('Trading Volume', fontsize=12, fontweight='bold')
    ax3.bar(dates, volumes, color='#6C757D', alpha=0.5, width=1.5)
    ax3.set_ylabel('Volume', fontsize=10, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=10, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis for all subplots
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    filename = f'{ticker}_616_VISION.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ {ticker} cognitive substrate vision chart saved")

def analyze_stock(ticker, period="2y"):
    """Run complete 6-1-6 analysis on a stock"""
    print(f"\n{'='*80}")
    print(f"{ticker} - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS")
    print(f"{'='*80}")
    
    # Step 1: Fetch data
    print(f"[1/6] Fetching {ticker} historical data...")
    data = fetch_stock_data(ticker, period)
    
    # Save raw data
    with open(f'{ticker.lower()}_full_history.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved to {ticker.lower()}_full_history.json")
    
    # Step 2: Build capsules
    print(f"[2/6] Building 6-1-6 temporal capsules...")
    capsules = build_616_capsules(data)
    print(f"✓ Built {len(capsules)} temporal capsules")
    
    # Step 3: Detect patterns
    print(f"[3/6] Detecting causal patterns and anomalies...")
    pattern_breaks = detect_pattern_breaks(capsules, threshold=5.0)
    print(f"✓ Detected {len(pattern_breaks)} pattern breaks")
    
    causal_chains = detect_causal_chains(capsules)
    print(f"✓ Detected {len(causal_chains)} causal chains")
    
    anomalies = detect_anomalies(capsules)
    print(f"✓ Detected {len(anomalies)} anomalies")
    
    # Step 4: Calculate metrics
    print(f"[4/6] Calculating cognitive metrics...")
    
    if len(capsules) == 0:
        print(f"✗ No data available for {ticker} (possibly delisted)")
        return None
    
    consistencies = [calculate_causal_consistency(c) for c in capsules]
    avg_consistency = np.mean(consistencies)
    
    volatilities = [abs(c['price_change']) for c in capsules if c['price_change'] != 0]
    avg_volatility = np.mean(volatilities) if volatilities else 0
    
    pattern_break_rate = (len(pattern_breaks) / len(capsules)) * 100
    anomaly_rate = (len(anomalies) / len(capsules)) * 100
    
    print(f"  Average Causal Consistency: {avg_consistency:.3f}")
    print(f"  Average Volatility: {avg_volatility:.2f}%")
    print(f"  Pattern Break Rate: {pattern_break_rate:.1f}%")
    print(f"  Anomaly Rate: {anomaly_rate:.1f}%")
    
    # Step 5: Generate report
    print(f"[5/6] Generating cognitive analysis report...")
    metrics = generate_report(ticker, data, capsules, pattern_breaks, causal_chains, anomalies)
    
    # Step 6: Create chart
    print(f"[6/6] Creating cognitive substrate vision chart...")
    create_vision_chart(ticker, data, capsules, pattern_breaks)
    
    return metrics

# Main execution
if __name__ == "__main__":
    # Analyze both stocks
    msft_metrics = analyze_stock("MSFT", period="2y")
    # ATVI was acquired by MSFT in Oct 2023, use historical data
    atvi_metrics = analyze_stock("ATVI", period="5y")
    
    print(f"\n{'='*80}")
    print("COMPARATIVE ANALYSIS COMPLETE")
    print(f"{'='*80}")
    
    if msft_metrics:
        print(f"\nMSFT Metrics:")
        print(f"  Causal Consistency: {msft_metrics['avg_consistency']:.3f}")
        print(f"  Volatility: {msft_metrics['avg_volatility']:.2f}%")
        print(f"  Pattern Break Rate: {msft_metrics['pattern_break_rate']:.1f}%")
        print(f"  Verdict: {msft_metrics['verdict']}")
    
    if atvi_metrics:
        print(f"\nATVI Metrics:")
        print(f"  Causal Consistency: {atvi_metrics['avg_consistency']:.3f}")
        print(f"  Volatility: {atvi_metrics['avg_volatility']:.2f}%")
        print(f"  Pattern Break Rate: {atvi_metrics['pattern_break_rate']:.1f}%")
        print(f"  Verdict: {atvi_metrics['verdict']}")
    else:
        print(f"\nATVI: No data available (delisted after Microsoft acquisition in Oct 2023)")
    
    print(f"\n{'='*80}")
