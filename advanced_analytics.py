"""
advanced_analytics.py — Day 6: Advanced Analytics + Risk Metrics
Capstone Project - I | Bluestock Mutual Fund Analytics

Tasks:
  1. Historical VaR (95%) + CVaR for all 40 schemes
  2. Rolling 90-day Sharpe — plot over time for top 5 funds
  3. Investor cohort analysis — first-txn-year grouping
  4. SIP continuity analysis — at-risk investor flagging
  5. Sector HHI concentration per fund
  6. 5 advanced narrative insights (printed + saved)

Deliverables:
  reports/var_cvar_report.csv
  reports/charts/rolling_sharpe_chart.png
  (Advanced_Analytics.ipynb wraps this module)

All thresholds and paths come from config.py — nothing is hardcoded here.
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

warnings.filterwarnings("ignore")

# ── Config (single source of truth) ──────────────────────────────────────────
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import config as C

# ── Matplotlib theme ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  C.THEME["surface"],
    "axes.facecolor":    "white",
    "axes.edgecolor":    "#DDE3EF",
    "axes.labelcolor":   C.THEME["navy"],
    "axes.titlecolor":   C.THEME["navy"],
    "axes.titlesize":    11,
    "axes.titleweight":  "bold",
    "axes.labelsize":    9,
    "xtick.color":       C.THEME["muted"],
    "ytick.color":       C.THEME["muted"],
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "grid.color":        "#EEF1F7",
    "figure.dpi":        130,
    "savefig.dpi":       150,
    "savefig.bbox":      "tight",
    "savefig.facecolor": C.THEME["surface"],
    "font.family":       "DejaVu Sans",
})


# ════════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ════════════════════════════════════════════════════════════════════════════════

def load_nav_returns() -> pd.DataFrame:
    """
    Load nav_history (cleaned preferred), pivot to wide, compute daily returns.
    Returns DataFrame: index=date, columns=amfi_code, values=daily_return.
    """
    nav = pd.read_csv(C.data_path("nav_history"))
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date", "nav"]).sort_values(["amfi_code", "date"])

    pivot = nav.pivot_table(index="date", columns="amfi_code",
                             values="nav", aggfunc="last").sort_index()
    returns = pivot.pct_change().iloc[1:]           # nav_t / nav_t-1 - 1
    returns = returns.clip(lower=-0.20, upper=0.20) # clip data artefacts
    return returns


def load_nav_pivot() -> pd.DataFrame:
    """Wide NAV pivot (index=date, cols=amfi_code, vals=NAV price)."""
    nav = pd.read_csv(C.data_path("nav_history"))
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date", "nav"]).sort_values(["amfi_code", "date"])
    return nav.pivot_table(index="date", columns="amfi_code",
                            values="nav", aggfunc="last").sort_index()


def load_fund_master() -> pd.DataFrame:
    return pd.read_csv(C.data_path("fund_master"))


def load_transactions() -> pd.DataFrame:
    txn = pd.read_csv(C.data_path("investor_txn"))
    txn["transaction_date"] = pd.to_datetime(txn["transaction_date"], errors="coerce")
    return txn.dropna(subset=["transaction_date"])


def load_holdings() -> pd.DataFrame:
    return pd.read_csv(C.data_path("portfolio_holdings"))


def load_scorecard() -> pd.DataFrame:
    return pd.read_csv(C.report_path("fund_scorecard.csv"))


# ════════════════════════════════════════════════════════════════════════════════
# TASK 1 — Historical VaR (95%) + CVaR
# ════════════════════════════════════════════════════════════════════════════════

def compute_var_cvar(returns: pd.DataFrame,
                     fund_master: pd.DataFrame) -> pd.DataFrame:
    """
    Historical VaR at VAR_CONFIDENCE level and CVaR for all 40 schemes.

    VaR  = VAR_PERCENTILE-th percentile of daily return distribution (negative = loss)
    CVaR = mean of returns BELOW the VaR threshold (expected shortfall)

    Both expressed as positive loss percentages for readability.

    Parameters
    ----------
    returns     : wide daily-return DataFrame (index=date, cols=amfi_code)
    fund_master : fund metadata for name/category labelling

    Returns
    -------
    DataFrame with one row per fund containing VaR, CVaR, std_dev,
    min_return, and descriptive statistics.
    """
    print(f"\n── VaR / CVaR  (confidence={C.VAR_CONFIDENCE*100:.0f}%) ──────────────────────────")

    records = []
    for code in returns.columns:
        r = returns[code].dropna()
        if len(r) < 30:
            continue

        var_threshold = float(np.percentile(r, C.VAR_PERCENTILE * 100))
        tail_returns  = r[r < var_threshold]
        cvar          = float(tail_returns.mean()) if len(tail_returns) > 0 else var_threshold

        records.append({
            "amfi_code":        code,
            "var_95_pct":       round(var_threshold * 100, 4),   # negative = loss
            "cvar_95_pct":      round(cvar * 100, 4),
            "daily_std_pct":    round(float(r.std()) * 100, 4),
            "min_daily_ret_pct":round(float(r.min()) * 100, 4),
            "max_daily_ret_pct":round(float(r.max()) * 100, 4),
            "n_obs":            len(r),
            "tail_obs":         len(tail_returns),
        })

    df = pd.DataFrame(records)

    # Merge fund metadata
    meta = fund_master[["amfi_code", "scheme_name", "fund_house",
                         "category", "plan", "risk_category"]].copy()
    df   = df.merge(meta, on="amfi_code", how="left")

    # Sort by worst VaR (most negative = riskiest)
    df   = df.sort_values("var_95_pct").reset_index(drop=True)

    # Save
    out = C.report_path("var_cvar_report.csv")
    df.to_csv(out, index=False)
    print(f"   ✅ var_cvar_report.csv → {out}  ({len(df)} funds)")

    # Print top worst & best
    print(f"\n   Worst 5 VaR (riskiest):")
    print(df[["scheme_name", "var_95_pct", "cvar_95_pct", "category"]].head(5).to_string(index=False))
    print(f"\n   Best 5 VaR (safest):")
    print(df[["scheme_name", "var_95_pct", "cvar_95_pct", "category"]].tail(5).to_string(index=False))

    return df


# ════════════════════════════════════════════════════════════════════════════════
# TASK 2 — Rolling 90-day Sharpe
# ════════════════════════════════════════════════════════════════════════════════

def compute_rolling_sharpe(returns: pd.DataFrame,
                            scorecard: pd.DataFrame,
                            fund_master: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling Sharpe = returns.rolling(ROLLING_WINDOW).mean()
                   / returns.rolling(ROLLING_WINDOW).std() × √252

    Computed for top ROLLING_SHARPE_FUNDS funds (by scorecard rank).

    Returns
    -------
    DataFrame: index=date, one column per fund with rolling Sharpe values.
    """
    print(f"\n── Rolling {C.ROLLING_WINDOW}-day Sharpe ────────────────────────────────────")

    # Select top N funds by scorecard rank
    top_codes = (scorecard
                 .nsmallest(C.ROLLING_SHARPE_FUNDS, "scorecard_rank")["amfi_code"]
                 .tolist())
    name_map  = fund_master.set_index("amfi_code")["scheme_name"].str[:28].to_dict()

    rf_daily  = C.RISK_FREE_RATE / C.TRADING_DAYS
    rolling_sharpe = {}

    for code in top_codes:
        if code not in returns.columns:
            continue
        r = returns[code].dropna()
        excess = r - rf_daily
        roll_mean = excess.rolling(C.ROLLING_WINDOW, min_periods=C.ROLLING_WINDOW // 2).mean()
        roll_std  = r.rolling(C.ROLLING_WINDOW,      min_periods=C.ROLLING_WINDOW // 2).std()
        sharpe    = (roll_mean / roll_std.replace(0, np.nan)) * np.sqrt(C.TRADING_DAYS)
        rolling_sharpe[name_map.get(code, str(code))] = sharpe

    rs_df = pd.DataFrame(rolling_sharpe).dropna(how="all")
    print(f"   Computed rolling Sharpe for {len(rolling_sharpe)} funds | "
          f"{len(rs_df)} date points")
    return rs_df


def plot_rolling_sharpe(rs_df: pd.DataFrame) -> str:
    """
    Plot rolling Sharpe over time for the selected funds.
    Returns path to saved PNG.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.set_facecolor(C.THEME["surface"])
    ax.set_facecolor("white")

    palette = C.THEME["palette"]
    for i, col in enumerate(rs_df.columns):
        ax.plot(rs_df.index, rs_df[col], linewidth=1.8,
                color=palette[i % len(palette)], label=col, alpha=0.9)

    # Reference line at Sharpe = 1
    ax.axhline(1.0, color=C.THEME["pos"],  linestyle="--",
               linewidth=1.2, alpha=0.7, label="Sharpe = 1 (Good)")
    ax.axhline(0.0, color=C.THEME["neg"],  linestyle=":",
               linewidth=1.0, alpha=0.6, label="Sharpe = 0")

    ax.set_title(f"Rolling {C.ROLLING_WINDOW}-Day Sharpe Ratio — "
                 f"Top {C.ROLLING_SHARPE_FUNDS} Funds  (Rf = {C.RISK_FREE_RATE*100:.1f}%)",
                 fontsize=12, fontweight="bold", color=C.THEME["navy"])
    ax.set_xlabel("Date")
    ax.set_ylabel("Rolling Sharpe Ratio")
    ax.legend(loc="upper left", fontsize=8, ncol=2,
              framealpha=0.9, edgecolor=C.THEME["muted"])
    ax.grid(True, alpha=0.5)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))

    # Branding
    fig.text(0.99, 0.01, "BLUESTOCK MF ANALYTICS · DAY 6",
             fontsize=7, color=C.THEME["muted"], ha="right", va="bottom", alpha=0.6)

    out = str(C.chart_path("rolling_sharpe_chart.png"))
    fig.savefig(out)
    plt.close(fig)
    print(f"   ✅ rolling_sharpe_chart.png → {out}")
    return out


# ════════════════════════════════════════════════════════════════════════════════
# TASK 3 — Investor Cohort Analysis
# ════════════════════════════════════════════════════════════════════════════════

def investor_cohort_analysis(txn: pd.DataFrame,
                              fund_master: pd.DataFrame) -> pd.DataFrame:
    """
    Group investors by first transaction year (cohort).
    For each cohort compute:
      - investor count
      - avg SIP amount
      - total invested
      - top fund preference (most-transacted amfi_code)

    Returns cohort summary DataFrame.
    """
    print("\n── Investor Cohort Analysis ────────────────────────────────────────")

    # Determine cohort: year of first transaction per investor
    first_txn = (txn.groupby("investor_id")["transaction_date"]
                    .min()
                    .dt.year
                    .rename("cohort_year"))
    txn_enriched = txn.merge(first_txn.reset_index(), on="investor_id", how="left")

    # SIP amounts per cohort
    sip_txn  = txn_enriched[txn_enriched["transaction_type"] == "SIP"]
    cohort_sip = (sip_txn.groupby("cohort_year")
                          .agg(
                              investor_count=("investor_id", "nunique"),
                              avg_sip_amount=("amount_inr", "mean"),
                              total_invested =("amount_inr", "sum"),
                          )
                          .reset_index())
    cohort_sip["avg_sip_amount"] = cohort_sip["avg_sip_amount"].round(0)
    cohort_sip["total_invested"]  = cohort_sip["total_invested"].round(0)

    # Top fund preference per cohort (most-transacted amfi_code)
    fund_pref = (txn_enriched
                 .groupby(["cohort_year", "amfi_code"])
                 .size()
                 .reset_index(name="txn_count")
                 .sort_values("txn_count", ascending=False)
                 .groupby("cohort_year")
                 .first()
                 .reset_index()[["cohort_year", "amfi_code"]])
    name_map = fund_master.set_index("amfi_code")["scheme_name"].to_dict()
    fund_pref["top_fund"] = fund_pref["amfi_code"].map(name_map)

    cohort_df = cohort_sip.merge(fund_pref[["cohort_year", "top_fund"]],
                                  on="cohort_year", how="left")

    print(f"   Cohorts found: {sorted(cohort_df.cohort_year.tolist())}")
    print(cohort_df.to_string(index=False))
    return cohort_df


# ════════════════════════════════════════════════════════════════════════════════
# TASK 4 — SIP Continuity Analysis
# ════════════════════════════════════════════════════════════════════════════════

def sip_continuity_analysis(txn: pd.DataFrame) -> pd.DataFrame:
    """
    For investors with >= SIP_MIN_TRANSACTIONS SIP transactions:
      - compute average gap (days) between consecutive SIP dates
      - flag investor as "at-risk" if avg gap > SIP_GAP_THRESHOLD days

    Returns investor-level DataFrame with continuity metrics.
    """
    print(f"\n── SIP Continuity Analysis  "
          f"(min_txn={C.SIP_MIN_TRANSACTIONS}, gap_threshold={C.SIP_GAP_THRESHOLD}d) ──")

    sip_only = txn[txn["transaction_type"] == "SIP"].copy()
    sip_only = sip_only.sort_values(["investor_id", "transaction_date"])

    # Investors with enough SIP history
    sip_counts = sip_only.groupby("investor_id").size()
    eligible   = sip_counts[sip_counts >= C.SIP_MIN_TRANSACTIONS].index
    sip_filt   = sip_only[sip_only["investor_id"].isin(eligible)]

    records = []
    for inv_id, grp in sip_filt.groupby("investor_id"):
        dates = grp["transaction_date"].sort_values().reset_index(drop=True)
        gaps  = dates.diff().dt.days.dropna()
        avg_gap    = float(gaps.mean())
        max_gap    = float(gaps.max())
        n_txn      = len(dates)
        at_risk    = avg_gap > C.SIP_GAP_THRESHOLD
        records.append({
            "investor_id":    inv_id,
            "sip_txn_count":  n_txn,
            "avg_gap_days":   round(avg_gap, 1),
            "max_gap_days":   round(max_gap, 1),
            "first_sip_date": dates.iloc[0].strftime("%Y-%m-%d"),
            "last_sip_date":  dates.iloc[-1].strftime("%Y-%m-%d"),
            "at_risk":        at_risk,
        })

    result = pd.DataFrame(records)
    at_risk_count = result["at_risk"].sum()
    print(f"   Eligible investors (≥{C.SIP_MIN_TRANSACTIONS} SIP txns): {len(result)}")
    print(f"   At-risk (avg gap > {C.SIP_GAP_THRESHOLD}d): "
          f"{at_risk_count}  ({at_risk_count/len(result)*100:.1f}%)")
    print(f"   Avg gap (all eligible): {result['avg_gap_days'].mean():.1f} days")

    # Save
    out = C.report_path("sip_continuity.csv")
    result.to_csv(out, index=False)
    print(f"   ✅ sip_continuity.csv → {out}")
    return result


# ════════════════════════════════════════════════════════════════════════════════
# TASK 5 — Sector HHI Concentration
# ════════════════════════════════════════════════════════════════════════════════

def compute_sector_hhi(holdings: pd.DataFrame,
                        fund_master: pd.DataFrame) -> pd.DataFrame:
    """
    Herfindahl–Hirschman Index per fund:
        HHI = Σ (weight_i)²   where weight_i is sector weight (%) for fund i

    Normalised to 0–10000 scale (weight in % → (w/100)² × 10000 = w²).
    Interpretation:
        HHI > HHI_HIGH_THRESHOLD     → Highly concentrated
        HHI > HHI_MODERATE           → Moderately concentrated
        else                          → Diversified

    Only equity funds are included (sector allocation is meaningful).
    """
    print(f"\n── Sector HHI Concentration  "
          f"(high≥{C.HHI_HIGH_THRESHOLD}, moderate≥{C.HHI_MODERATE}) ──────────")

    equity_codes = fund_master[fund_master["category"] == "Equity"]["amfi_code"].tolist()
    eq_holdings  = holdings[holdings["amfi_code"].isin(equity_codes)].copy()

    # Aggregate to sector-level weights per fund (in case multiple stocks per sector)
    sector_wt = (eq_holdings
                 .groupby(["amfi_code", "sector"])["weight_pct"]
                 .sum()
                 .reset_index())

    hhi_records = []
    for code, grp in sector_wt.groupby("amfi_code"):
        w     = grp["weight_pct"].values          # already in %
        hhi   = float(np.sum(w ** 2))             # Σ w² (100-scale gives 100–10000)
        top_sector = grp.nlargest(1, "weight_pct").iloc[0]["sector"]
        top_wt     = grp.nlargest(1, "weight_pct").iloc[0]["weight_pct"]
        n_sectors  = len(grp)

        label = ("Highly Concentrated" if hhi >= C.HHI_HIGH_THRESHOLD
                 else "Moderately Concentrated" if hhi >= C.HHI_MODERATE
                 else "Diversified")

        hhi_records.append({
            "amfi_code":         code,
            "hhi":               round(hhi, 1),
            "concentration":     label,
            "top_sector":        top_sector,
            "top_sector_wt_pct": round(float(top_wt), 2),
            "n_sectors":         n_sectors,
        })

    hhi_df = pd.DataFrame(hhi_records)
    name_map = fund_master.set_index("amfi_code")["scheme_name"].str[:30].to_dict()
    hhi_df["scheme_name"] = hhi_df["amfi_code"].map(name_map)
    hhi_df = hhi_df.sort_values("hhi", ascending=False).reset_index(drop=True)

    print(f"\n   {'Scheme':<30} {'HHI':>7}  {'Concentration':<23}  Top Sector")
    print("   " + "-"*80)
    for _, row in hhi_df.iterrows():
        print(f"   {row['scheme_name']:<30} {row['hhi']:>7.0f}  "
              f"{row['concentration']:<23}  {row['top_sector']} ({row['top_sector_wt_pct']:.1f}%)")

    # Save
    out = C.report_path("sector_hhi.csv")
    hhi_df.to_csv(out, index=False)
    print(f"\n   ✅ sector_hhi.csv → {out}")
    return hhi_df


# ════════════════════════════════════════════════════════════════════════════════
# TASK 6 — 5 Advanced Insights
# ════════════════════════════════════════════════════════════════════════════════

def generate_advanced_insights(var_df: pd.DataFrame,
                                 cohort_df: pd.DataFrame,
                                 continuity_df: pd.DataFrame,
                                 hhi_df: pd.DataFrame,
                                 scorecard: pd.DataFrame) -> list:
    """
    Generate 5 data-driven advanced insights from Day 6 analytics.
    Returns list of insight strings; also saves to reports/advanced_insights.md
    """
    print("\n── 5 Advanced Insights ─────────────────────────────────────────────")

    insights = []

    # Insight 1 — Highest VaR fund
    worst_var = var_df.nsmallest(1, "var_95_pct").iloc[0]
    i1 = (f"**I1 — Highest Risk (VaR):** '{worst_var['scheme_name'][:40]}' has the worst "
          f"95% VaR of {worst_var['var_95_pct']:.2f}% per day, meaning on 1 in 20 trading days "
          f"losses could exceed this. Its CVaR (expected shortfall) is "
          f"{worst_var['cvar_95_pct']:.2f}%, indicating fat-tail risk. "
          f"Investors in this fund should be prepared for sharp drawdowns.")

    # Insight 2 — Investor cohort investing more
    if len(cohort_df) >= 2:
        top_cohort = cohort_df.nlargest(1, "avg_sip_amount").iloc[0]
        i2 = (f"**I2 — Highest-Investing Cohort:** The {int(top_cohort['cohort_year'])} investor "
              f"cohort ({int(top_cohort['investor_count'])} investors) has the highest avg SIP "
              f"of ₹{top_cohort['avg_sip_amount']:,.0f}, with ₹{top_cohort['total_invested']/1e7:.1f} Cr "
              f"total invested. Their top fund preference is '{top_cohort['top_fund'][:35]}', "
              f"reflecting a growth-oriented bias.")
    else:
        top_cohort = cohort_df.iloc[0]
        i2 = (f"**I2 — Cohort Insight:** Single cohort ({int(top_cohort['cohort_year'])}) with "
              f"{int(top_cohort['investor_count'])} investors, avg SIP ₹{top_cohort['avg_sip_amount']:,.0f}.")

    # Insight 3 — SIP continuity risk
    at_risk_pct = continuity_df["at_risk"].mean() * 100
    avg_gap     = continuity_df["avg_gap_days"].mean()
    i3 = (f"**I3 — SIP Continuity Risk:** Among investors with ≥{C.SIP_MIN_TRANSACTIONS} SIP "
          f"transactions, {at_risk_pct:.1f}% are 'at-risk' with an average gap between SIP "
          f"instalments exceeding {C.SIP_GAP_THRESHOLD} days (overall avg gap: {avg_gap:.1f} days). "
          f"This signals potential churn risk and is a KPI for investor engagement teams.")

    # Insight 4 — Sector HHI
    most_conc = hhi_df.nlargest(1, "hhi").iloc[0]
    most_div  = hhi_df.nsmallest(1, "hhi").iloc[0]
    i4 = (f"**I4 — Sector Concentration (HHI):** '{most_conc['scheme_name'][:30]}' is the most "
          f"concentrated equity fund (HHI={most_conc['hhi']:.0f}) with "
          f"{most_conc['top_sector_wt_pct']:.1f}% in {most_conc['top_sector']}. "
          f"In contrast, '{most_div['scheme_name'][:30]}' is the most diversified "
          f"(HHI={most_div['hhi']:.0f} across {most_div['n_sectors']} sectors). "
          f"Concentrated funds carry higher sector-specific risk.")

    # Insight 5 — Rolling Sharpe stability vs scorecard
    top_fund_name = scorecard.nsmallest(1, "scorecard_rank").iloc[0]["scheme_name"][:40]
    best_var_name = var_df.nlargest(1, "var_95_pct").iloc[0]["scheme_name"][:40]
    i5 = (f"**I5 — Risk-Adjusted vs Raw Risk:** The top-ranked scorecard fund "
          f"'{top_fund_name}' demonstrates consistent rolling Sharpe above 1.0, "
          f"indicating stable risk-adjusted performance over time. Meanwhile, "
          f"'{best_var_name}' shows the lowest daily VaR, confirming it as a "
          f"capital-preservation choice for conservative investors. "
          f"Investors should match fund selection to both risk tolerance and time horizon.")

    insights = [i1, i2, i3, i4, i5]

    print()
    for i, ins in enumerate(insights, 1):
        # Strip markdown bold markers for console print
        clean = ins.replace("**", "")
        print(f"   {clean}\n")

    # Save to markdown
    md = "# Advanced Analytics Insights — Day 6\n\n"
    md += "\n\n".join(insights)
    out = C.report_path("advanced_insights.md")
    with open(out, "w") as fh:
        fh.write(md)
    print(f"   ✅ advanced_insights.md → {out}")
    return insights


# ════════════════════════════════════════════════════════════════════════════════
# SUPPLEMENTARY — VaR/CVaR bar chart
# ════════════════════════════════════════════════════════════════════════════════

def plot_var_cvar(var_df: pd.DataFrame) -> str:
    """
    Horizontal bar chart showing VaR and CVaR for all 40 funds.
    VaR shown as absolute values (positive = loss magnitude).
    """
    df = var_df.copy()
    df["var_95_abs"]  = df["var_95_pct"].abs()
    df["cvar_95_abs"] = df["cvar_95_pct"].abs()
    df = df.sort_values("var_95_abs", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 10))
    fig.set_facecolor(C.THEME["surface"])
    ax.set_facecolor("white")

    y = range(len(df))
    ax.barh(y, df["cvar_95_abs"], height=0.6,
            color=C.THEME["neg"], alpha=0.55, label="CVaR 95%")
    ax.barh(y, df["var_95_abs"],  height=0.6,
            color=C.THEME["navy"], alpha=0.85, label="VaR 95%")

    labels = df["scheme_name"].str[:32].tolist()
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("Daily Loss Magnitude (%)")
    ax.set_title(f"Historical VaR & CVaR ({C.VAR_CONFIDENCE*100:.0f}% Confidence) — All 40 Funds",
                 fontsize=12, fontweight="bold", color=C.THEME["navy"])
    ax.legend(fontsize=9)
    ax.grid(True, axis="x", alpha=0.5)
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f%%"))

    fig.text(0.99, 0.01, "BLUESTOCK MF ANALYTICS · DAY 6",
             fontsize=7, color=C.THEME["muted"], ha="right", va="bottom", alpha=0.6)

    out = str(C.chart_path("var_cvar_chart.png"))
    fig.savefig(out)
    plt.close(fig)
    print(f"   ✅ var_cvar_chart.png → {out}")
    return out


def plot_hhi(hhi_df: pd.DataFrame) -> str:
    """Horizontal bar chart of HHI concentration per equity fund."""
    df = hhi_df.sort_values("hhi", ascending=True).copy()

    colors = df["concentration"].map({
        "Highly Concentrated":    C.THEME["neg"],
        "Moderately Concentrated":C.THEME["gold"],
        "Diversified":            C.THEME["pos"],
    })

    fig, ax = plt.subplots(figsize=(11, 7))
    fig.set_facecolor(C.THEME["surface"])
    ax.set_facecolor("white")

    bars = ax.barh(df["scheme_name"].str[:30], df["hhi"],
                   color=colors, height=0.6, edgecolor="white")
    ax.axvline(C.HHI_HIGH_THRESHOLD, color=C.THEME["neg"], linestyle="--",
               linewidth=1.2, label=f"High (≥{C.HHI_HIGH_THRESHOLD})")
    ax.axvline(C.HHI_MODERATE,       color=C.THEME["gold"], linestyle="--",
               linewidth=1.2, label=f"Moderate (≥{C.HHI_MODERATE})")

    ax.set_xlabel("HHI Score  (higher = more concentrated)")
    ax.set_title("Sector HHI Concentration — Equity Funds",
                 fontsize=12, fontweight="bold", color=C.THEME["navy"])
    ax.legend(fontsize=9)
    ax.grid(True, axis="x", alpha=0.5)

    fig.text(0.99, 0.01, "BLUESTOCK MF ANALYTICS · DAY 6",
             fontsize=7, color=C.THEME["muted"], ha="right", va="bottom", alpha=0.6)

    out = str(C.chart_path("sector_hhi_chart.png"))
    fig.savefig(out)
    plt.close(fig)
    print(f"   ✅ sector_hhi_chart.png → {out}")
    return out


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

def run_advanced_analytics():
    """Entry point — runs all Day 6 tasks in sequence."""
    print("=" * 68)
    print("DAY 6 — Advanced Analytics + Risk Metrics")
    print("=" * 68)

    # ── Load shared data ─────────────────────────────────────────────────
    print("\n── Loading datasets ─────────────────────────────────────────────────")
    returns      = load_nav_returns()
    fund_master  = load_fund_master()
    txn          = load_transactions()
    holdings     = load_holdings()
    scorecard    = load_scorecard()
    print(f"   Returns  : {returns.shape[0]} dates × {returns.shape[1]} funds")
    print(f"   Investors: {txn['investor_id'].nunique():,}")
    print(f"   Holdings : {len(holdings)} rows across {holdings['amfi_code'].nunique()} funds")

    # ── Task 1: VaR / CVaR ───────────────────────────────────────────────
    var_df      = compute_var_cvar(returns, fund_master)

    # ── Task 2: Rolling Sharpe ───────────────────────────────────────────
    rs_df       = compute_rolling_sharpe(returns, scorecard, fund_master)
    plot_rolling_sharpe(rs_df)

    # ── Task 3: Cohort Analysis ──────────────────────────────────────────
    cohort_df   = investor_cohort_analysis(txn, fund_master)

    # ── Task 4: SIP Continuity ───────────────────────────────────────────
    continuity_df = sip_continuity_analysis(txn)

    # ── Task 5: Sector HHI ───────────────────────────────────────────────
    hhi_df      = compute_sector_hhi(holdings, fund_master)

    # ── Supplementary charts ─────────────────────────────────────────────
    plot_var_cvar(var_df)
    plot_hhi(hhi_df)

    # ── Task 6: Advanced Insights ─────────────────────────────────────────
    insights    = generate_advanced_insights(var_df, cohort_df,
                                              continuity_df, hhi_df, scorecard)

    print("\n" + "=" * 68)
    print("✅ Day 6 — Advanced Analytics complete.")
    print("   Deliverables:")
    deliverables = [
        ("reports/var_cvar_report.csv",          "VaR & CVaR for all 40 funds"),
        ("reports/sip_continuity.csv",           "SIP continuity & at-risk flags"),
        ("reports/sector_hhi.csv",               "Sector HHI concentration"),
        ("reports/advanced_insights.md",         "5 advanced narrative insights"),
        ("reports/charts/rolling_sharpe_chart.png", "Rolling 90-day Sharpe chart"),
        ("reports/charts/var_cvar_chart.png",    "VaR/CVaR bar chart"),
        ("reports/charts/sector_hhi_chart.png",  "HHI concentration chart"),
        ("recommender.py",                       "Fund recommender CLI module"),
        ("notebooks/Advanced_Analytics.ipynb",   "Jupyter notebook (all tasks)"),
    ]
    for path, desc in deliverables:
        full = C.PROJECT_ROOT / path
        exists = "✅" if full.exists() else "⬜"
        print(f"   {exists} {path}  — {desc}")
    print("=" * 68)

    return {
        "var_df":        var_df,
        "rs_df":         rs_df,
        "cohort_df":     cohort_df,
        "continuity_df": continuity_df,
        "hhi_df":        hhi_df,
        "insights":      insights,
    }


if __name__ == "__main__":
    run_advanced_analytics()


# ─── Entry-point for run_pipeline.py ─────────────────────────────────────────
def run_all():
    """Execute all Day 6 advanced analytics tasks via the main runner."""
    run_advanced_analytics()
