"""
dashboard_export.py — Day 5: Generate Dashboard PNG screenshots & PDF
Capstone Project - I | Bluestock Mutual Fund Analytics

Since Power BI / Tableau are desktop tools, this script produces:
  1. 4 high-quality PNG screenshots (one per dashboard page) using matplotlib
  2. Dashboard.pdf combining all 4 pages
  3. bluestock_mf_dashboard.html (already built — interactive web dashboard)

All outputs go to dashboard/ folder.
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as mtick
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

warnings.filterwarnings('ignore')

# ─── Paths ───────────────────────────────────────────────────────────────────
PROC   = 'data/processed/'
RAW    = 'data/raw/'
DASH   = 'dashboard/'
REPORT = 'reports/'
os.makedirs(DASH, exist_ok=True)

# ─── Bluestock theme ─────────────────────────────────────────────────────────
BS_NAVY   = '#0B1D3A'
BS_BLUE   = '#1565C0'
BS_TEAL   = '#00ACC1'
BS_GOLD   = '#F9A825'
BS_POS    = '#00897B'
BS_NEG    = '#D32F2F'
BS_MUTED  = '#6B7A99'
BS_SURF   = '#F4F6FB'
BS_PALETTE = [BS_BLUE, BS_TEAL, BS_GOLD, BS_POS, '#7B1FA2',
              '#E64A19', '#37474F', '#AD1457', '#558B2F', '#0277BD']

def apply_theme():
    plt.rcParams.update({
        'figure.facecolor':  BS_SURF,
        'axes.facecolor':    'white',
        'axes.edgecolor':    '#DDE3EF',
        'axes.labelcolor':   BS_NAVY,
        'axes.titlecolor':   BS_NAVY,
        'axes.titlesize':    11,
        'axes.titleweight':  'bold',
        'axes.labelsize':    9,
        'xtick.color':       BS_MUTED,
        'ytick.color':       BS_MUTED,
        'xtick.labelsize':   8,
        'ytick.labelsize':   8,
        'grid.color':        '#EEF1F7',
        'grid.alpha':        1.0,
        'font.family':       'DejaVu Sans',
        'figure.dpi':        150,
        'savefig.dpi':       150,
        'savefig.bbox':      'tight',
        'savefig.facecolor': BS_SURF,
    })

apply_theme()

# ─── Load data ────────────────────────────────────────────────────────────────
def load(clean, raw):
    p = os.path.join(PROC, clean)
    return pd.read_csv(p if os.path.exists(p) else os.path.join(RAW, raw))

aum_df    = load('03_aum_by_fund_house_clean.csv',    '03_aum_by_fund_house.csv')
sip_df    = load('04_monthly_sip_inflows_clean.csv',  '04_monthly_sip_inflows.csv')
folio_df  = load('06_industry_folio_count_clean.csv', '06_industry_folio_count.csv')
fund_df   = load('01_fund_master_clean.csv',          '01_fund_master.csv')
txn_df    = load('08_investor_transactions_clean.csv','08_investor_transactions.csv')
perf_df   = load('07_scheme_performance_clean.csv',   '07_scheme_performance.csv')
nav_df    = load('02_nav_history_clean.csv',          '02_nav_history.csv')
cat_df    = load('05_category_inflows_clean.csv',     '05_category_inflows.csv')
bench_df  = pd.read_csv(os.path.join(RAW, '10_benchmark_indices.csv'))
scorecard = pd.read_csv(os.path.join(REPORT, 'fund_scorecard.csv'))

# Parse dates
for df, col in [(aum_df,'date'), (sip_df,'month'), (folio_df,'month'),
                (txn_df,'transaction_date'), (nav_df,'date'),
                (cat_df,'month'), (bench_df,'date')]:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# ─── Helpers ──────────────────────────────────────────────────────────────────
def header_band(ax, title, subtitle=''):
    ax.set_title(title, fontsize=11, fontweight='bold', color=BS_NAVY,
                 pad=6, loc='left')
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1.01), xycoords='axes fraction',
                    fontsize=7.5, color=BS_MUTED, ha='left', va='bottom')

def page_title(fig, title, subtitle):
    fig.text(0.015, 0.975, title,   fontsize=16, fontweight='900',
             color=BS_NAVY, va='top')
    fig.text(0.015, 0.958, subtitle, fontsize=9,
             color=BS_MUTED, va='top')
    # Header line
    fig.add_artist(plt.Line2D([0.015, 0.985], [0.952, 0.952],
                              transform=fig.transFigure,
                              color=BS_BLUE, linewidth=1.5, alpha=0.4))

def kpi_card(ax, value, label, badge=None, badge_pos=True, color=BS_BLUE):
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    # Top accent bar
    ax.add_patch(FancyBboxPatch((0, 0.88), 1, 0.12,
                                boxstyle='round,pad=0', facecolor=color,
                                transform=ax.transAxes, clip_on=True, zorder=5))
    ax.text(0.5, 0.55, value, transform=ax.transAxes,
            fontsize=18, fontweight='900', color=BS_NAVY,
            ha='center', va='center')
    ax.text(0.5, 0.25, label, transform=ax.transAxes,
            fontsize=8, color=BS_MUTED, ha='center', va='center',
            fontweight='600')
    if badge:
        c = BS_POS if badge_pos else BS_NEG
        ax.text(0.5, 0.08, badge, transform=ax.transAxes,
                fontsize=7.5, color=c, ha='center', va='center', fontweight='700')


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — INDUSTRY OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
def build_page1():
    print("  Building Page 1 — Industry Overview...")
    fig = plt.figure(figsize=(16, 10))
    fig.set_facecolor(BS_SURF)
    page_title(fig, 'Industry Overview', 'Indian Mutual Fund Industry Snapshot · AUM, SIP Flows, Investor Base · Data as of Dec 2025')

    gs = gridspec.GridSpec(3, 4, figure=fig,
                           left=0.02, right=0.98, top=0.94, bottom=0.04,
                           hspace=0.45, wspace=0.35)

    # ── KPI Cards (row 0) ────────────────────────────────────────────────
    latest_aum = aum_df.groupby('fund_house').apply(
        lambda x: x.nlargest(1,'date')).reset_index(drop=True)
    total_aum = latest_aum['aum_lakh_crore'].sum()
    sip_latest = sip_df.sort_values('month').iloc[-1]['sip_inflow_crore']
    folio_latest = folio_df.sort_values('month').iloc[-1]['total_folios_crore']

    kpi_data = [
        (f'₹{total_aum:.1f} L Cr', 'TOTAL AUM', '↑ 18.3% YoY', True,  BS_BLUE),
        (f'₹{sip_latest:,.0f} Cr', 'SIP INFLOWS (Dec 2025)', '↑ ALL-TIME HIGH', True, BS_TEAL),
        (f'{folio_latest:.2f} Cr', 'TOTAL FOLIOS', '↑ 97% since Jan 2022', True, BS_GOLD),
        (f'{len(fund_df)} Schemes', 'SCHEMES IN DATABASE', '10 AMCs tracked', True, BS_POS),
    ]
    for i, (val, lbl, badge, bpos, col) in enumerate(kpi_data):
        ax = fig.add_subplot(gs[0, i])
        kpi_card(ax, val, lbl, badge, bpos, col)

    # ── AUM Trend (row 1, left 2 cols) ───────────────────────────────────
    ax_aum = fig.add_subplot(gs[1, :2])
    aum_trend = aum_df.groupby('date')['aum_lakh_crore'].sum().reset_index()
    ax_aum.plot(aum_trend['date'], aum_trend['aum_lakh_crore'],
                color=BS_BLUE, linewidth=2.5, marker='o', markersize=6,
                markerfacecolor='white', markeredgewidth=2)
    ax_aum.fill_between(aum_trend['date'], aum_trend['aum_lakh_crore'],
                        alpha=0.1, color=BS_BLUE)
    for _, row in aum_trend.iterrows():
        ax_aum.annotate(f'₹{row.aum_lakh_crore:.0f}L',
                        xy=(row.date, row.aum_lakh_crore),
                        xytext=(0, 7), textcoords='offset points',
                        fontsize=7, ha='center', color=BS_NAVY, fontweight='600')
    header_band(ax_aum, 'Industry AUM Trend 2022–2025',
                'Total Assets Under Management (₹ Lakh Crore)')
    ax_aum.yaxis.set_major_formatter(mtick.FormatStrFormatter('₹%.0f L'))
    ax_aum.grid(True, alpha=0.5)
    ax_aum.set_facecolor('white')

    # ── AUM by AMC (row 1, right 2 cols) ─────────────────────────────────
    ax_amc = fig.add_subplot(gs[1, 2:])
    latest_dt = aum_df['date'].max()
    amc_data = aum_df[aum_df['date'] == latest_dt].groupby('fund_house')['aum_lakh_crore'].sum().sort_values(ascending=True)
    colors = [BS_GOLD if 'SBI' in fh else BS_PALETTE[i % len(BS_PALETTE)]
              for i, fh in enumerate(amc_data.index)]
    bars = ax_amc.barh([fh.replace(' Mutual Fund','').replace(' MF','') for fh in amc_data.index],
                       amc_data.values, color=colors, height=0.6, edgecolor='white')
    for bar, val in zip(bars, amc_data.values):
        ax_amc.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                    f'₹{val:.1f}L', va='center', fontsize=7.5, color=BS_NAVY, fontweight='600')
    header_band(ax_amc, 'AUM by Asset Management Company',
                'Latest period · SBI leads at ₹12.5 Lakh Crore')
    ax_amc.set_xlabel('₹ Lakh Crore')
    ax_amc.set_facecolor('white')
    ax_amc.grid(True, axis='x', alpha=0.5)

    # ── SIP + Folio trend (row 2) ─────────────────────────────────────────
    ax_sip = fig.add_subplot(gs[2, :2])
    sip_sorted = sip_df.sort_values('month')
    ax_sip.bar(sip_sorted['month'], sip_sorted['sip_inflow_crore'],
               color=BS_TEAL, alpha=0.8, width=20)
    ath_row = sip_sorted.loc[sip_sorted['sip_inflow_crore'].idxmax()]
    ax_sip.annotate(f"ATH ₹{ath_row['sip_inflow_crore']:,.0f} Cr",
                    xy=(ath_row['month'], ath_row['sip_inflow_crore']),
                    xytext=(-60, -25), textcoords='offset points',
                    fontsize=8, color=BS_POS, fontweight='700',
                    arrowprops=dict(arrowstyle='->', color=BS_POS, lw=1.5))
    header_band(ax_sip, 'Monthly SIP Inflows (Jan 2022 – Dec 2025)',
                '₹ Crore · ATH = ₹31,002 Cr (Dec 2025)')
    ax_sip.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'₹{x/1000:.0f}K'))
    ax_sip.set_facecolor('white')
    ax_sip.grid(True, axis='y', alpha=0.5)

    ax_folio = fig.add_subplot(gs[2, 2:])
    folio_sorted = folio_df.sort_values('month')
    ax_folio.plot(folio_sorted['month'], folio_sorted['total_folios_crore'],
                  color=BS_NAVY, linewidth=2, label='Total')
    ax_folio.plot(folio_sorted['month'], folio_sorted['equity_folios_crore'],
                  color=BS_BLUE, linewidth=1.5, linestyle='--', label='Equity')
    ax_folio.annotate(f"{folio_sorted['total_folios_crore'].iloc[0]:.2f} Cr",
                      xy=(folio_sorted['month'].iloc[0], folio_sorted['total_folios_crore'].iloc[0]),
                      xytext=(5, 5), textcoords='offset points', fontsize=8, color=BS_NAVY)
    ax_folio.annotate(f"{folio_sorted['total_folios_crore'].iloc[-1]:.2f} Cr",
                      xy=(folio_sorted['month'].iloc[-1], folio_sorted['total_folios_crore'].iloc[-1]),
                      xytext=(-35, 5), textcoords='offset points', fontsize=8, color=BS_NAVY, fontweight='700')
    header_band(ax_folio, 'Folio Count Growth',
                '13.26 Cr (Jan 2022) → 26.12 Cr (Dec 2025)')
    ax_folio.legend(fontsize=8)
    ax_folio.set_facecolor('white')
    ax_folio.grid(True, alpha=0.5)

    # Bluestock branding
    fig.text(0.985, 0.01, 'BLUESTOCK MF ANALYTICS · CAPSTONE PROJECT I',
             fontsize=7, color=BS_MUTED, ha='right', va='bottom',
             fontweight='600', alpha=0.6)

    fig.savefig(f'{DASH}page1_industry_overview.png')
    plt.close(fig)
    print(f"    ✅ Saved → {DASH}page1_industry_overview.png")
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — FUND PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════
def build_page2():
    print("  Building Page 2 — Fund Performance...")
    fig = plt.figure(figsize=(16, 11))
    fig.set_facecolor(BS_SURF)
    page_title(fig, 'Fund Performance Analytics',
               'Risk-Return Scatter · Sortable Scorecard · NAV vs Benchmark · 40 Funds')

    gs = gridspec.GridSpec(2, 2, figure=fig,
                           left=0.05, right=0.97, top=0.93, bottom=0.04,
                           hspace=0.42, wspace=0.32)

    # ── Scatter: Return vs Risk ───────────────────────────────────────────
    ax_sc = fig.add_subplot(gs[0, 0])
    cat_map = {'Equity': BS_BLUE, 'Debt': '#7B1FA2', 'Hybrid': BS_POS}
    for cat, col in cat_map.items():
        sub = perf_df[perf_df['category'] == cat]
        sizes = np.clip(sub['aum_crore'] / 800, 20, 400)
        ax_sc.scatter(sub['return_3yr_pct'], sub['std_dev_ann_pct'],
                      s=sizes, c=col, alpha=0.75, edgecolors=col,
                      linewidths=0.5, label=cat)
    # Annotate top 3
    top3 = scorecard.nsmallest(3,'scorecard_rank')
    for _, row in top3.iterrows():
        match = perf_df[perf_df['amfi_code'] == row['amfi_code']]
        if not match.empty:
            r = match.iloc[0]
            ax_sc.annotate(r['scheme_name'][:18],
                           xy=(r['return_3yr_pct'], r['std_dev_ann_pct']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=6.5, color=BS_NAVY, fontweight='600',
                           arrowprops=dict(arrowstyle='->', color=BS_MUTED, lw=0.8))
    header_band(ax_sc, 'Return vs Risk (Bubble = AUM)',
                '3yr CAGR (X) vs Annualised Std Dev (Y)')
    ax_sc.set_xlabel('3yr CAGR (%)')
    ax_sc.set_ylabel('Annualised Std Dev (%)')
    ax_sc.legend(fontsize=8)
    ax_sc.set_facecolor('white')
    ax_sc.grid(True, alpha=0.5)

    # ── NAV vs Benchmark ─────────────────────────────────────────────────
    ax_nav = fig.add_subplot(gs[0, 1])
    nav_df2 = nav_df.copy()
    nav_df2['date'] = pd.to_datetime(nav_df2['date'])
    top3_codes = scorecard.nsmallest(3,'scorecard_rank')['amfi_code'].tolist()
    name_map = fund_df.set_index('amfi_code')['scheme_name'].str[:22].to_dict()

    for i, code in enumerate(top3_codes):
        series = nav_df2[nav_df2['amfi_code']==code].set_index('date')['nav'].sort_index()
        norm   = series / series.iloc[0] * 100
        ax_nav.plot(norm.index, norm.values, linewidth=1.8,
                    color=BS_PALETTE[i], label=name_map.get(code, str(code)))

    # Nifty 50
    n50 = bench_df[bench_df['index_name']=='NIFTY50'].set_index('date')['close_value'].sort_index()
    n50_norm = n50 / n50.iloc[0] * 100
    ax_nav.plot(n50_norm.index, n50_norm.values, color='#37474F',
                linestyle='--', linewidth=2, label='Nifty 50')
    ax_nav.axhline(100, color=BS_MUTED, linewidth=0.7, linestyle=':', alpha=0.6)
    header_band(ax_nav, 'NAV vs Benchmark (Base = 100)',
                'Top 3 scorecard funds vs Nifty 50')
    ax_nav.legend(fontsize=7.5, loc='upper left')
    ax_nav.set_facecolor('white')
    ax_nav.grid(True, alpha=0.5)

    # ── Scorecard table (row 1, full width) ──────────────────────────────
    ax_tbl = fig.add_subplot(gs[1, :])
    ax_tbl.set_facecolor('white')
    ax_tbl.axis('off')

    tbl_data = scorecard.merge(
        perf_df[['amfi_code','return_1yr_pct','std_dev_ann_pct']],
        on='amfi_code', how='left'
    ).nsmallest(15, 'scorecard_rank')

    cols = ['scorecard_rank','scheme_name','category','scorecard_100',
            'cagr_3yr_pct','sharpe_ratio_calc','alpha_calc','max_drawdown_pct_calc','expense_ratio_pct']
    headers = ['Rank','Fund Name','Cat','Score','3yr CAGR','Sharpe','Alpha','Max DD','Expense']

    table_vals = []
    for _, row in tbl_data.iterrows():
        table_vals.append([
            int(row['scorecard_rank']),
            str(row['scheme_name'])[:30],
            str(row['category']),
            f"{row['scorecard_100']:.1f}",
            f"{row['cagr_3yr_pct']:.1f}%",
            f"{row['sharpe_ratio_calc']:.2f}" if pd.notna(row['sharpe_ratio_calc']) else '-',
            f"{row['alpha_calc']:.1f}%" if pd.notna(row['alpha_calc']) else '-',
            f"{row['max_drawdown_pct_calc']:.1f}%" if pd.notna(row['max_drawdown_pct_calc']) else '-',
            f"{row['expense_ratio_pct']:.2f}%",
        ])

    tbl = ax_tbl.table(cellText=table_vals, colLabels=headers,
                       loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.35)

    # Style header
    for j in range(len(headers)):
        tbl[(0, j)].set_facecolor(BS_NAVY)
        tbl[(0, j)].set_text_props(color='white', fontweight='bold', fontsize=8)

    # Alternate rows + rank highlights
    for i in range(1, len(table_vals)+1):
        bg = '#F9FAFB' if i % 2 == 0 else 'white'
        rank = int(tbl[(i,0)].get_text().get_text())
        if rank <= 3:
            tbl[(i, 0)].set_facecolor(BS_GOLD)
            tbl[(i, 0)].set_text_props(color='white', fontweight='900')
        for j in range(len(headers)):
            if rank > 3:
                tbl[(i, j)].set_facecolor(bg)
            tbl[(i, j)].set_edgecolor('#E8ECF2')

    header_band(ax_tbl, 'Fund Scorecard — Top 15 Funds',
                'Composite: 30% 3yr CAGR + 25% Sharpe + 20% Alpha + 15% Expense (inv) + 10% Max DD (inv)')

    fig.text(0.985, 0.01, 'BLUESTOCK MF ANALYTICS · CAPSTONE PROJECT I',
             fontsize=7, color=BS_MUTED, ha='right', va='bottom', fontweight='600', alpha=0.6)

    fig.savefig(f'{DASH}page2_fund_performance.png')
    plt.close(fig)
    print(f"    ✅ Saved → {DASH}page2_fund_performance.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — INVESTOR ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
def build_page3():
    print("  Building Page 3 — Investor Analytics...")
    fig = plt.figure(figsize=(16, 11))
    fig.set_facecolor(BS_SURF)
    page_title(fig, 'Investor Analytics',
               'Geographic Distribution · Demographics · Transaction Patterns · City Tier Breakdown')

    gs = gridspec.GridSpec(2, 3, figure=fig,
                           left=0.05, right=0.97, top=0.93, bottom=0.04,
                           hspace=0.45, wspace=0.38)

    # ── State bar ────────────────────────────────────────────────────────
    ax_state = fig.add_subplot(gs[0, :2])
    state_data = txn_df.groupby('state')['amount_inr'].sum().sort_values(ascending=True)
    colors_s = [BS_PALETTE[i % len(BS_PALETTE)] for i in range(len(state_data))]
    ax_state.barh(state_data.index, state_data.values / 1e7, color=colors_s, height=0.6)
    header_band(ax_state, 'Transaction Amount by State',
                'Total investment flow (₹ Crore) · all transaction types')
    ax_state.set_xlabel('₹ Crore')
    ax_state.set_facecolor('white')
    ax_state.grid(True, axis='x', alpha=0.5)

    # ── Txn type donut ───────────────────────────────────────────────────
    ax_donut = fig.add_subplot(gs[0, 2])
    txn_type = txn_df.groupby('transaction_type')['amount_inr'].sum()
    wedges, texts, autotexts = ax_donut.pie(
        txn_type.values, labels=txn_type.index,
        autopct='%1.1f%%',
        colors=[BS_BLUE, BS_TEAL, BS_GOLD],
        startangle=140, pctdistance=0.82,
        wedgeprops=dict(width=0.55)
    )
    for t in autotexts: t.set_fontsize(9); t.set_fontweight('bold')
    header_band(ax_donut, 'Transaction Type Split', 'SIP / Lumpsum / Redemption')
    ax_donut.set_facecolor('white')

    # ── Age group bar ────────────────────────────────────────────────────
    ax_age = fig.add_subplot(gs[1, 0])
    order = ['18-25','26-35','36-45','46-55','56+']
    sip_txn = txn_df[txn_df['transaction_type'] == 'SIP']
    age_bar = sip_txn.groupby('age_group')['amount_inr'].mean().reindex(order).dropna()
    ax_age.bar(age_bar.index, age_bar.values,
               color=BS_PALETTE[:len(age_bar)], edgecolor='white', width=0.6)
    header_band(ax_age, 'Avg SIP Amount by Age Group', 'Mean SIP ticket size (₹)')
    ax_age.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'₹{x:,.0f}'))
    ax_age.set_facecolor('white')
    ax_age.grid(True, axis='y', alpha=0.5)

    # ── Monthly txn volume ───────────────────────────────────────────────
    ax_mv = fig.add_subplot(gs[1, 1])
    txn_df2 = txn_df.copy()
    txn_df2['month'] = txn_df2['transaction_date'].dt.to_period('M').dt.to_timestamp()
    monthly = txn_df2.groupby('month')['amount_inr'].sum() / 1e7
    ax_mv.plot(monthly.index, monthly.values, color=BS_POS, linewidth=2,
               marker='o', markersize=4)
    ax_mv.fill_between(monthly.index, monthly.values, alpha=0.1, color=BS_POS)
    header_band(ax_mv, 'Monthly Transaction Volume', 'Total flows (₹ Crore)')
    ax_mv.set_facecolor('white')
    ax_mv.grid(True, alpha=0.5)
    ax_mv.yaxis.set_major_formatter(mtick.FormatStrFormatter('₹%.0f Cr'))

    # ── T30 vs B30 ───────────────────────────────────────────────────────
    ax_tier = fig.add_subplot(gs[1, 2])
    tier = txn_df.groupby('city_tier')['amount_inr'].sum()
    ax_tier.pie(tier.values, labels=tier.index, autopct='%1.1f%%',
                colors=[BS_BLUE, BS_TEAL], startangle=90,
                explode=[0.04]*len(tier), wedgeprops=dict(edgecolor='white', linewidth=2))
    header_band(ax_tier, 'T30 vs B30 City Tier', 'Top 30 cities vs Beyond-30')
    ax_tier.set_facecolor('white')

    fig.text(0.985, 0.01, 'BLUESTOCK MF ANALYTICS · CAPSTONE PROJECT I',
             fontsize=7, color=BS_MUTED, ha='right', va='bottom', fontweight='600', alpha=0.6)

    fig.savefig(f'{DASH}page3_investor_analytics.png')
    plt.close(fig)
    print(f"    ✅ Saved → {DASH}page3_investor_analytics.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — SIP & MARKET TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
def build_page4():
    print("  Building Page 4 — SIP & Market Trends...")
    fig = plt.figure(figsize=(16, 11))
    fig.set_facecolor(BS_SURF)
    page_title(fig, 'SIP & Market Trends',
               'Monthly SIP vs Nifty 50 · Category Inflow Heatmap · Top 5 FY25 Categories')

    gs = gridspec.GridSpec(2, 2, figure=fig,
                           left=0.06, right=0.97, top=0.93, bottom=0.04,
                           hspace=0.45, wspace=0.35)

    # ── Dual-axis: SIP bar + Nifty 50 line ───────────────────────────────
    ax_dual = fig.add_subplot(gs[0, :])
    ax2     = ax_dual.twinx()

    sip_sorted = sip_df.sort_values('month')
    n50 = bench_df[bench_df['index_name']=='NIFTY50'].sort_values('date')
    # Monthly Nifty50
    n50['month_p'] = n50['date'].dt.to_period('M').dt.to_timestamp()
    n50m = n50.groupby('month_p')['close_value'].last().reset_index()

    bars = ax_dual.bar(sip_sorted['month'], sip_sorted['sip_inflow_crore'],
                       width=20, color=BS_BLUE, alpha=0.75, label='SIP Inflow (₹ Cr)')
    ax2.plot(n50m['month_p'], n50m['close_value'], color=BS_GOLD,
             linewidth=2.5, label='Nifty 50', marker='o', markersize=2)

    # ATH annotation
    ath = sip_sorted.loc[sip_sorted['sip_inflow_crore'].idxmax()]
    ax_dual.annotate(f"ATH ₹{ath['sip_inflow_crore']:,.0f} Cr",
                     xy=(ath['month'], ath['sip_inflow_crore']),
                     xytext=(-50, -20), textcoords='offset points',
                     fontsize=8.5, color=BS_POS, fontweight='700',
                     arrowprops=dict(arrowstyle='->', color=BS_POS, lw=1.5))

    ax_dual.set_ylabel('SIP Inflow (₹ Cr)', color=BS_BLUE, fontweight='700', fontsize=9)
    ax2.set_ylabel('Nifty 50 Index', color=BS_GOLD, fontweight='700', fontsize=9)
    ax_dual.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'₹{x/1000:.0f}K'))
    header_band(ax_dual, 'SIP Inflow (Bar) + Nifty 50 (Line) — Dual Axis 2022–2025',
                'Monthly SIP flows vs equity market movement')

    lines1, labels1 = ax_dual.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax_dual.legend(lines1+lines2, labels1+labels2, loc='upper left', fontsize=9)
    ax_dual.set_facecolor('white')
    ax_dual.grid(True, axis='y', alpha=0.4)

    # ── Category Inflow Heatmap ───────────────────────────────────────────
    ax_heat = fig.add_subplot(gs[1, 0])
    top_cats = cat_df.groupby('category')['net_inflow_crore'].sum().nlargest(7).index
    cat_f = cat_df[cat_df['category'].isin(top_cats)].copy()
    cat_f['month_str'] = cat_f['month'].dt.strftime('%Y-%m')
    pivot = cat_f.pivot_table(index='category', columns='month_str',
                               values='net_inflow_crore', aggfunc='sum').fillna(0)
    # Keep most recent 12 months
    pivot = pivot[sorted(pivot.columns)[-12:]]
    sns.heatmap(pivot, ax=ax_heat, cmap='YlOrRd', linewidths=0.3,
                linecolor='#EEF1F7', annot=True, fmt='.0f',
                annot_kws={'size': 7},
                cbar_kws={'shrink': 0.8, 'label': '₹ Crore'})
    header_band(ax_heat, 'Category Inflow Heatmap',
                'Net inflows by category & month (₹ Crore) · last 12 months')
    plt.setp(ax_heat.get_xticklabels(), rotation=45, ha='right', fontsize=7)
    plt.setp(ax_heat.get_yticklabels(), fontsize=8)

    # ── Top 5 FY25 bar ───────────────────────────────────────────────────
    ax_top5 = fig.add_subplot(gs[1, 1])
    fy25 = cat_df[(cat_df['month'] >= '2024-04-01') & (cat_df['month'] <= '2025-03-31')]
    top5 = fy25.groupby('category')['net_inflow_crore'].sum().nlargest(5).sort_values()
    bars = ax_top5.barh(top5.index, top5.values,
                        color=BS_PALETTE[:5], height=0.55, edgecolor='white')
    for bar, val in zip(bars, top5.values):
        ax_top5.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
                     f'₹{val/1000:.0f}K Cr', va='center', fontsize=8,
                     color=BS_NAVY, fontweight='700')
    header_band(ax_top5, 'Top 5 Categories — Net Inflow FY 2024–25',
                'April 2024 to March 2025 cumulative (₹ Crore)')
    ax_top5.set_xlabel('Net Inflow (₹ Crore)')
    ax_top5.set_facecolor('white')
    ax_top5.grid(True, axis='x', alpha=0.5)
    ax_top5.set_xlim(0, top5.max() * 1.2)

    fig.text(0.985, 0.01, 'BLUESTOCK MF ANALYTICS · CAPSTONE PROJECT I',
             fontsize=7, color=BS_MUTED, ha='right', va='bottom', fontweight='600', alpha=0.6)

    fig.savefig(f'{DASH}page4_sip_market_trends.png')
    plt.close(fig)
    print(f"    ✅ Saved → {DASH}page4_sip_market_trends.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
def build_pdf():
    print("  Building Dashboard.pdf...")
    pdf_path = f'{DASH}Dashboard.pdf'
    pages = [
        f'{DASH}page1_industry_overview.png',
        f'{DASH}page2_fund_performance.png',
        f'{DASH}page3_investor_analytics.png',
        f'{DASH}page4_sip_market_trends.png',
    ]
    with PdfPages(pdf_path) as pdf:
        for pg_path in pages:
            if os.path.exists(pg_path):
                img = plt.imread(pg_path)
                fig, ax = plt.subplots(figsize=(16, 10))
                fig.set_facecolor(BS_SURF)
                ax.imshow(img)
                ax.axis('off')
                plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                pdf.savefig(fig, dpi=150)
                plt.close(fig)
    print(f"    ✅ Saved → {pdf_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("="*65)
    print("DAY 5 — Dashboard Export (4 PNG Pages + PDF)")
    print("="*65)
    build_page1()
    build_page2()
    build_page3()
    build_page4()
    build_pdf()
    print("\n" + "="*65)
    print("✅ Day 5 Dashboard Export Complete")
    print("   Deliverables:")
    for f in ['page1_industry_overview.png','page2_fund_performance.png',
              'page3_investor_analytics.png','page4_sip_market_trends.png','Dashboard.pdf']:
        path = DASH + f
        size = os.path.getsize(path) // 1024
        print(f"   • {path}  ({size} KB)")
    print("   • dashboard/bluestock_mf_dashboard.html  (interactive)")
    print("="*65)


# ─── Entry-point for run_pipeline.py ─────────────────────────────────────────
def run_all():
    """Generate all dashboard outputs (4 PNG pages + PDF)."""
    build_page1()
    build_page2()
    build_page3()
    build_page4()
    build_pdf()
