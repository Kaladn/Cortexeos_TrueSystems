#!/usr/bin/env python3
"""
AERT (Aeries Technology) - Deep Historical Market Analysis
Fetches full market history and generates comprehensive analysis
"""

import sys
sys.path.append('/opt/.manus/.sandbox-runtime')
from data_api import ApiClient
import json
from datetime import datetime
import statistics

def fetch_full_history():
    """Fetch complete historical data for AERT"""
    client = ApiClient()
    
    print("=" * 80)
    print("AERT (AERIES TECHNOLOGY) - DEEP MARKET HISTORY ANALYSIS")
    print("=" * 80)
    
    try:
        # Fetch maximum available historical data
        print("\n[1/4] Fetching full historical data...")
        response = client.call_api('YahooFinance/get_stock_chart', query={
            'symbol': 'AERT',
            'region': 'US',
            'interval': '1d',
            'range': 'max',  # Maximum available history
            'includeAdjustedClose': True,
            'events': 'div,split'
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
        print("\n[2/4] Saving raw historical data...")
        with open('/home/ubuntu/aert_full_history.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("✓ Saved to aert_full_history.json")
        
        # Analyze the data
        print("\n[3/4] Analyzing market history...")
        analysis = analyze_history(timestamps, quotes, meta)
        
        # Generate report
        print("\n[4/4] Generating comprehensive report...")
        generate_report(analysis, meta)
        
        return analysis
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def analyze_history(timestamps, quotes, meta):
    """Perform deep analysis on historical data"""
    
    analysis = {
        'meta': meta,
        'timeline': [],
        'price_stats': {},
        'volume_stats': {},
        'volatility': {},
        'major_events': [],
        'periods': {}
    }
    
    # Build timeline with all data points
    closes = []
    volumes = []
    highs = []
    lows = []
    
    for i in range(len(timestamps)):
        date = datetime.fromtimestamp(timestamps[i])
        close = quotes['close'][i] if quotes['close'][i] else 0
        volume = quotes['volume'][i] if quotes['volume'][i] else 0
        high = quotes['high'][i] if quotes['high'][i] else 0
        low = quotes['low'][i] if quotes['low'][i] else 0
        
        if close > 0:
            closes.append(close)
            volumes.append(volume)
            highs.append(high)
            lows.append(low)
            
            analysis['timeline'].append({
                'date': date.strftime('%Y-%m-%d'),
                'close': close,
                'volume': volume,
                'high': high,
                'low': low
            })
    
    # Calculate statistics
    if closes:
        analysis['price_stats'] = {
            'all_time_high': max(closes),
            'all_time_low': min(closes),
            'current': closes[-1],
            'mean': statistics.mean(closes),
            'median': statistics.median(closes),
            'stdev': statistics.stdev(closes) if len(closes) > 1 else 0
        }
        
        analysis['volume_stats'] = {
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'avg_volume': statistics.mean(volumes),
            'current_volume': volumes[-1]
        }
        
        # Calculate volatility (standard deviation of daily returns)
        daily_returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                daily_return = (closes[i] - closes[i-1]) / closes[i-1]
                daily_returns.append(daily_return)
        
        if daily_returns:
            analysis['volatility'] = {
                'daily_stdev': statistics.stdev(daily_returns),
                'max_gain': max(daily_returns) * 100,
                'max_loss': min(daily_returns) * 100,
                'avg_daily_return': statistics.mean(daily_returns) * 100
            }
        
        # Identify major price movements (>20% in a day)
        for i in range(1, len(analysis['timeline'])):
            prev_close = analysis['timeline'][i-1]['close']
            curr_close = analysis['timeline'][i]['close']
            if prev_close > 0:
                change_pct = ((curr_close - prev_close) / prev_close) * 100
                if abs(change_pct) > 20:
                    analysis['major_events'].append({
                        'date': analysis['timeline'][i]['date'],
                        'change_pct': change_pct,
                        'from': prev_close,
                        'to': curr_close,
                        'type': 'SPIKE' if change_pct > 0 else 'CRASH'
                    })
        
        # Analyze different time periods
        periods = {
            '1_week': 5,
            '1_month': 21,
            '3_months': 63,
            '6_months': 126,
            '1_year': 252,
            '2_years': 504,
            '5_years': 1260
        }
        
        for period_name, days in periods.items():
            if len(closes) >= days:
                period_start = closes[-days]
                period_end = closes[-1]
                period_return = ((period_end - period_start) / period_start) * 100
                analysis['periods'][period_name] = {
                    'start_price': period_start,
                    'end_price': period_end,
                    'return_pct': period_return,
                    'days': days
                }
    
    return analysis

def generate_report(analysis, meta):
    """Generate comprehensive markdown report"""
    
    report = []
    report.append("# AERT (AERIES TECHNOLOGY) - DEEP MARKET HISTORY ANALYSIS")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Data Points:** {len(analysis['timeline'])} trading days")
    
    if analysis['timeline']:
        report.append(f"**Date Range:** {analysis['timeline'][0]['date']} to {analysis['timeline'][-1]['date']}")
    
    report.append("\n---\n")
    
    # Current Status
    report.append("## CURRENT STATUS")
    report.append(f"\n**Current Price:** ${meta['regularMarketPrice']:.2f}")
    report.append(f"**Market Cap:** ${meta.get('marketCap', 0):,}")
    report.append(f"**Exchange:** {meta['exchangeName']}")
    report.append(f"**Currency:** {meta['currency']}")
    
    # Price Statistics
    if analysis['price_stats']:
        ps = analysis['price_stats']
        report.append("\n---\n")
        report.append("## PRICE STATISTICS (ALL-TIME)")
        report.append(f"\n**All-Time High:** ${ps['all_time_high']:.2f}")
        report.append(f"**All-Time Low:** ${ps['all_time_low']:.2f}")
        report.append(f"**Current Price:** ${ps['current']:.2f}")
        report.append(f"**Mean Price:** ${ps['mean']:.2f}")
        report.append(f"**Median Price:** ${ps['median']:.2f}")
        report.append(f"**Standard Deviation:** ${ps['stdev']:.2f}")
        
        # Calculate distance from ATH and ATL
        dist_from_ath = ((ps['current'] - ps['all_time_high']) / ps['all_time_high']) * 100
        dist_from_atl = ((ps['current'] - ps['all_time_low']) / ps['all_time_low']) * 100
        report.append(f"\n**Distance from ATH:** {dist_from_ath:.1f}%")
        report.append(f"**Distance from ATL:** +{dist_from_atl:.1f}%")
    
    # Volatility
    if analysis['volatility']:
        v = analysis['volatility']
        report.append("\n---\n")
        report.append("## VOLATILITY ANALYSIS")
        report.append(f"\n**Daily Volatility (StDev):** {v['daily_stdev']*100:.2f}%")
        report.append(f"**Max Single-Day Gain:** +{v['max_gain']:.2f}%")
        report.append(f"**Max Single-Day Loss:** {v['max_loss']:.2f}%")
        report.append(f"**Avg Daily Return:** {v['avg_daily_return']:.3f}%")
        
        # Volatility rating
        if v['daily_stdev'] > 0.05:
            rating = "EXTREMELY HIGH (High-Risk)"
        elif v['daily_stdev'] > 0.03:
            rating = "HIGH (Speculative)"
        elif v['daily_stdev'] > 0.02:
            rating = "MODERATE"
        else:
            rating = "LOW (Stable)"
        report.append(f"\n**Volatility Rating:** {rating}")
    
    # Volume Statistics
    if analysis['volume_stats']:
        vs = analysis['volume_stats']
        report.append("\n---\n")
        report.append("## VOLUME STATISTICS")
        report.append(f"\n**Current Volume:** {vs['current_volume']:,}")
        report.append(f"**Average Volume:** {vs['avg_volume']:,.0f}")
        report.append(f"**Max Volume:** {vs['max_volume']:,}")
        report.append(f"**Min Volume:** {vs['min_volume']:,}")
        
        volume_vs_avg = (vs['current_volume'] / vs['avg_volume']) * 100
        report.append(f"\n**Current vs Avg:** {volume_vs_avg:.1f}% of average")
    
    # Period Returns
    if analysis['periods']:
        report.append("\n---\n")
        report.append("## PERIOD RETURNS")
        report.append("\n| Period | Start Price | End Price | Return |")
        report.append("|--------|-------------|-----------|--------|")
        
        for period_name, data in sorted(analysis['periods'].items(), key=lambda x: x[1]['days']):
            period_label = period_name.replace('_', ' ').title()
            report.append(f"| {period_label} | ${data['start_price']:.2f} | ${data['end_price']:.2f} | {data['return_pct']:+.1f}% |")
    
    # Major Events
    if analysis['major_events']:
        report.append("\n---\n")
        report.append("## MAJOR PRICE MOVEMENTS (>20% in one day)")
        report.append(f"\n**Total Events:** {len(analysis['major_events'])}")
        report.append("\n| Date | Type | Change | From | To |")
        report.append("|------|------|--------|------|-----|")
        
        # Show last 10 major events
        for event in analysis['major_events'][-10:]:
            report.append(f"| {event['date']} | {event['type']} | {event['change_pct']:+.1f}% | ${event['from']:.2f} | ${event['to']:.2f} |")
    
    # Save report
    report_text = '\n'.join(report)
    with open('/home/ubuntu/AERT_DEEP_ANALYSIS_REPORT.md', 'w') as f:
        f.write(report_text)
    
    print("✓ Report saved to AERT_DEEP_ANALYSIS_REPORT.md")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if analysis['price_stats']:
        ps = analysis['price_stats']
        print(f"All-Time High: ${ps['all_time_high']:.2f}")
        print(f"All-Time Low: ${ps['all_time_low']:.2f}")
        print(f"Current: ${ps['current']:.2f}")
        dist_from_ath = ((ps['current'] - ps['all_time_high']) / ps['all_time_high']) * 100
        print(f"Distance from ATH: {dist_from_ath:.1f}%")
    
    if analysis['volatility']:
        v = analysis['volatility']
        print(f"\nDaily Volatility: {v['daily_stdev']*100:.2f}%")
        print(f"Max Gain: +{v['max_gain']:.2f}%")
        print(f"Max Loss: {v['max_loss']:.2f}%")
    
    if analysis['periods'] and '1_year' in analysis['periods']:
        yr = analysis['periods']['1_year']
        print(f"\n1-Year Return: {yr['return_pct']:+.1f}%")
    
    print(f"\nMajor Events (>20% moves): {len(analysis['major_events'])}")
    print("=" * 80)

if __name__ == "__main__":
    fetch_full_history()
    print("\n✓ Analysis complete. Check AERT_DEEP_ANALYSIS_REPORT.md for full details.")
