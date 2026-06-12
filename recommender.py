"""
recommender.py — Simple Fund Recommender
Capstone Project - I | Bluestock Mutual Fund Analytics | Day 6

Usage (CLI):
    python recommender.py --risk Low
    python recommender.py --risk Moderate
    python recommender.py --risk High
    python recommender.py  # interactive prompt

Usage (as module):
    from recommender import recommend_funds
    result = recommend_funds("Moderate")
    print(result)

Logic:
    Input : risk appetite string (Low / Moderate / High)
    Filter: funds whose risk_category matches RISK_APPETITE_MAP[appetite]
    Rank  : by Sharpe ratio (from fund_scorecard.csv)
    Output: top RECOMMENDER_TOP_N funds — printed table + returned DataFrame

All configuration (top-N, risk mappings, paths) comes from config.py.
Nothing is hardcoded in this module.
"""

import sys
import argparse
import pandas as pd
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


# ════════════════════════════════════════════════════════════════════════════════
# CORE RECOMMENDATION LOGIC
# ════════════════════════════════════════════════════════════════════════════════

def recommend_funds(risk_appetite: str,
                    top_n: int = None,
                    verbose: bool = True) -> pd.DataFrame:
    """
    Recommend top mutual funds based on investor risk appetite.

    Parameters
    ----------
    risk_appetite : str
        One of 'Low', 'Moderate', or 'High' (case-insensitive).
    top_n : int, optional
        Override the default RECOMMENDER_TOP_N from config.
    verbose : bool
        If True, print a formatted recommendation table.

    Returns
    -------
    pd.DataFrame
        Filtered + ranked fund recommendations with key metrics.

    Raises
    ------
    ValueError
        If risk_appetite is not one of the valid options.
    FileNotFoundError
        If required data files are missing.
    """
    # ── Validate input ────────────────────────────────────────────────────
    appetite_normalised = risk_appetite.strip().title()
    valid_options = list(C.RISK_APPETITE_MAP.keys())

    if appetite_normalised not in valid_options:
        raise ValueError(
            f"Invalid risk appetite: '{risk_appetite}'. "
            f"Choose from: {valid_options}"
        )

    n = top_n if top_n is not None else C.RECOMMENDER_TOP_N
    target_risk_grades = C.RISK_APPETITE_MAP[appetite_normalised]

    # ── Load data ─────────────────────────────────────────────────────────
    scorecard_path = C.report_path("fund_scorecard.csv")
    fund_path      = C.data_path("fund_master")

    if not scorecard_path.exists():
        raise FileNotFoundError(
            f"fund_scorecard.csv not found at {scorecard_path}. "
            "Run performance_analytics.py first."
        )
    if not fund_path.exists():
        raise FileNotFoundError(f"Fund master not found at {fund_path}.")

    scorecard   = pd.read_csv(scorecard_path)
    fund_master = pd.read_csv(fund_path)

    # ── Merge risk_category from fund_master into scorecard ───────────────
    merged = scorecard.merge(
        fund_master[["amfi_code", "risk_category", "sub_category",
                     "fund_manager", "launch_date", "min_sip_amount"]],
        on="amfi_code", how="left"
    )

    # ── Filter by matching risk categories ────────────────────────────────
    filtered = merged[merged["risk_category"].isin(target_risk_grades)].copy()

    if filtered.empty:
        if verbose:
            print(f"\n⚠️  No funds found matching risk appetite '{appetite_normalised}'. "
                  f"(Looked for: {target_risk_grades})")
        return pd.DataFrame()

    # ── Rank by Sharpe ratio (best risk-adjusted return) ──────────────────
    ranked = (filtered
              .dropna(subset=["sharpe_ratio_calc"])
              .sort_values("sharpe_ratio_calc", ascending=False)
              .head(n)
              .reset_index(drop=True))

    ranked.index = ranked.index + 1   # 1-based rank

    # ── Select display columns ────────────────────────────────────────────
    display_cols = [
        "scheme_name", "fund_house", "category", "risk_category",
        "sharpe_ratio_calc", "cagr_3yr_pct", "alpha_calc",
        "max_drawdown_pct_calc", "expense_ratio_pct",
        "scorecard_100", "min_sip_amount",
    ]
    # Keep only columns that exist
    display_cols = [c for c in display_cols if c in ranked.columns]
    result = ranked[display_cols].copy()

    # ── Print recommendation table ─────────────────────────────────────────
    if verbose:
        _print_recommendation(result, appetite_normalised, target_risk_grades, n)

    return result


def _print_recommendation(df: pd.DataFrame,
                           appetite: str,
                           matched_grades: list,
                           n: int):
    """Print a formatted, readable recommendation table to stdout."""
    sep = "─" * 70

    print(f"\n{'='*70}")
    print(f"  🎯  BLUESTOCK FUND RECOMMENDER")
    print(f"{'='*70}")
    print(f"  Risk Appetite : {appetite}")
    print(f"  Risk Grades   : {', '.join(matched_grades)}")
    print(f"  Ranking by    : Sharpe Ratio (best risk-adjusted return)")
    print(f"  Showing top   : {n} fund(s)")
    print(f"{'='*70}\n")

    for rank, row in df.iterrows():
        print(f"  Rank #{rank}  ─────────────────────────────────────────────────")
        print(f"  Fund        : {row['scheme_name']}")
        print(f"  Fund House  : {row.get('fund_house', '—')}")
        print(f"  Category    : {row.get('category', '—')}  "
              f"| Risk Grade: {row.get('risk_category', '—')}")
        print(f"  Sharpe Ratio: {row.get('sharpe_ratio_calc', float('nan')):.3f}  "
              f"| 3yr CAGR : {row.get('cagr_3yr_pct', float('nan')):.2f}%  "
              f"| Alpha    : {row.get('alpha_calc', float('nan')):.2f}%")
        print(f"  Max Drawdown: {row.get('max_drawdown_pct_calc', float('nan')):.2f}%  "
              f"| Expense  : {row.get('expense_ratio_pct', float('nan')):.2f}%  "
              f"| Score    : {row.get('scorecard_100', float('nan')):.1f}/100")
        if "min_sip_amount" in row and pd.notna(row["min_sip_amount"]):
            print(f"  Min SIP     : ₹{int(row['min_sip_amount']):,}/month")
        print()

    print(f"{'='*70}")
    print(f"  ⚠️  This is for educational purposes only.")
    print(f"     Mutual fund investments are subject to market risks.")
    print(f"{'='*70}\n")


# ════════════════════════════════════════════════════════════════════════════════
# BATCH — all 3 risk levels (useful for testing / notebook)
# ════════════════════════════════════════════════════════════════════════════════

def recommend_all(verbose: bool = True) -> dict:
    """
    Run recommendations for all three risk appetite levels.

    Returns
    -------
    dict mapping 'Low' / 'Moderate' / 'High' → recommendation DataFrame
    """
    results = {}
    for appetite in C.RISK_APPETITE_MAP.keys():
        if verbose:
            print(f"\n{'─'*68}")
        results[appetite] = recommend_funds(appetite, verbose=verbose)
    return results


# ════════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="recommender",
        description="Bluestock MF Fund Recommender — "
                    "top funds matched to your risk appetite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python recommender.py --risk Low\n"
            "  python recommender.py --risk Moderate --top 5\n"
            "  python recommender.py --risk High\n"
            "  python recommender.py --all\n"
        ),
    )
    parser.add_argument(
        "--risk", "-r",
        choices=list(C.RISK_APPETITE_MAP.keys()),
        metavar="APPETITE",
        help=f"Risk appetite: {list(C.RISK_APPETITE_MAP.keys())}",
    )
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=C.RECOMMENDER_TOP_N,
        metavar="N",
        help=f"Number of funds to recommend (default: {C.RECOMMENDER_TOP_N})",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run recommendations for all risk appetite levels",
    )
    return parser


def main():
    parser  = _build_parser()
    args    = parser.parse_args()

    if args.all:
        recommend_all(verbose=True)
        return

    if args.risk:
        recommend_funds(args.risk, top_n=args.top, verbose=True)
        return

    # Interactive mode if no flags
    print("\n🎯  Bluestock Fund Recommender — Interactive Mode")
    print(f"   Valid risk appetites: {list(C.RISK_APPETITE_MAP.keys())}")
    try:
        appetite = input("   Enter your risk appetite: ").strip()
        recommend_funds(appetite, verbose=True)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")


if __name__ == "__main__":
    main()
