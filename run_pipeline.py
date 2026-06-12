"""
run_pipeline.py — Master Execution Script
Capstone Project - I | Bluestock Mutual Fund Analytics

Orchestrates the full end-to-end pipeline:
  Step 1: Data Ingestion & Validation  (data_ingestion.py)
  Step 2: Data Cleaning & SQLite DB    (data_cleaning.py)
  Step 3: Exploratory Data Analysis    (eda_analysis.py)
  Step 4: Performance Analytics        (performance_analytics.py)
  Step 5: Advanced Analytics           (advanced_analytics.py)
  Step 6: Dashboard Export             (dashboard_export.py)
  Step 7: Fund Recommender Demo        (recommender.py)

Usage:
    python run_pipeline.py              # run all steps
    python run_pipeline.py --steps 1,2  # run specific steps
    python run_pipeline.py --skip 6     # skip specific steps
    python run_pipeline.py --from 3     # start from step N

All paths and constants are resolved via config.py — nothing is hardcoded.
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
    di.inspect_datasets()
    di.validate_amfi_codes()
    di.explore_fund_master()
    di.generate_quality_report()


def _step_cleaning():
    """Step 2: Data cleaning + SQLite database creation."""
    import data_cleaning as dc
    dc.clean_nav_history()
    dc.clean_investor_transactions()
    dc.clean_scheme_performance()
    dc.clean_remaining_datasets()
    dc.create_database()
    dc.write_sql_artifacts()
    dc.generate_data_dictionary()


def _step_eda():
    """Step 3: Exploratory Data Analysis — 15 charts."""
    import eda_analysis as eda
    eda.run_all()


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
