"""
Market Oracle SQLite Storage
Replaces Neo4j dependency. Stores analysis results, regime history, and comparisons.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


class OracleStore:
    """SQLite storage for Market Oracle analysis results."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    period TEXT NOT NULL,
                    run_date TEXT NOT NULL,
                    total_days INTEGER,
                    avg_consistency REAL,
                    avg_volatility REAL,
                    pattern_break_rate REAL,
                    anomaly_rate REAL,
                    verdict TEXT,
                    risk TEXT,
                    grade TEXT,
                    current_regime TEXT,
                    total_regime_changes INTEGER,
                    regime_stability REAL,
                    dominant_regime TEXT,
                    regime_distribution TEXT,
                    duration_seconds REAL
                );

                CREATE TABLE IF NOT EXISTS regimes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    regime_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    duration_days INTEGER,
                    avg_consistency REAL,
                    avg_volatility REAL,
                    pattern_breaks INTEGER,
                    anomalies INTEGER,
                    risk TEXT,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
                );

                CREATE TABLE IF NOT EXISTS regime_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    change_date TEXT NOT NULL,
                    from_regime TEXT NOT NULL,
                    to_regime TEXT NOT NULL,
                    consistency_before REAL,
                    consistency_after REAL,
                    delta REAL,
                    severity TEXT,
                    price_at_change REAL,
                    volume_at_change INTEGER,
                    nearest_pattern_break TEXT,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
                );

                CREATE TABLE IF NOT EXISTS trading_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    close REAL,
                    volume INTEGER,
                    price_change REAL,
                    causal_consistency REAL,
                    backward_score REAL,
                    forward_score REAL,
                    is_pattern_break INTEGER DEFAULT 0,
                    break_type TEXT,
                    is_anomaly INTEGER DEFAULT 0,
                    regime TEXT,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
                );

                CREATE INDEX IF NOT EXISTS idx_analyses_ticker ON analyses(ticker);
                CREATE INDEX IF NOT EXISTS idx_trading_days_analysis ON trading_days(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_regimes_analysis ON regimes(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_regime_changes_analysis ON regime_changes(analysis_id);
            """)

    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def save_analysis(self, ticker, period, metrics, regime_analysis, duration):
        """Save a complete analysis run."""
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO analyses (
                    ticker, period, run_date, total_days,
                    avg_consistency, avg_volatility, pattern_break_rate, anomaly_rate,
                    verdict, risk, grade,
                    current_regime, total_regime_changes, regime_stability,
                    dominant_regime, regime_distribution, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, period, datetime.now().isoformat(), regime_analysis.total_days,
                metrics["avg_consistency"], metrics["avg_volatility"],
                metrics["pattern_break_rate"], metrics["anomaly_rate"],
                metrics["verdict"], metrics["risk"], metrics["grade"],
                regime_analysis.current_regime, regime_analysis.total_regime_changes,
                regime_analysis.regime_stability, regime_analysis.dominant_regime,
                json.dumps(regime_analysis.regime_distribution), duration,
            ))
            analysis_id = cursor.lastrowid

            # Save regimes
            for r in regime_analysis.regimes:
                conn.execute("""
                    INSERT INTO regimes (
                        analysis_id, regime_type, start_date, end_date,
                        duration_days, avg_consistency, avg_volatility,
                        pattern_breaks, anomalies, risk
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id, r.regime_type, r.start_date, r.end_date,
                    r.duration_days, r.avg_consistency, r.avg_volatility,
                    r.pattern_breaks_in_regime, r.anomalies_in_regime, r.risk,
                ))

            # Save regime changes
            for rc in regime_analysis.regime_changes:
                conn.execute("""
                    INSERT INTO regime_changes (
                        analysis_id, change_date, from_regime, to_regime,
                        consistency_before, consistency_after, delta, severity,
                        price_at_change, volume_at_change, nearest_pattern_break
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id, rc.date, rc.from_regime, rc.to_regime,
                    rc.consistency_before, rc.consistency_after, rc.delta,
                    rc.severity, rc.price_at_change, rc.volume_at_change,
                    rc.nearest_pattern_break,
                ))

            return analysis_id

    def save_trading_days(self, analysis_id, capsules, causal_results, patterns,
                          regime_labels):
        """Save per-day data for an analysis run."""
        pb_dates = {pb["date"]: pb for pb in patterns.get("pattern_breaks", [])}
        anomaly_dates = {a["date"] for a in patterns.get("anomalies", [])}

        with self._conn() as conn:
            for i, capsule in enumerate(capsules):
                cr = causal_results[capsule["index"]]
                date = capsule["date"]
                pb = pb_dates.get(date)
                regime = regime_labels[i] if i < len(regime_labels) else ""

                conn.execute("""
                    INSERT INTO trading_days (
                        analysis_id, date, close, volume, price_change,
                        causal_consistency, backward_score, forward_score,
                        is_pattern_break, break_type, is_anomaly, regime
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id, date,
                    capsule["anchor"]["close"], capsule["anchor"]["volume"],
                    capsule["price_change"],
                    cr["consistency"], cr["backward_score"], cr["forward_score"],
                    1 if pb else 0, pb["type"] if pb else None,
                    1 if date in anomaly_dates else 0, regime,
                ))

    def get_analysis_history(self, ticker: str, limit: int = 20) -> list:
        """Get recent analysis runs for a ticker."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM analyses WHERE ticker = ?
                ORDER BY run_date DESC LIMIT ?
            """, (ticker, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_regimes(self, analysis_id: int) -> list:
        """Get regimes for an analysis run."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM regimes WHERE analysis_id = ?
                ORDER BY start_date
            """, (analysis_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_regime_changes(self, analysis_id: int) -> list:
        """Get regime changes for an analysis run."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM regime_changes WHERE analysis_id = ?
                ORDER BY change_date
            """, (analysis_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_tickers(self) -> list:
        """Get all tickers that have been analyzed."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DISTINCT ticker FROM analyses ORDER BY ticker
            """).fetchall()
            return [r["ticker"] for r in rows]

    def compare_tickers(self, tickers: list) -> list:
        """Get latest analysis for each ticker for comparison."""
        results = []
        with self._conn() as conn:
            for t in tickers:
                row = conn.execute("""
                    SELECT * FROM analyses WHERE ticker = ?
                    ORDER BY run_date DESC LIMIT 1
                """, (t,)).fetchone()
                if row:
                    results.append(dict(row))
        return results
