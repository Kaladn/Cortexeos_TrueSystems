"""
Market Oracle API — Bridge endpoint for Clearbox AI Studio.
Mount point: /api/market_oracle/

Routes (see CONTRACT.md for full schema):
  POST /api/market_oracle/analyze  — single or multi-ticker analysis
  POST /api/market_oracle/history  — past runs for a ticker
  POST /api/market_oracle/regimes  — regime breakdown by analysis_id
  GET  /api/market_oracle/config   — default config + regime band definitions
  GET  /api/market_oracle/help     — machine-readable API schema (AI + dev use)
"""

import logging
from pathlib import Path
from .market_oracle import MarketOraclePlugin

logger = logging.getLogger("market_oracle.api")

_plugin = None


def get_plugin() -> MarketOraclePlugin:
    global _plugin
    if _plugin is None:
        _plugin = MarketOraclePlugin()
    return _plugin


def handle_analyze(request_data: dict) -> dict:
    """
    POST /api/market_oracle/analyze

    Body: { "tickers": ["MSFT"], "config": { "period": "2y", ... } }
    Single ticker  → full analysis result dict
    Multiple tickers → { "comparison": [...], "results": {...} }
    """
    plugin = get_plugin()
    tickers = request_data.get("tickers", [])
    config  = dict(request_data.get("config", {}))  # copy — we pop from it
    period  = config.pop("period", None)

    if not tickers:
        return {"error": "No tickers provided"}

    if len(tickers) == 1:
        return plugin.analyze(tickers[0], period=period, **config)
    else:
        return plugin.compare(tickers, period=period, **config)


def handle_history(request_data: dict) -> dict:
    """POST /api/market_oracle/history — { "ticker": str, "limit": int }"""
    plugin = get_plugin()
    ticker = request_data.get("ticker", "")
    limit  = request_data.get("limit", 20)
    return {"history": plugin.history(ticker, limit)}


def handle_regimes(request_data: dict) -> dict:
    """POST /api/market_oracle/regimes — { "analysis_id": int }"""
    plugin = get_plugin()
    analysis_id = request_data.get("analysis_id")
    if not analysis_id:
        return {"error": "analysis_id required"}
    return {
        "regimes": plugin.get_regimes(analysis_id),
        "changes": plugin.get_regime_changes(analysis_id),
    }


def handle_config(request_data: dict) -> dict:
    """GET /api/market_oracle/config — current config + regime band schema"""
    return get_plugin().get_ui_config()


def handle_help(request_data: dict) -> dict:
    """GET /api/market_oracle/help — machine-readable API schema"""
    return get_plugin().get_help()


ROUTES = {
    "POST /api/market_oracle/analyze": handle_analyze,
    "POST /api/market_oracle/history": handle_history,
    "POST /api/market_oracle/regimes": handle_regimes,
    "GET /api/market_oracle/config":   handle_config,
    "GET /api/market_oracle/help":     handle_help,
}
