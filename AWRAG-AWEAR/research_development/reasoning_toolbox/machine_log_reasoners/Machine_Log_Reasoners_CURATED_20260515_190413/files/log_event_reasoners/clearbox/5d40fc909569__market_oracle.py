"""
Market Oracle — Clearbox AI Studio Plugin
6-1-6 Financial Cognitive Substrate + Regime Change Analysis

Pipeline (in order, all config overridable per-run):
  MarketFetcher      → list[market_day_dict]
  DataValidator      → bool
  CapsuleBuilder     → list[capsule_dict]  (NCV-73 populated by CausalAnalyzer)
  CausalAnalyzer     → dict[index → {consistency, ncv_73, backward_score, forward_score}]
  PatternDetector    → {pattern_breaks, causal_chains, anomalies}
  MetricsCalculator  → {avg_consistency, avg_volatility, ..., verdict, risk, grade}
  RegimeDetector     → RegimeAnalysis
  ReportGenerator    → str (absolute path to .md)
  VisionChart        → str (absolute path to .png)
  OracleStore        → int (analysis_id)

See CONTRACT.md for full boundary contract, config schema, and invariants.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from .core.regime_detector import RegimeDetector, classify_regime, REGIME_BANDS, REGIME_RISK
from .core.storage import OracleStore

logger = logging.getLogger("market_oracle")

# Absolute base path for all file output — anchored to user home, not CWD
_OUTPUT_BASE = Path.home() / ".clearbox" / "market_oracle"

DEFAULT_CONFIG = {
    "analysis": {
        "default_period": "2y",
        "pattern_break_threshold": 5.0,
        "causal_consistency_high": 0.7,
        "causal_consistency_low": 0.3,
        "min_chain_length": 5,
        "capsule_prev_positions": 6,
        "capsule_next_positions": 6,
    },
    "regime": {
        "regime_rolling_window": 10,
        "min_regime_days": 5,
        "regime_change_lookback": 5,
    },
    "output": {
        "reports_dir": str(_OUTPUT_BASE / "reports"),
        "charts_dir":  str(_OUTPUT_BASE / "charts"),
        "chart_dpi": 300,
        "chart_width": 16,
        "chart_height": 12,
    },
}


class MarketOraclePlugin:
    """
    Clearbox plugin for financial regime change analysis.
    Also works standalone (no Clearbox required).

    Usage:
        plugin = MarketOraclePlugin()
        result = plugin.analyze("MSFT", period="2y")
        result = plugin.analyze("XRP-USD", period="5y",
                                pattern_break_threshold=3.0,
                                regime_rolling_window=15)
        comparison = plugin.compare(["MSFT", "AAPL", "GOOG"])
    """

    def __init__(self, db_path: str = None, config: dict = None):
        self.config = {
            "analysis": {**DEFAULT_CONFIG["analysis"]},
            "regime":   {**DEFAULT_CONFIG["regime"]},
            "output":   {**DEFAULT_CONFIG["output"]},
        }
        if config:
            for section, values in config.items():
                if section in self.config and isinstance(values, dict):
                    self.config[section].update(values)
                else:
                    self.config[section] = values

        if db_path is None:
            db_path = str(_OUTPUT_BASE / "market_oracle.db")
        self.store = OracleStore(db_path)

        self._fetcher = None
        self._validator = None
        self._capsule_builder = None
        self._causal_analyzer = None
        self._pattern_detector = None
        self._metrics_calc = None
        self._report_gen = None
        self._vision_chart = None
        self._regime_detector = None

    def _ensure_modules(self):
        """Lazy-load analysis modules on first use."""
        if self._fetcher is not None:
            return
        from .core.market_fetcher import MarketFetcher
        from .core.data_validator import DataValidator
        from .core.capsule_builder import CapsuleBuilder
        from .core.causal_analyzer import CausalAnalyzer
        from .core.pattern_detector import PatternDetector
        from .core.metrics_calculator import MetricsCalculator
        from .core.report_generator import ReportGenerator
        from .core.vision_chart import VisionChart

        self._fetcher        = MarketFetcher(self.config)
        self._validator      = DataValidator(self.config)
        self._capsule_builder = CapsuleBuilder(self.config)
        self._causal_analyzer = CausalAnalyzer(self.config)
        self._pattern_detector = PatternDetector(self.config)
        self._metrics_calc   = MetricsCalculator(self.config)
        self._report_gen     = ReportGenerator(self.config)
        self._vision_chart   = VisionChart(self.config)
        self._regime_detector = RegimeDetector(self.config.get("regime", {}))

    def analyze(self, ticker: str, period: str = None, **overrides) -> dict:
        """
        Run full 6-1-6 cognitive + regime analysis for one ticker.

        Args:
            ticker:  Symbol e.g. "MSFT", "XRP-USD"
            period:  "1mo" | "3mo" | "6mo" | "1y" | "2y" | "5y" | "10y" | "max"
            **overrides: Any key from DEFAULT_CONFIG["analysis"] or ["regime"],
                         applied only to this run.
                         e.g. pattern_break_threshold=3.0, regime_rolling_window=15

        Returns:
            dict with keys: ticker, period, analysis_id, metrics, regime,
                            report_path, chart_path, duration
            OR: {"error": str} on fetch/validation failure
        """
        self._ensure_modules()

        # Deep copy config, apply per-run overrides
        run_config = json.loads(json.dumps(self.config))
        for key, val in overrides.items():
            for section in run_config:
                if isinstance(run_config[section], dict) and key in run_config[section]:
                    run_config[section][key] = val

        # Rebuild config-sensitive modules if overrides present
        if overrides:
            from .core.capsule_builder import CapsuleBuilder
            from .core.pattern_detector import PatternDetector
            capsule_builder  = CapsuleBuilder(run_config)
            pattern_detector = PatternDetector(run_config)
            regime_detector  = RegimeDetector(run_config.get("regime", {}))
        else:
            capsule_builder  = self._capsule_builder
            pattern_detector = self._pattern_detector
            regime_detector  = self._regime_detector

        if period is None:
            period = run_config["analysis"]["default_period"]

        start_time = datetime.now()
        logger.info(f"Market Oracle: analyzing {ticker} ({period})")

        market_data = self._fetcher.fetch(ticker, period)
        if not market_data:
            return {"error": f"No data available for {ticker}"}

        if not self._validator.validate(market_data):
            return {"error": f"Data validation failed for {ticker}"}

        capsules       = capsule_builder.build(market_data)
        causal_results = self._causal_analyzer.analyze(capsules)
        patterns       = pattern_detector.detect(capsules, causal_results)
        metrics        = self._metrics_calc.calculate(capsules, causal_results, patterns)
        regime_analysis = regime_detector.detect(capsules, causal_results, patterns, ticker)

        # Regime labels for per-day storage
        raw_consistency = [causal_results[c["index"]]["consistency"] for c in capsules]
        rolling_avg     = regime_detector._rolling_mean(raw_consistency, regime_detector.rolling_window)
        regime_labels   = [classify_regime(v) for v in rolling_avg]

        report_path = self._report_gen.generate(
            ticker, market_data, capsules, causal_results, patterns, metrics)
        chart_path = self._vision_chart.create(
            ticker, market_data, capsules, causal_results, patterns)

        duration = (datetime.now() - start_time).total_seconds()

        analysis_id = self.store.save_analysis(ticker, period, metrics, regime_analysis, duration)
        self.store.save_trading_days(analysis_id, capsules, causal_results, patterns, regime_labels)

        logger.info(
            f"Market Oracle: {ticker} complete in {duration:.2f}s — "
            f"{regime_analysis.total_regime_changes} regime changes, "
            f"current: {regime_analysis.current_regime}"
        )

        return {
            "ticker": ticker,
            "period": period,
            "analysis_id": analysis_id,
            "metrics": metrics,
            "regime": {
                "current":       regime_analysis.current_regime,
                "total_changes": regime_analysis.total_regime_changes,
                "stability":     regime_analysis.regime_stability,
                "dominant":      regime_analysis.dominant_regime,
                "distribution":  regime_analysis.regime_distribution,
                "avg_duration":  regime_analysis.avg_regime_duration,
                "regimes":       [r.to_dict() for r in regime_analysis.regimes],
                "changes":       [rc.to_dict() for rc in regime_analysis.regime_changes],
            },
            "report_path": report_path,
            "chart_path":  chart_path,
            "duration":    duration,
        }

    def compare(self, tickers: list, period: str = None, **overrides) -> dict:
        """
        Analyze multiple tickers and return side-by-side comparison.

        Returns:
            {"comparison": [summary_per_ticker sorted by consistency desc],
             "results":    {ticker: full_analyze_result}}
        """
        results = {}
        for t in tickers:
            results[t] = self.analyze(t, period=period, **overrides)

        comparison = []
        for t, r in results.items():
            if "error" in r:
                comparison.append({"ticker": t, "error": r["error"]})
                continue
            comparison.append({
                "ticker":           t,
                "consistency":      r["metrics"]["avg_consistency"],
                "pattern_break_rate": r["metrics"]["pattern_break_rate"],
                "anomaly_rate":     r["metrics"]["anomaly_rate"],
                "verdict":          r["metrics"]["verdict"],
                "grade":            r["metrics"]["grade"],
                "current_regime":   r["regime"]["current"],
                "regime_changes":   r["regime"]["total_changes"],
                "stability":        r["regime"]["stability"],
                "dominant_regime":  r["regime"]["dominant"],
            })

        comparison.sort(key=lambda x: x.get("consistency", 0), reverse=True)
        return {"comparison": comparison, "results": results}

    def history(self, ticker: str, limit: int = 20) -> list:
        """Return recent analysis runs for a ticker from SQLite."""
        return self.store.get_analysis_history(ticker, limit)

    def get_regimes(self, analysis_id: int) -> list:
        """Return regime breakdown for a specific analysis_id."""
        return self.store.get_regimes(analysis_id)

    def get_regime_changes(self, analysis_id: int) -> list:
        """Return regime change events for a specific analysis_id."""
        return self.store.get_regime_changes(analysis_id)

    def get_ui_config(self) -> dict:
        """
        Return config and schema for UI population.
        Used by GET /api/market_oracle/config
        """
        return {
            "analysis":         self.config["analysis"],
            "regime":           self.config["regime"],
            "available_periods": ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
            "regime_bands": {
                k: {
                    "range": list(v),     # [lo, hi] as list (JSON-safe)
                    "risk":  REGIME_RISK[k],  # "LOW" / "MEDIUM" / "HIGH" / "EXTREME"
                }
                for k, v in REGIME_BANDS.items()
            },
        }

    def get_help(self) -> dict:
        """
        Machine-readable API schema for AI and developer use.
        Used by GET /api/market_oracle/help
        """
        return {
            "plugin": "Market Oracle",
            "version": "1.0.0",
            "description": (
                "6-1-6 financial cognitive substrate. Bidirectional causal validation. "
                "Regime change detection from rolling consistency bands. "
                "No ML models. NCV-73 count-based analysis."
            ),
            "endpoints": {
                "POST /api/market_oracle/analyze": {
                    "description": "Run 6-1-6 analysis for one or more tickers",
                    "body": {
                        "tickers": "list[str] — e.g. ['MSFT'] or ['MSFT','AAPL']",
                        "config": {
                            "period": "str — '1mo'|'3mo'|'6mo'|'1y'|'2y'|'5y'|'10y'|'max'",
                            "pattern_break_threshold": "float — % change = break (default 5.0)",
                            "capsule_prev_positions":  "int — N in N-1-N, prev (default 6)",
                            "capsule_next_positions":  "int — N in N-1-N, next (default 6)",
                            "regime_rolling_window":   "int — days for rolling avg (default 10)",
                            "min_regime_days":         "int — min days per regime (default 5)",
                            "causal_consistency_high": "float — chain threshold (default 0.7)",
                            "causal_consistency_low":  "float — anomaly threshold (default 0.3)",
                            "min_chain_length":        "int — min days for chain (default 5)",
                        }
                    },
                    "returns": {
                        "single_ticker": (
                            "ticker, period, analysis_id, metrics{avg_consistency, "
                            "avg_volatility, pattern_break_rate, anomaly_rate, "
                            "num_pattern_breaks, num_causal_chains, num_anomalies, "
                            "verdict, risk, grade}, "
                            "regime{current, total_changes, stability, dominant, "
                            "distribution, avg_duration, regimes[], changes[]}, "
                            "report_path, chart_path, duration"
                        ),
                        "multi_ticker": (
                            "comparison[{ticker, consistency, pattern_break_rate, "
                            "anomaly_rate, verdict, grade, current_regime, "
                            "regime_changes, stability, dominant_regime}], "
                            "results{ticker: single_ticker_result}"
                        ),
                    },
                },
                "POST /api/market_oracle/history": {
                    "description": "Get past analysis runs for a ticker",
                    "body": {"ticker": "str", "limit": "int (default 20)"},
                    "returns": "history: list of analysis rows from SQLite",
                },
                "POST /api/market_oracle/regimes": {
                    "description": "Get regime breakdown for a stored analysis",
                    "body": {"analysis_id": "int"},
                    "returns": "regimes: list, changes: list",
                },
                "GET /api/market_oracle/config": {
                    "description": "Current default config + regime band definitions",
                    "returns": "analysis config, regime config, available_periods, regime_bands",
                },
                "GET /api/market_oracle/help": {
                    "description": "This document — machine-readable API schema",
                    "returns": "plugin metadata, all endpoints, param types, return shapes",
                },
            },
            "regime_types": {
                k: {"range": list(v), "risk": REGIME_RISK[k]}
                for k, v in REGIME_BANDS.items()
            },
            "data_model": {
                "capsule": (
                    "{index: int, date: str(YYYY-MM-DD), "
                    "anchor: {date,open,high,low,close,volume}, "
                    "prev_positions: list[market_day], "
                    "next_positions: list[market_day], "
                    "price_change: float(%%), volume_change: float(%%), "
                    "ncv_73: np.ndarray[73]}"
                ),
                "regime": (
                    "{regime_type: ORDERED|MODERATE|VOLATILE|CHAOTIC, "
                    "start_date, end_date, start_index, end_index, "
                    "duration_days, avg_consistency, avg_volatility, "
                    "pattern_breaks_in_regime, anomalies_in_regime, risk}"
                ),
                "regime_change": (
                    "{date, index, from_regime, to_regime, "
                    "consistency_before, consistency_after, delta, "
                    "severity: MINOR|MAJOR|CRITICAL, "
                    "price_at_change, volume_at_change, nearest_pattern_break}"
                ),
            },
            "storage": {
                "db_path": str(_OUTPUT_BASE / "market_oracle.db"),
                "tables": ["analyses", "regimes", "regime_changes", "trading_days"],
            },
            "output_paths": {
                "reports": str(_OUTPUT_BASE / "reports"),
                "charts":  str(_OUTPUT_BASE / "charts"),
            },
        }
