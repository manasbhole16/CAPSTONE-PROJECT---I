"""
config.py — Centralised configuration for Capstone Project - I
All thresholds, paths, and business-logic constants live here.
Never hardcode values elsewhere — import from this module instead.
"""

import os
from pathlib import Path

# ─── Project root (resolved dynamically regardless of working directory) ───
PROJECT_ROOT = Path(__file__).resolve().parent

# ─── Directory paths (all relative to project root) ───────────────────────
DIRS = {
    "raw":       PROJECT_ROOT / "data" / "raw",
    "processed": PROJECT_ROOT / "data" / "processed",
    "reports":   PROJECT_ROOT / "reports",
    "charts":    PROJECT_ROOT / "reports" / "charts",
    "notebooks": PROJECT_ROOT / "notebooks",
    "sql":       PROJECT_ROOT / "sql",
    "dashboard": PROJECT_ROOT / "dashboard",
}

# ─── Dataset filenames ─────────────────────────────────────────────────────
RAW_FILES = {
    "fund_master":         "01_fund_master.csv",
    "nav_history":         "02_nav_history.csv",
    "aum_by_fund_house":   "03_aum_by_fund_house.csv",
    "monthly_sip":         "04_monthly_sip_inflows.csv",
    "category_inflows":    "05_category_inflows.csv",
    "folio_count":         "06_industry_folio_count.csv",
    "scheme_performance":  "07_scheme_performance.csv",
    "investor_txn":        "08_investor_transactions.csv",
    "portfolio_holdings":  "09_portfolio_holdings.csv",
    "benchmark_indices":   "10_benchmark_indices.csv",
}

CLEAN_FILES = {k: v.replace(".csv", "_clean.csv") for k, v in RAW_FILES.items()}

# ─── Database ──────────────────────────────────────────────────────────────
DB_PATH = PROJECT_ROOT / "bluestock_mf.db"

# ─── Performance analytics constants ──────────────────────────────────────
TRADING_DAYS   = 252          # annualisation factor
RISK_FREE_RATE = 0.065        # RBI repo rate proxy (annual)

# ─── Day 6: Risk & Advanced Analytics ─────────────────────────────────────
VAR_CONFIDENCE      = 0.95    # Historical VaR confidence level (95%)
VAR_PERCENTILE      = 1 - VAR_CONFIDENCE   # 5th percentile of daily returns

ROLLING_WINDOW      = 90      # Rolling Sharpe window in trading days
ROLLING_SHARPE_FUNDS = 5      # Number of top funds to plot for rolling Sharpe

SIP_MIN_TRANSACTIONS = 6      # Min SIP txns to include in continuity analysis
SIP_GAP_THRESHOLD    = 35     # Days gap flagging investor as "at-risk"

RECOMMENDER_TOP_N    = 3      # Number of funds returned by recommender

HHI_HIGH_THRESHOLD   = 2500  # HHI > this → highly concentrated (out of 10000)
HHI_MODERATE         = 1500  # HHI between this and HIGH → moderately concentrated

# ─── Risk appetite → risk_category mapping for recommender ────────────────
RISK_APPETITE_MAP = {
    "Low":      ["Low", "Moderate"],
    "Moderate": ["Moderate", "Moderately High"],
    "High":     ["High", "Very High", "Moderately High"],
}

# ─── Bluestock visual theme ────────────────────────────────────────────────
THEME = {
    "navy":    "#0B1D3A",
    "blue":    "#1565C0",
    "teal":    "#00ACC1",
    "gold":    "#F9A825",
    "pos":     "#00897B",
    "neg":     "#D32F2F",
    "muted":   "#6B7A99",
    "surface": "#F4F6FB",
    "palette": [
        "#1565C0", "#00ACC1", "#F9A825", "#00897B",
        "#7B1FA2", "#E64A19", "#37474F", "#AD1457",
        "#558B2F", "#0277BD",
    ],
}

# ─── Helper: resolve dataset path (cleaned preferred, raw fallback) ────────
def data_path(key: str, prefer_clean: bool = True) -> Path:
    """Return Path to dataset. Prefers cleaned version if it exists."""
    if prefer_clean:
        clean = DIRS["processed"] / CLEAN_FILES[key]
        if clean.exists():
            return clean
    return DIRS["raw"] / RAW_FILES[key]


def report_path(filename: str) -> Path:
    """Return Path inside reports/."""
    return DIRS["reports"] / filename


def chart_path(filename: str) -> Path:
    """Return Path inside reports/charts/."""
    return DIRS["charts"] / filename


def notebook_path(filename: str) -> Path:
    """Return Path inside notebooks/."""
    return DIRS["notebooks"] / filename
