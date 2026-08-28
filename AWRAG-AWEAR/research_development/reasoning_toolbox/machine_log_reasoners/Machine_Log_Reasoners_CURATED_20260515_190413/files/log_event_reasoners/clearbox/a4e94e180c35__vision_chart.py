"""
Vision Chart Generator
Creates cognitive substrate visualization charts.
Output path: absolute, anchored to ~/.clearbox/market_oracle/charts/
"""

from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class VisionChart:
    """Generates cognitive substrate vision charts."""

    def __init__(self, config):
        self.config = config
        # Resolve to absolute path regardless of CWD
        self.charts_dir = Path(config['output']['charts_dir']).expanduser().resolve()
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.dpi    = config['output']['chart_dpi']
        self.width  = config['output']['chart_width']
        self.height = config['output']['chart_height']

    def create(self, ticker, market_data, capsules, causal_results, patterns):
        """
        Create cognitive substrate vision chart (3 subplots).

        Args:
            ticker:         str
            market_data:    list[{date,open,high,low,close,volume}]
            capsules:       list[capsule_dict]
            causal_results: dict[index → {consistency,ncv_73,backward_score,forward_score}]
            patterns:       {pattern_breaks,causal_chains,anomalies}

        Returns:
            str: Absolute path to .png file
        """
        dates        = [datetime.strptime(d['date'], '%Y-%m-%d') for d in market_data]
        prices       = [d['close'] for d in market_data]
        volumes      = [d['volume'] for d in market_data]
        consistencies = [causal_results[c['index']]['consistency'] for c in capsules]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(self.width, self.height))
        fig.suptitle(f'{ticker} — 6-1-6 Cognitive Substrate Analysis',
                     fontsize=16, fontweight='bold')

        # Subplot 1: Price + pattern breaks
        ax1.set_title('Price Timeline with Pattern Breaks', fontsize=12, fontweight='bold')
        ax1.plot(dates, prices, 'o-', color='#2E86AB', markersize=4,
                 linewidth=1.5, alpha=0.7, label='Price')
        for pb in patterns['pattern_breaks']:
            pb_date = datetime.strptime(pb['date'], '%Y-%m-%d')
            if pb_date in dates:
                pb_idx = dates.index(pb_date)
                color  = '#06A77D' if pb['type'] == 'spike' else '#D62828'
                marker = '^'       if pb['type'] == 'spike' else 'v'
                ax1.plot(pb_date, prices[pb_idx], marker, color=color,
                         markersize=10, markeredgecolor='black', markeredgewidth=0.5)
            ax1.axvline(datetime.strptime(pb['date'], '%Y-%m-%d'),
                        color=('#06A77D' if pb['type'] == 'spike' else '#D62828'),
                        alpha=0.15, linewidth=1)
        ax1.set_ylabel('Price (USD)', fontsize=10, fontweight='bold')
        ax1.set_yscale('log')
        ax1.grid(True, alpha=0.3)
        ax1.legend(['Price', 'Spike (>threshold up)', 'Crash (>threshold down)'],
                   loc='upper left')

        # Subplot 2: Causal consistency
        ax2.set_title('6-1-6 Causal Consistency (0=Chaos, 1=Predictable)',
                      fontsize=12, fontweight='bold')
        ax2.bar(dates, consistencies, color='#F77F00', alpha=0.7, width=1.5)
        ax2.axhline(y=0.7, color='#06A77D', linestyle='--', linewidth=1,
                    alpha=0.5, label='High Consistency (0.70)')
        ax2.axhline(y=0.3, color='#D62828', linestyle='--', linewidth=1,
                    alpha=0.5, label='Low Consistency (0.30)')
        ax2.set_ylabel('Causal Consistency', fontsize=10, fontweight='bold')
        ax2.set_ylim(0, 1.0)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right')

        # Subplot 3: Volume
        ax3.set_title('Trading Volume', fontsize=12, fontweight='bold')
        ax3.bar(dates, volumes, color='#6C757D', alpha=0.5, width=1.5)
        ax3.set_ylabel('Volume', fontsize=10, fontweight='bold')
        ax3.set_xlabel('Date', fontsize=10, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        filename = self.charts_dir / f'{ticker}_616_VISION.png'
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        return str(filename)
