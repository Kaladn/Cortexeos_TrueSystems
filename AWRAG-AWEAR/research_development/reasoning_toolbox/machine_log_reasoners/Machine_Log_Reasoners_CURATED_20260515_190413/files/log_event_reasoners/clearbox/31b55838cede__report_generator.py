"""
Report Generator
Generates markdown cognitive analysis reports.
Output path: absolute, anchored to ~/.clearbox/market_oracle/reports/
"""

from datetime import datetime
from pathlib import Path


class ReportGenerator:
    """Generates cognitive analysis reports."""

    def __init__(self, config):
        self.config = config
        # Resolve to absolute path regardless of CWD
        self.reports_dir = Path(config['output']['reports_dir']).expanduser().resolve()
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, ticker, market_data, capsules, causal_results, patterns, metrics):
        """
        Generate complete cognitive analysis report.

        Args:
            ticker:        str
            market_data:   list[{date,open,high,low,close,volume}]
            capsules:      list[capsule_dict]
            causal_results: dict[index → {consistency,ncv_73,backward_score,forward_score}]
            patterns:      {pattern_breaks,causal_chains,anomalies}
            metrics:       {avg_consistency,avg_volatility,...,verdict,risk,grade}

        Returns:
            str: Absolute path to generated .md file
        """
        report = self._build_report(ticker, market_data, capsules, patterns, metrics)
        filename = self.reports_dir / f"{ticker}_616_COGNITIVE_ANALYSIS.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return str(filename)

    def _build_report(self, ticker, market_data, capsules, patterns, metrics):
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
- **Total Predictable Days:** {sum([c['length'] for c in patterns['causal_chains']], 0)}

### Causal Anomalies
- **Total Detected:** {metrics['num_anomalies']}
- **Rate:** {metrics['anomaly_rate']:.1f}% of trading days

### Volatility
- **Average Daily Change:** {metrics['avg_volatility']:.2f}%

---

## 6-1-6 VERDICT

**Cognitive Assessment:** {metrics['verdict']}
**Risk Level:** {metrics['risk']}
**Investment Grade:** {metrics['grade']}

---

## METHODOLOGY

6-1-6 temporal capsules: 6 prev positions + 1 anchor + 6 next positions = 13-point window.
NCV-73: 36 prev dims + 1 anchor dim + 36 next dims = 73-dimensional causal context vector.
Bidirectional validation: backward (anchor follows prev pattern) + forward (next follows anchor).
Causal consistency = (backward_score + forward_score) / 2. Range 0.0 (chaos) to 1.0 (predictable).
Pattern break threshold: {self.config['analysis']['pattern_break_threshold']}% price change.
Causal chain threshold: consistency >= {self.config['analysis']['causal_consistency_high']}.
Anomaly threshold: consistency < {self.config['analysis']['causal_consistency_low']}.

**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Engine:** CRSA-616 Cognitive Substrate
**Developed by:** Shadow Wolf / YourNightmare

---

*This analysis is for informational purposes only and does not constitute investment advice.*
"""
