"""
Report Generator
Generates markdown cognitive analysis reports
"""

from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """Generates cognitive analysis reports"""
    
    def __init__(self, config):
        self.config = config
        self.reports_dir = Path(config['output']['reports_dir'])
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, ticker, market_data, capsules, causal_results, patterns, metrics):
        """
        Generate complete cognitive analysis report
        
        Args:
            ticker: Stock/crypto ticker symbol
            market_data: Raw market data
            capsules: 6-1-6 temporal capsules
            causal_results: Causal analysis results
            patterns: Detected patterns
            metrics: Calculated metrics
        
        Returns:
            str: Path to generated report file
        """
        report = self._build_report(ticker, market_data, capsules, patterns, metrics)
        
        filename = self.reports_dir / f"{ticker}_616_COGNITIVE_ANALYSIS.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        return str(filename)
    
    def _build_report(self, ticker, market_data, capsules, patterns, metrics):
        """Build report content"""
        return f"""# {ticker} - 6-1-6 COGNITIVE SUBSTRATE ANALYSIS

## EXECUTIVE SUMMARY

**Ticker:** {ticker}  
**Analysis Period:** {market_data[0]['date']} to {market_data[-1]['date']}  
**Trading Days Analyzed:** {len(capsules)}

---

## COGNITIVE METRICS

### Causal Consistency
- **Average:** {metrics['avg_consistency']:.3f}
- **Interpretation:** {"High predictability" if metrics['avg_consistency'] > 0.6 else "Moderate predictability" if metrics['avg_consistency'] > 0.4 else "Low predictability" if metrics['avg_consistency'] > 0.25 else "Chaotic behavior"}

### Pattern Breaks
- **Total Detected:** {metrics['num_pattern_breaks']}
- **Rate:** {metrics['pattern_break_rate']:.1f}% of trading days
- **Spikes (>5% up):** {len([pb for pb in patterns['pattern_breaks'] if pb['type'] == 'spike'])}
- **Crashes (>5% down):** {len([pb for pb in patterns['pattern_breaks'] if pb['type'] == 'crash'])}

### Causal Chains
- **Total Detected:** {metrics['num_causal_chains']}
- **Longest Chain:** {max([c['length'] for c in patterns['causal_chains']], default=0)} days
- **Total Predictable Days:** {sum([c['length'] for c in patterns['causal_chains']]) if patterns['causal_chains'] else 0}

### Causal Anomalies
- **Total Detected:** {metrics['num_anomalies']}
- **Rate:** {metrics['anomaly_rate']:.1f}% of trading days
- **Interpretation:** Days where consequence defied cause

### Volatility
- **Average Daily Change:** {metrics['avg_volatility']:.2f}%
- **Interpretation:** {"Low volatility" if metrics['avg_volatility'] < 2 else "Moderate volatility" if metrics['avg_volatility'] < 5 else "High volatility"}

---

## 6-1-6 VERDICT

**Cognitive Assessment:** {metrics['verdict']}  
**Risk Level:** {metrics['risk']}  
**Investment Grade:** {metrics['grade']}

---

## INTERPRETATION

### What the 6-1-6 Architecture Reveals

The CRSA-616 cognitive substrate analyzes {ticker} through **73-dimensional causal context** (36 previous + 1 anchor + 36 next possibilities). Each trading day is evaluated for:

1. **Backward Validation:** Does today's price follow from previous pattern?
2. **Forward Validation:** Does future price follow from today's action?
3. **Causal Consistency:** Do cause and consequence align?

### Key Findings

The analysis reveals a causal consistency of {metrics['avg_consistency']:.3f}, indicating {metrics['verdict'].lower()}. With {metrics['num_pattern_breaks']} pattern breaks ({metrics['pattern_break_rate']:.1f}% of days), the asset shows {"frequent" if metrics['pattern_break_rate'] > 20 else "moderate" if metrics['pattern_break_rate'] > 10 else "rare"} unexpected price movements. The detection of {metrics['num_causal_chains']} causal chains suggests {"strong" if metrics['num_causal_chains'] > 10 else "moderate" if metrics['num_causal_chains'] > 5 else "weak" if metrics['num_causal_chains'] > 0 else "no"} predictable sequences in the price action.

Furthermore, {metrics['num_anomalies']} anomalies ({metrics['anomaly_rate']:.1f}% of days) were identified where consequence defied cause, indicating {"high" if metrics['anomaly_rate'] > 50 else "moderate" if metrics['anomaly_rate'] > 30 else "low"} levels of external shock influence on price movements.

---

## INVESTMENT IMPLICATIONS

### For Traders

The causal structure {"supports" if metrics['avg_consistency'] > 0.5 else "undermines"} technical analysis approaches. Pattern breaks are {"frequent and risky" if metrics['pattern_break_rate'] > 15 else "rare and tradeable"}, while the presence of {"multiple" if metrics['num_causal_chains'] > 5 else "few"} causal chains {"enables" if metrics['num_causal_chains'] > 5 else "limits"} momentum trading strategies.

### For Investors

The {"high" if metrics['avg_consistency'] > 0.5 else "low"} consistency suggests {"stable fundamentals" if metrics['avg_consistency'] > 0.5 else "external shocks dominate"}. The {"low" if metrics['avg_volatility'] < 3 else "high"} volatility profile {"supports long-term holding" if metrics['avg_volatility'] < 3 else "requires active management"}. The anomaly rate of {metrics['anomaly_rate']:.1f}% indicates {"rational pricing" if metrics['anomaly_rate'] < 30 else "speculation dominates"}.

---

## METHODOLOGY

This analysis uses the **CRSA-616 (YOURNIGHTMARE) cognitive substrate**:

The analysis employs a deterministic reasoning approach based on count-based statistics rather than probabilistic models. Each trading day is represented as a 6-1-6 temporal capsule containing six previous positions, one anchor position, and six next positions. Bidirectional validation checks both backward consistency (whether today follows from yesterday) and forward consistency (whether tomorrow follows from today). The resulting Nightmare Capsule Vectors (NCV-73) represent 73-dimensional causal context for each position, enabling precise measurement of causal relationships in price movements.

**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Engine:** CRSA-616 Cognitive Substrate  
**Developed by:** Shadow Wolf / CompuCog Systems

---

*This analysis is for informational purposes only and does not constitute investment advice.*
"""
