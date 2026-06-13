"""
run_pipeline.py — Master Execution Script
Capstone Project - I | Bluestock Mutual Fund Analytics
"""

import sys
import time
import argparse
import logging
import traceback
from pathlib import Path

# ─── Ensure project root is on sys.path ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
import config as C

# ─── Logging setup ───────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(C.DIRS["reports"] / "pipeline_run.log", mode="a"),
    ],
)
log = logging.getLogger("pipeline")


# ─── Pipeline step registry ───────────────────────────────────────────────────
def _step_ingestion():
    """Step 1: Data ingestion, shape checks, and anomaly report."""
    import data_ingestion as di
    datasets = di.inspect_datasets()
    if datasets:
        fund_master = datasets.get('01_fund_master.csv')
        nav_history = datasets.get('02_nav_history.csv')
        di.document_anomalies(datasets)
        di.explore_fund_master(fund_master)
        di.validate_amfi_codes(fund_master, nav_history)

def _step_cleaning():
    """Step 2: Data cleaning + SQLite database creation."""
    import data_cleaning as dc
    import pandas as pd
    import os
    nav_clean  = dc.clean_nav_history()
    txn_clean  = dc.clean_investor_transactions()
    perf_clean = dc.clean_scheme_performance()
    others     = dc.clean_remaining_datasets()

    fund_master = pd.read_csv(os.path.join(dc.RAW_DIR, '01_fund_master.csv'))
    aum_df      = pd.read_csv(os.path.join(dc.RAW_DIR, '03_aum_by_fund_house.csv'))

    dc.load_to_sqlite(nav_clean, txn_clean, perf_clean, aum_df, fund_master)
    dc.write_sql_files()
    dc.run_sample_queries()

def _step_eda():
    """Step 3: Exploratory Data Analysis — 15 charts."""
    import eda_analysis as eda
    import os, pandas as pd
    
    def load_any(clean_name, raw_name):
        path_clean = os.path.join(eda.PROC_DIR, clean_name)
        if os.path.exists(path_clean):
            return pd.read_csv(path_clean)
        return pd.read_csv(os.path.join(eda.RAW_DIR, raw_name))

    nav_df       = load_any('02_nav_history_clean.csv',          '02_nav_history.csv')
    fund_master  = load_any('01_fund_master_clean.csv',          '01_fund_master.csv')
    aum_df       = load_any('03_aum_by_fund_house_clean.csv',    '03_aum_by_fund_house.csv')
    sip_df       = load_any('04_monthly_sip_inflows_clean.csv',  '04_monthly_sip_inflows.csv')
    cat_df       = load_any('05_category_inflows_clean.csv',     '05_category_inflows.csv')
    folio_df     = load_any('06_industry_folio_count_clean.csv', '06_industry_folio_count.csv')
    perf_df      = load_any('07_scheme_performance_clean.csv',   '07_scheme_performance.csv')
    txn_df       = load_any('08_investor_transactions_clean.csv','08_investor_transactions.csv')
    holdings_df  = load_any('09_portfolio_holdings_clean.csv',   '09_portfolio_holdings.csv')

    eda.chart_nav_trend(nav_df, fund_master)
    eda.chart_aum_growth(aum_df)
    eda.chart_sip_timeseries(sip_df)
    eda.chart_category_heatmap(cat_df)
    eda.chart_age_distribution(txn_df)
    eda.chart_sip_boxplot_age(txn_df)
    eda.chart_gender_split(txn_df)
    eda.chart_state_sip(txn_df)
    eda.chart_t30_b30(txn_df)
    eda.chart_folio_growth(folio_df)
    eda.chart_nav_correlation(nav_df, fund_master)
    eda.chart_sector_donut(holdings_df, fund_master)
    eda.chart_expense_ratio(perf_df)
    eda.chart_risk_grade(fund_master)
    eda.chart_morningstar(perf_df)

    eda.document_eda_findings(nav_df, sip_df, folio_df, txn_df, perf_df, fund_master, holdings_df)


def _step_performance():
    """Step 4: Performance analytics — CAGR, Sharpe, Sortino, Alpha/Beta, Scorecard."""
    import performance_analytics as pa
    pa.run_all()


def _step_advanced():
    """Step 5: Advanced analytics — VaR/CVaR, Rolling Sharpe, Cohort, SIP Continuity, HHI."""
    import advanced_analytics as aa
    aa.run_all()


def _step_dashboard():
    """Step 6: Dashboard export — PNG pages + PDF."""
    import dashboard_export as de
    de.run_all()


def _step_recommender():
    """Step 7: Fund recommender demo (Low / Moderate / High risk)."""
    from recommender import recommend_funds
    for appetite in ["Low", "Moderate", "High"]:
        log.info("--- Recommender: %s risk ---", appetite)
        recommend_funds(appetite, verbose=True)


STEPS = {
    1: ("Data Ingestion & Validation",  _step_ingestion),
    2: ("Data Cleaning & SQLite DB",    _step_cleaning),
    3: ("Exploratory Data Analysis",    _step_eda),
    4: ("Performance Analytics",        _step_performance),
    5: ("Advanced Analytics",           _step_advanced),
    6: ("Dashboard Export",             _step_dashboard),
    7: ("Fund Recommender Demo",        _step_recommender),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _banner(msg: str) -> None:
    width = 60
    log.info("=" * width)
    log.info("  %s", msg)
    log.info("=" * width)


def _parse_int_list(raw: str) -> list[int]:
    """Parse '1,3,5' or '3' into [1, 3, 5]."""
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


# ─── Main orchestrator ───────────────────────────────────────────────────────
def run(step_ids: list[int]) -> bool:
    """Execute the requested steps. Returns True if all passed."""
    results: dict[int, str] = {}
    _banner(f"Bluestock MF Analytics Pipeline  |  {len(step_ids)} step(s)")

    for sid in sorted(step_ids):
        if sid not in STEPS:
            log.warning("Unknown step %s — skipping.", sid)
            continue

        label, func = STEPS[sid]
        log.info("[STEP %d/%d] %s", sid, max(step_ids), label)
        t0 = time.perf_counter()
        try:
            func()
            elapsed = time.perf_counter() - t0
            log.info("  ✓  Completed in %.1f s", elapsed)
            results[sid] = "PASS"
        except Exception:
            elapsed = time.perf_counter() - t0
            log.error("  ✗  FAILED after %.1f s", elapsed)
            log.error(traceback.format_exc())
            results[sid] = "FAIL"

    # ── Summary ────────────────────────────────────────────────────────────
    _banner("Pipeline Summary")
    all_pass = True
    for sid in sorted(results):
        status = results[sid]
        icon = "✓" if status == "PASS" else "✗"
        log.info("  %s  Step %d  %s  [%s]", icon, sid, STEPS[sid][0], status)
        if status != "PASS":
            all_pass = False

    if all_pass:
        log.info("\n  All steps completed successfully.")
    else:
        log.warning("\n  One or more steps failed — review log above.")

    return all_pass


# ─── CLI entry-point ──────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bluestock MF Analytics — master pipeline runner"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--steps",
        metavar="N[,N]",
        help="Comma-separated list of step numbers to run (e.g. --steps 1,2,3)",
    )
    group.add_argument(
        "--skip",
        metavar="N[,N]",
        help="Comma-separated list of step numbers to skip",
    )
    group.add_argument(
        "--from",
        dest="from_step",
        type=int,
        metavar="N",
        help="Run all steps starting from step N",
    )
    args = parser.parse_args()

    all_steps = list(STEPS.keys())

    if args.steps:
        step_ids = _parse_int_list(args.steps)
    elif args.skip:
        skip_ids = set(_parse_int_list(args.skip))
        step_ids = [s for s in all_steps if s not in skip_ids]
    elif args.from_step:
        step_ids = [s for s in all_steps if s >= args.from_step]
    else:
        step_ids = all_steps

    # Ensure required output directories exist
    for d in C.DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

    success = run(step_ids)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()