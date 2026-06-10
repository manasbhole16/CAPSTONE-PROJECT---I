"""
performance_analytics.py — Day 4: Fund Performance Analytics
Capstone Project - I | Bluestock Mutual Fund Analytics

Tasks:
  1. Compute daily returns for all 40 schemes
  2. Compute CAGR (1yr, 3yr, 5yr) — comparison table
  3. Sharpe Ratio  — (Rp - Rf) / Std(Rp) × √252, Rf = 6.5%
  4. Sortino Ratio — same but downside std deviation only
  5. Alpha & Beta  — OLS regression on Nifty 100 via scipy.stats.linregress
  6. Maximum Drawdown — min(NAV / running_max - 1), worst date range
  7. Fund Scorecard (0–100) composite ranking
  8. Benchmark comparison chart — top 5 funds vs Nifty 50 & Nifty 100
     Tracking error = std(fund_return - benchmark_return) × √252

Deliverables:
  - reports/fund_scorecard.csv
  - reports/alpha_beta.csv
  - reports/charts/16_benchmark_comparison.png
  - (notebook wrapper: Performance_Analytics.ipynb)
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from scipy import stats

warnings.filterwarnings('ignore')

# ─── Paths ────────────────────────────────────────────────────────────────────
RAW_DIR    = 'data/raw/'
PROC_DIR   = 'data/processed/'
REPORTS    = 'reports/'
CHARTS     = 'reports/charts/'

for d in [REPORTS, CHARTS]:
    os.makedirs(d, exist_ok=True)

# ─── Constants ────────────────────────────────────────────────────────────────
RF_ANNUAL  = 0.065          # Risk-free rate: RBI repo proxy 6.5%
RF_DAILY   = RF_ANNUAL / 252
TRADING_DAYS = 252

sns.set_theme(style='whitegrid', palette='tab10')
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10})


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _load(clean_name, raw_name):
    """Load cleaned version if available, else raw."""
    path = os.path.join(PROC_DIR, clean_name)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.read_csv(os.path.join(RAW_DIR, raw_name))


def _save_chart(fig, name):
    path = os.path.join(CHARTS, name)
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f"   📊 Saved → {path}")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Load & Prepare NAV Data
# ═══════════════════════════════════════════════════════════════════════════════

def load_nav_pivot() -> pd.DataFrame:
    """
    Load nav_history, parse dates, pivot to wide format:
    index = date, columns = amfi_code, values = nav.
    Only keeps trading days (non-NaN rows across majority of funds).
    """
    nav = _load('02_nav_history_clean.csv', '02_nav_history.csv')
    nav['date'] = pd.to_datetime(nav['date'], errors='coerce')
    nav = nav.dropna(subset=['date', 'nav'])
    nav = nav.sort_values(['amfi_code', 'date'])

    # Pivot: rows = dates, cols = amfi_codes
    pivot = nav.pivot_table(index='date', columns='amfi_code',
                             values='nav', aggfunc='last')
    pivot = pivot.sort_index()
    print(f"   NAV pivot: {pivot.shape[0]} dates × {pivot.shape[1]} funds")
    return pivot


def load_benchmark_pivot() -> pd.DataFrame:
    """Load benchmark_indices, pivot wide: index=date, cols=index_name."""
    bench = pd.read_csv(os.path.join(RAW_DIR, '10_benchmark_indices.csv'))
    bench['date'] = pd.to_datetime(bench['date'], errors='coerce')
    bench = bench.dropna(subset=['date'])
    pivot = bench.pivot_table(index='date', columns='index_name',
                               values='close_value', aggfunc='last')
    pivot = pivot.sort_index()
    return pivot


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Daily Returns
# ═══════════════════════════════════════════════════════════════════════════════

def compute_daily_returns(nav_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    daily_return = nav_t / nav_t-1 - 1  for all 40 schemes.
    Validates that distributions look reasonable (mean near 0, std ~1–2%).
    """
    print("\n── Daily Returns ──────────────────────────────────────")
    returns = nav_pivot.pct_change()           # nav_t / nav_t-1 - 1
    returns = returns.iloc[1:]                 # drop first NaN row

    # Validate: mean daily return should be near 0, std ~0.5–2%
    mean_ret = returns.mean()
    std_ret  = returns.std()
    print(f"   Daily returns shape  : {returns.shape}")
    print(f"   Mean daily return    : {mean_ret.mean()*100:.4f}%  (cross-fund avg)")
    print(f"   Avg daily std dev    : {std_ret.mean()*100:.4f}%   (should be ~0.5–2%)")
    print(f"   Any extreme outliers (|r|>20%): "
          f"{(returns.abs() > 0.20).sum().sum()} cells")

    # Clip extreme outliers (data artefacts from forward-fill gaps)
    returns = returns.clip(lower=-0.20, upper=0.20)
    return returns


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CAGR (1yr, 3yr, 5yr)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_cagr(nav_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    CAGR = (NAV_end / NAV_start) ^ (1/n) - 1
    n = number of years (1, 3, 5).
    Uses last available date as end date.
    """
    print("\n── CAGR Computation ───────────────────────────────────")
    end_date  = nav_pivot.index.max()
    nav_end   = nav_pivot.loc[end_date]

    results = {}
    periods = {
        '1yr':  1,
        '3yr':  3,
        '5yr':  5,
    }
    for label, years in periods.items():
        target_start = end_date - pd.DateOffset(years=years)
        # Find nearest available date on or after target
        valid_dates = nav_pivot.index[nav_pivot.index >= target_start]
        if len(valid_dates) == 0:
            print(f"   ⚠️  No data for {label} lookback")
            continue
        start_date = valid_dates[0]
        nav_start  = nav_pivot.loc[start_date]
        n          = (end_date - start_date).days / 365.25
        cagr       = (nav_end / nav_start) ** (1 / n) - 1
        results[f'cagr_{label}_pct'] = (cagr * 100).round(2)
        print(f"   {label}: start={start_date.date()}, "
              f"end={end_date.date()}, n={n:.2f}yr")

    cagr_df = pd.DataFrame(results)
    cagr_df.index.name = 'amfi_code'
    cagr_df = cagr_df.reset_index()
    print(f"   CAGR table shape: {cagr_df.shape}")
    return cagr_df


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Sharpe & Sortino Ratios
# ═══════════════════════════════════════════════════════════════════════════════

def compute_sharpe_sortino(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Sharpe  = (Rp - Rf) / Std(Rp) × √252
    Sortino = (Rp - Rf) / Std_down(Rp) × √252
    Rf = 6.5% annually → RF_DAILY per day.
    Uses full return history for each fund.
    """
    print("\n── Sharpe & Sortino Ratios ────────────────────────────")
    excess = returns - RF_DAILY   # daily excess return

    sharpe_list  = []
    sortino_list = []

    for code in returns.columns:
        r = returns[code].dropna()
        e = excess[code].dropna()

        if len(r) < 30:
            sharpe_list.append(np.nan)
            sortino_list.append(np.nan)
            continue

        # Sharpe
        sharpe = (e.mean() / r.std()) * np.sqrt(TRADING_DAYS)

        # Sortino — downside std (only negative-return days)
        downside = r[r < 0]
        if len(downside) > 1:
            downside_std = downside.std()
        else:
            downside_std = r.std()
        sortino = (e.mean() / downside_std) * np.sqrt(TRADING_DAYS)

        sharpe_list.append(round(sharpe, 4))
        sortino_list.append(round(sortino, 4))

    df = pd.DataFrame({
        'amfi_code':     returns.columns.tolist(),
        'sharpe_ratio_calc':  sharpe_list,
        'sortino_ratio_calc': sortino_list,
    })
    print(f"   Sharpe range : {df['sharpe_ratio_calc'].min():.3f} – "
          f"{df['sharpe_ratio_calc'].max():.3f}")
    print(f"   Sortino range: {df['sortino_ratio_calc'].min():.3f} – "
          f"{df['sortino_ratio_calc'].max():.3f}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Alpha & Beta (OLS on Nifty 100)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_alpha_beta(returns: pd.DataFrame,
                       bench_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    OLS regression: fund_return ~ nifty100_return
    Beta  = slope
    Alpha = intercept × 252  (annualised)
    Uses scipy.stats.linregress.
    """
    print("\n── Alpha & Beta (OLS on Nifty 100) ───────────────────")

    # Nifty 100 daily returns
    if 'NIFTY100' not in bench_pivot.columns:
        print("   ⚠️  NIFTY100 not in benchmark data — skipping Alpha/Beta")
        return pd.DataFrame(columns=['amfi_code', 'alpha_calc', 'beta_calc', 'r_squared'])

    nifty100 = bench_pivot['NIFTY100'].pct_change().dropna()

    records = []
    for code in returns.columns:
        fund_ret = returns[code].dropna()

        # Align dates
        aligned = pd.concat([fund_ret, nifty100], axis=1, join='inner').dropna()
        aligned.columns = ['fund', 'bench']

        if len(aligned) < 60:
            records.append({'amfi_code': code,
                            'alpha_calc': np.nan,
                            'beta_calc':  np.nan,
                            'r_squared':  np.nan})
            continue

        slope, intercept, r_value, p_value, std_err = stats.linregress(
            aligned['bench'], aligned['fund']
        )

        alpha_annual = intercept * TRADING_DAYS   # annualise daily intercept
        records.append({
            'amfi_code':   code,
            'alpha_calc':  round(alpha_annual * 100, 4),   # in %
            'beta_calc':   round(slope, 4),
            'r_squared':   round(r_value**2, 4),
            'p_value':     round(p_value, 6),
        })

    df = pd.DataFrame(records)
    print(f"   Alpha range : {df['alpha_calc'].min():.2f}% – "
          f"{df['alpha_calc'].max():.2f}%")
    print(f"   Beta range  : {df['beta_calc'].min():.3f} – "
          f"{df['beta_calc'].max():.3f}")
    print(f"   Avg R²      : {df['r_squared'].mean():.3f}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Maximum Drawdown
# ═══════════════════════════════════════════════════════════════════════════════

def compute_max_drawdown(nav_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Maximum Drawdown = min(NAV / running_max - 1) for each fund.
    Also identifies the drawdown start date (peak) and trough date.
    """
    print("\n── Maximum Drawdown ───────────────────────────────────")
    records = []
    for code in nav_pivot.columns:
        series = nav_pivot[code].dropna()
        if len(series) < 10:
            continue

        running_max = series.cummax()
        drawdown    = series / running_max - 1

        max_dd      = drawdown.min()
        trough_date = drawdown.idxmin()
        # Peak = last running-max date before the trough
        peak_date   = running_max.loc[:trough_date].idxmax()
        dd_duration = (trough_date - peak_date).days

        records.append({
            'amfi_code':       code,
            'max_drawdown_pct_calc': round(max_dd * 100, 2),
            'peak_date':       peak_date.strftime('%Y-%m-%d'),
            'trough_date':     trough_date.strftime('%Y-%m-%d'),
            'drawdown_days':   dd_duration,
        })

    df = pd.DataFrame(records)
    worst = df.nsmallest(3, 'max_drawdown_pct_calc')[
        ['amfi_code', 'max_drawdown_pct_calc', 'peak_date', 'trough_date']]
    print(f"   Worst 3 drawdowns:\n{worst.to_string(index=False)}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Fund Scorecard (0–100)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_scorecard(cagr_df, sharpe_df, alpha_df, dd_df, fund_master) -> pd.DataFrame:
    """
    Composite score (0–100):
      30% × 3yr CAGR rank
      25% × Sharpe rank
      20% × Alpha rank
      15% × Expense ratio rank (inverse — lower expense = better rank)
      10% × Max drawdown rank (inverse — smaller drawdown = better rank)

    Ranks are percentile ranks (0–100), higher = better.
    """
    print("\n── Fund Scorecard ─────────────────────────────────────")

    # Merge all metrics
    df = fund_master[['amfi_code', 'scheme_name', 'fund_house',
                       'category', 'plan', 'expense_ratio_pct']].copy()
    df = df.merge(cagr_df[['amfi_code', 'cagr_3yr_pct']],    on='amfi_code', how='left')
    df = df.merge(sharpe_df[['amfi_code', 'sharpe_ratio_calc']], on='amfi_code', how='left')
    df = df.merge(alpha_df[['amfi_code', 'alpha_calc']],      on='amfi_code', how='left')
    df = df.merge(dd_df[['amfi_code', 'max_drawdown_pct_calc']], on='amfi_code', how='left')

    n = len(df)

    def pct_rank(series, ascending=True):
        """Percentile rank (0–100). ascending=True: higher value → higher rank."""
        return series.rank(pct=True, ascending=ascending, na_option='bottom') * 100

    # Component ranks
    df['rank_cagr3']     = pct_rank(df['cagr_3yr_pct'])
    df['rank_sharpe']    = pct_rank(df['sharpe_ratio_calc'])
    df['rank_alpha']     = pct_rank(df['alpha_calc'])
    df['rank_expense']   = pct_rank(df['expense_ratio_pct'], ascending=False)  # inverse
    df['rank_drawdown']  = pct_rank(df['max_drawdown_pct_calc'], ascending=False)  # inverse

    # Composite score
    df['scorecard_100'] = (
        0.30 * df['rank_cagr3']   +
        0.25 * df['rank_sharpe']  +
        0.20 * df['rank_alpha']   +
        0.15 * df['rank_expense'] +
        0.10 * df['rank_drawdown']
    ).round(2)

    df = df.sort_values('scorecard_100', ascending=False).reset_index(drop=True)
    df['scorecard_rank'] = df.index + 1

    print(f"   Top 5 funds by scorecard:")
    top5_cols = ['scheme_name', 'scorecard_100', 'cagr_3yr_pct',
                 'sharpe_ratio_calc', 'alpha_calc']
    print(df[top5_cols].head(5).to_string(index=False))
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Benchmark Comparison Chart
# ═══════════════════════════════════════════════════════════════════════════════

def compute_tracking_error(fund_ret: pd.Series,
                            bench_ret: pd.Series) -> float:
    """Tracking error = std(fund_return - benchmark_return) × √252."""
    aligned = pd.concat([fund_ret, bench_ret], axis=1, join='inner').dropna()
    if len(aligned) < 10:
        return np.nan
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return diff.std() * np.sqrt(TRADING_DAYS) * 100   # in %


def chart_benchmark_comparison(nav_pivot: pd.DataFrame,
                                returns: pd.DataFrame,
                                bench_pivot: pd.DataFrame,
                                scorecard_df: pd.DataFrame,
                                fund_master: pd.DataFrame):
    """
    Plot top 5 scorecard funds vs Nifty 50 & Nifty 100 over 3 years.
    Normalises all series to 100 at start date.
    Also prints tracking errors.
    """
    print("\n── Benchmark Comparison Chart ─────────────────────────")

    # 3-year window
    end_date   = nav_pivot.index.max()
    start_date = end_date - pd.DateOffset(years=3)
    mask       = (nav_pivot.index >= start_date)

    # Top 5 funds by scorecard
    top5_codes = scorecard_df.head(5)['amfi_code'].tolist()
    name_map   = fund_master.set_index('amfi_code')['scheme_name'].str[:28].to_dict()

    # Benchmark series
    bench_cols = {'NIFTY50': 'Nifty 50', 'NIFTY100': 'Nifty 100'}
    bench_3yr  = bench_pivot.loc[bench_pivot.index >= start_date, list(bench_cols.keys())]

    fig, axes = plt.subplots(2, 1, figsize=(14, 12),
                             gridspec_kw={'height_ratios': [3, 1]})
    ax_main = axes[0]
    ax_te   = axes[1]

    # ── Main performance chart ──────────────────────────────────────────────
    colors_fund  = plt.cm.tab10(np.linspace(0, 0.5, 5))
    colors_bench = ['black', 'dimgrey']

    te_records = []

    for i, code in enumerate(top5_codes):
        if code not in nav_pivot.columns:
            continue
        series = nav_pivot.loc[mask, code].dropna()
        if len(series) < 5:
            continue
        # Normalise to 100 at first valid date
        norm = series / series.iloc[0] * 100
        label = name_map.get(code, str(code))
        ax_main.plot(norm.index, norm.values, linewidth=1.6,
                     color=colors_fund[i], label=label)

        # Tracking errors vs both benchmarks
        fr = returns[code].dropna() if code in returns.columns else pd.Series()
        for bench_col, bench_label in bench_cols.items():
            if bench_col in bench_pivot.columns:
                br = bench_pivot[bench_col].pct_change().dropna()
                te = compute_tracking_error(fr, br)
                te_records.append({
                    'Fund': label[:25],
                    f'TE vs {bench_label} (%)': round(te, 2) if not np.isnan(te) else '-'
                })

    # Benchmark lines
    for j, (col, label) in enumerate(bench_cols.items()):
        if col not in bench_3yr.columns:
            continue
        series = bench_3yr[col].dropna()
        if len(series) == 0:
            continue
        norm = series / series.iloc[0] * 100
        ax_main.plot(norm.index, norm.values, linewidth=2.2,
                     linestyle='--', color=colors_bench[j], label=label, zorder=5)

    ax_main.axhline(100, color='lightgrey', linewidth=0.8, linestyle=':')
    ax_main.set_title('Top 5 Funds vs Nifty 50 & Nifty 100 (3-Year Performance, Base = 100)',
                       fontsize=12, fontweight='bold')
    ax_main.set_ylabel('Normalised Value (Base = 100)')
    ax_main.set_xlabel('')
    ax_main.legend(loc='upper left', fontsize=8, ncol=2)
    ax_main.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0f'))

    # ── Tracking Error bar chart ────────────────────────────────────────────
    if te_records:
        te_df = pd.DataFrame(te_records)
        # Pivot for grouped bar — one row per fund, two cols for TE vs N50 / N100
        te_pivot = te_df.groupby('Fund').first()  # simplify

        # Recompute cleanly for bar chart
        te_bar = {}
        for i, code in enumerate(top5_codes):
            if code not in returns.columns:
                continue
            fr   = returns[code].dropna()
            row  = {}
            for col, bl in bench_cols.items():
                if col in bench_pivot.columns:
                    br = bench_pivot[col].pct_change().dropna()
                    row[bl] = compute_tracking_error(fr, br)
            te_bar[name_map.get(code, str(code))[:22]] = row

        te_plot = pd.DataFrame(te_bar).T.reset_index()
        te_plot.columns.name = None
        te_plot = te_plot.rename(columns={'index': 'Fund'})

        x = np.arange(len(te_plot))
        w = 0.35
        n50_col = 'Nifty 50'
        n100_col = 'Nifty 100'

        if n50_col in te_plot.columns:
            ax_te.bar(x - w/2, te_plot[n50_col], w, label='vs Nifty 50',
                      color='steelblue', alpha=0.8)
        if n100_col in te_plot.columns:
            ax_te.bar(x + w/2, te_plot[n100_col], w, label='vs Nifty 100',
                      color='coral', alpha=0.8)

        ax_te.set_xticks(x)
        ax_te.set_xticklabels(te_plot['Fund'], rotation=20, ha='right', fontsize=8)
        ax_te.set_title('Tracking Error vs Nifty 50 & Nifty 100 (Annualised %)',
                        fontsize=11, fontweight='bold')
        ax_te.set_ylabel('Tracking Error (%)')
        ax_te.legend(fontsize=9)

    plt.tight_layout(pad=2.5)
    _save_chart(fig, '16_benchmark_comparison.png')


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Save Deliverable CSVs
# ═══════════════════════════════════════════════════════════════════════════════

def save_deliverables(scorecard_df, alpha_df, cagr_df, sharpe_df, dd_df, fund_master):
    """Save fund_scorecard.csv and alpha_beta.csv to reports/."""

    # ── fund_scorecard.csv ──────────────────────────────────────────────────
    scorecard_out = scorecard_df[[
        'scorecard_rank', 'amfi_code', 'scheme_name', 'fund_house',
        'category', 'plan',
        'cagr_3yr_pct', 'sharpe_ratio_calc', 'sortino_ratio_calc',
        'alpha_calc', 'max_drawdown_pct_calc',
        'expense_ratio_pct', 'scorecard_100',
        'rank_cagr3', 'rank_sharpe', 'rank_alpha',
        'rank_expense', 'rank_drawdown',
    ]].copy() if 'sortino_ratio_calc' in scorecard_df.columns else scorecard_df

    # Merge sortino if missing from scorecard_df
    if 'sortino_ratio_calc' not in scorecard_out.columns:
        scorecard_out = scorecard_out.merge(
            sharpe_df[['amfi_code', 'sortino_ratio_calc']], on='amfi_code', how='left')

    scorecard_path = os.path.join(REPORTS, 'fund_scorecard.csv')
    scorecard_out.to_csv(scorecard_path, index=False)
    print(f"   📄 Saved → {scorecard_path}  ({len(scorecard_out)} rows)")

    # ── alpha_beta.csv ──────────────────────────────────────────────────────
    ab_out = alpha_df.merge(
        fund_master[['amfi_code', 'scheme_name', 'fund_house', 'category']],
        on='amfi_code', how='left'
    )
    cols = ['amfi_code', 'scheme_name', 'fund_house', 'category',
            'alpha_calc', 'beta_calc', 'r_squared']
    if 'p_value' in ab_out.columns:
        cols.append('p_value')
    ab_out = ab_out[cols]

    ab_path = os.path.join(REPORTS, 'alpha_beta.csv')
    ab_out.to_csv(ab_path, index=False)
    print(f"   📄 Saved → {ab_path}  ({len(ab_out)} rows)")

    return scorecard_path, ab_path


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Print Full Comparison Tables
# ═══════════════════════════════════════════════════════════════════════════════

def print_comparison_tables(scorecard_df, alpha_df, dd_df, fund_master):
    """Print nicely formatted comparison tables for all 40 funds."""

    name_map = fund_master.set_index('amfi_code')['scheme_name'].str[:30].to_dict()

    print("\n" + "="*70)
    print("📊 CAGR COMPARISON TABLE — ALL 40 FUNDS")
    print("="*70)
    cagr_cols = ['amfi_code', 'scheme_name', 'fund_house', 'category',
                 'cagr_1yr_pct', 'cagr_3yr_pct', 'cagr_5yr_pct',
                 'sharpe_ratio_calc', 'scorecard_100']
    disp = scorecard_df[[c for c in cagr_cols if c in scorecard_df.columns]].copy()
    disp['scheme_name'] = disp['scheme_name'].str[:28]
    print(disp.to_string(index=False))

    print("\n" + "="*70)
    print("📊 ALPHA & BETA TABLE — ALL 40 FUNDS")
    print("="*70)
    ab_disp = alpha_df.copy()
    ab_disp['scheme_name'] = ab_disp['amfi_code'].map(name_map)
    print(ab_disp[['scheme_name', 'alpha_calc', 'beta_calc',
                   'r_squared']].to_string(index=False))

    print("\n" + "="*70)
    print("📊 MAX DRAWDOWN TABLE — ALL 40 FUNDS")
    print("="*70)
    dd_disp = dd_df.copy()
    dd_disp['scheme_name'] = dd_disp['amfi_code'].map(name_map)
    dd_display = dd_disp.sort_values('max_drawdown_pct_calc')[
        ['scheme_name', 'max_drawdown_pct_calc', 'peak_date',
         'trough_date', 'drawdown_days']]
    print(dd_display.to_string(index=False))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_performance_analytics():
    print("="*70)
    print("DAY 4 — Fund Performance Analytics")
    print("="*70)

    fund_master = _load('01_fund_master_clean.csv', '01_fund_master.csv')

    # Step 1: Load NAV pivot and benchmark
    print("\n── Loading data ────────────────────────────────────────")
    nav_pivot   = load_nav_pivot()
    bench_pivot = load_benchmark_pivot()

    # Step 2: Daily returns
    returns = compute_daily_returns(nav_pivot)

    # Step 3: CAGR
    cagr_df = compute_cagr(nav_pivot)

    # Step 4: Sharpe & Sortino
    sharpe_df = compute_sharpe_sortino(returns)

    # Step 5: Alpha & Beta
    alpha_df = compute_alpha_beta(returns, bench_pivot)

    # Step 6: Max Drawdown
    dd_df = compute_max_drawdown(nav_pivot)

    # Step 7: Merge everything for scorecard
    # First enrich scorecard_df with sortino (needed for display)
    base_df = sharpe_df.merge(alpha_df[['amfi_code', 'alpha_calc']],
                               on='amfi_code', how='left')
    base_df = base_df.merge(cagr_df, on='amfi_code', how='left')
    base_df = base_df.merge(dd_df[['amfi_code', 'max_drawdown_pct_calc']],
                             on='amfi_code', how='left')

    scorecard_df = compute_scorecard(cagr_df, sharpe_df, alpha_df, dd_df, fund_master)

    # Bring sortino into scorecard for the CSV export
    scorecard_df = scorecard_df.merge(
        sharpe_df[['amfi_code', 'sortino_ratio_calc']], on='amfi_code', how='left')
    scorecard_df = scorecard_df.merge(
        cagr_df[['amfi_code', 'cagr_1yr_pct', 'cagr_5yr_pct']], on='amfi_code', how='left')

    # Step 8: Benchmark comparison chart
    chart_benchmark_comparison(nav_pivot, returns, bench_pivot, scorecard_df, fund_master)

    # Step 9: Save deliverables
    print("\n── Saving deliverables ─────────────────────────────────")
    save_deliverables(scorecard_df, alpha_df, cagr_df, sharpe_df, dd_df, fund_master)

    # Step 10: Print full tables
    print_comparison_tables(scorecard_df, alpha_df, dd_df, fund_master)

    print("\n" + "="*70)
    print("✅ Day 4 — Fund Performance Analytics complete.")
    print(f"   Deliverables:")
    print(f"   • reports/fund_scorecard.csv")
    print(f"   • reports/alpha_beta.csv")
    print(f"   • reports/charts/16_benchmark_comparison.png")
    print("="*70)


if __name__ == '__main__':
    run_performance_analytics()
