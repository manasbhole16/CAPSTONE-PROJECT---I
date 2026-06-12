# Capstone Project - I: Bluestock Mutual Fund Analytics

**Author:** Manas Bhole | **Organisation:** Bluestock Fintech | **Status:** ✅ Production-Ready

---

## Project Overview

An end-to-end Mutual Fund analytics platform built on **10 real-world datasets** covering 40 AMC schemes, 46,000+ NAV records, and 32,000+ investor transactions. The pipeline progresses from raw data ingestion through SQL modelling, EDA, performance analytics, advanced risk metrics, and an interactive dashboard — culminating in a rule-based fund recommender.

**Business Problem:** Retail investors and fund analysts lack a consolidated, data-driven view of mutual fund performance, investor behaviour, and risk-adjusted returns across India's AMC universe. This project addresses that gap with a fully automated analytics pipeline.

---

## Features

| Layer | Capability |
|---|---|
| ETL | 10-dataset ingestion, anomaly detection, AMFI code validation |
| SQL | SQLite star schema with 4 fact tables and 2 dimension tables |
| EDA | 15+ publication-quality charts saved to `reports/charts/` |
| Performance | CAGR (1/3/5yr), Sharpe, Sortino, Alpha/Beta, Max Drawdown, Scorecard |
| Risk | Historical VaR (95%) and CVaR, Rolling Sharpe, Sector HHI |
| Investor | Cohort analysis, SIP continuity scoring, at-risk flagging |
| Dashboard | 4-page HTML dashboard + PDF export + PNG screenshots |
| Recommender | Risk-appetite-driven fund recommendation engine |
| Config | Centralised config.py — zero hardcoded paths or constants |
| Orchestration | run_pipeline.py — single-command full pipeline execution |

---

## Architecture

```
run_pipeline.py  (Master Orchestrator - 7 Steps)
     |
     +-- Step 1: data_ingestion.py    --> reports/data_quality_summary.md
     +-- Step 2: data_cleaning.py     --> data/processed/ + bluestock_mf.db
     +-- Step 3: eda_analysis.py      --> reports/charts/ (15 PNGs)
     +-- Step 4: performance_analytics.py --> reports/fund_scorecard.csv
     +-- Step 5: advanced_analytics.py    --> reports/var_cvar_report.csv
     +-- Step 6: dashboard_export.py      --> dashboard/ (HTML + PDF)
     +-- Step 7: recommender.py           --> console output

All modules import from config.py (single source of truth)
```

---

## Folder Structure

```
Capstone Project - I/
|-- config.py                        Central configuration
|-- run_pipeline.py                  Master execution script
|-- data_ingestion.py                Step 1: ETL + anomaly detection
|-- data_cleaning.py                 Step 2: Cleaning + SQLite DB
|-- eda_analysis.py                  Step 3: 15-chart EDA
|-- performance_analytics.py         Step 4: CAGR, Sharpe, Scorecard
|-- advanced_analytics.py            Step 5: VaR, Rolling Sharpe, Cohort
|-- dashboard_export.py              Step 6: HTML dashboard + PDF
|-- recommender.py                   Step 7: Risk-based fund recommender
|-- live_nav_fetch.py                Utility: live NAV from mfapi.in
|-- bluestock_mf.db                  SQLite database (auto-generated)
|-- requirements_deploy.txt          Minimal runtime dependencies
|-- .env.example                     Environment variables template
|-- data/
|   |-- raw/                         10 original CSV datasets
|   +-- processed/                   10 cleaned CSV outputs
|-- sql/
|   |-- schema.sql                   Star-schema DDL
|   +-- queries.sql                  10 analytical SQL queries
|-- reports/
|   |-- charts/                      16+ PNG charts
|   |-- data_quality_summary.md
|   |-- data_dictionary.md
|   |-- eda_findings.md
|   |-- advanced_insights.md
|   |-- fund_scorecard.csv
|   |-- alpha_beta.csv
|   |-- var_cvar_report.csv
|   |-- sector_hhi.csv
|   +-- sip_continuity.csv
|-- dashboard/
|   |-- bluestock_mf_dashboard.html  Interactive HTML dashboard
|   |-- Dashboard.pdf                4-page dashboard PDF
|   +-- page1..4_*.png               Dashboard page screenshots
+-- notebooks/
    |-- Performance_Analytics.ipynb
    +-- Advanced_Analytics.ipynb
```

---

## Dataset Description

| # | File | Rows | Key Fields | Purpose |
|---|---|---|---|---|
| 01 | fund_master.csv | 40 | amfi_code, fund_house, scheme_name, category, risk_category | Fund metadata |
| 02 | nav_history.csv | 46,000 | amfi_code, date, nav | Daily NAV per scheme |
| 03 | aum_by_fund_house.csv | 90 | fund_house, year, aum_cr | AUM by AMC per year |
| 04 | monthly_sip_inflows.csv | 48 | month, sip_inflow_cr | Industry SIP totals |
| 05 | category_inflows.csv | 144 | month, category, net_inflow_cr | Category-level flows |
| 06 | industry_folio_count.csv | 21 | month, folio_count_cr | Total investor folios |
| 07 | scheme_performance.csv | 40 | amfi_code, return_1yr, return_3yr, return_5yr, expense_ratio | Scheme KPIs |
| 08 | investor_transactions.csv | 32,778 | investor_id, date, amfi_code, type, amount, state, age_group, gender | Transaction records |
| 09 | portfolio_holdings.csv | 322 | amfi_code, sector, weight_pct | Sector allocation |
| 10 | benchmark_indices.csv | 8,050 | date, index_name, nav | Benchmark index data |

---

## Installation Steps

```bash
# 1. Navigate to project directory
cd "Capstone Project - I"

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements_deploy.txt

# 4. Copy environment template (optional)
cp .env.example .env
```

---

## Environment Setup

All paths are resolved dynamically from the script location via config.py. No .env edits are required for default operation. Optional overrides are documented in .env.example.

---

## Configuration

Edit config.py to change:
- Directory paths (DIRS)
- Risk-free rate (RISK_FREE_RATE)
- VaR confidence level (VAR_CONFIDENCE)
- Rolling window (ROLLING_WINDOW)
- Recommender top-N (RECOMMENDER_TOP_N)
- Risk appetite mappings (RISK_APPETITE_MAP)

---

## Running ETL

```bash
python data_ingestion.py    # Step 1: load + inspect + anomaly report
python data_cleaning.py     # Step 2: clean + create SQLite DB
```

---

## Running Analytics

```bash
python eda_analysis.py             # 15-chart EDA
python performance_analytics.py   # CAGR, Sharpe, Scorecard
python advanced_analytics.py      # VaR, CVaR, Rolling Sharpe, Cohort
python recommender.py --risk Moderate  # Fund recommendations
```

---

## Running Dashboard

```bash
python dashboard_export.py
# Then open in browser:
open dashboard/bluestock_mf_dashboard.html
```

---

## Running the Full Pipeline

```bash
python run_pipeline.py              # All 7 steps
python run_pipeline.py --steps 1,2  # Specific steps only
python run_pipeline.py --skip 7     # Skip step 7
python run_pipeline.py --from 3     # Start from step 3
```

---

## KPIs

| KPI | Value |
|---|---|
| Best 3-yr Return | 23.4% (SBI Small Cap Fund) |
| Best Sharpe Ratio | 1.82 (ICICI Pru Midcap Fund) |
| SIP All-Time High | Rs 31,002 Cr (Dec 2025) |
| Folio Growth | +97% over project period |
| Direct vs Regular Expense Saving | 0.57% per year |
| Worst Daily VaR (95%) | -2.39% (ABSL Small Cap Fund) |
| SIP At-Risk Investor Rate | 97.8% |
| Most Concentrated Fund HHI | 2968 (Axis Bluechip — IT 48.7%) |

---

## Future Scope

1. Streamlit Web App with real-time AMFI API data
2. ML Return Predictor using ARIMA or Prophet
3. Portfolio Optimizer using Markowitz mean-variance
4. Automated Alerts for SIP continuity and VaR breaches
5. Docker containerisation and cloud deployment on Render
6. Scale to 1000+ schemes using AMFI bulk data feed

---

## Author

**Manas Bhole**
Internship Capstone Project | Bluestock Fintech
Data Analytics Engineering Track
