"""
data_cleaning.py — Task 2: Data Cleaning + SQL Database Design
Capstone Project - I | Bluestock Mutual Fund Analytics

Steps:
 1. Clean nav_history.csv         → parse dates, sort, forward-fill, deduplicate, validate NAV > 0
 2. Clean investor_transactions.csv → standardise transaction_type, validate amount, fix dates, KYC enum
 3. Clean scheme_performance.csv  → validate return columns numeric, flag anomalies, check expense_ratio
 4. Design & create SQLite star schema (dim_fund, dim_date, fact_nav, fact_transactions,
    fact_performance, fact_aum)
 5. Load all cleaned datasets into SQLite (bluestock_mf.db) using sqlite3
 6. Write 10 analytical SQL queries to sql/queries.sql
 7. Generate data_dictionary.md in reports/
"""

import pandas as pd
import sqlite3
import os
import warnings
warnings.filterwarnings('ignore')

# ─── Paths ────────────────────────────────────────────────────────────────────
RAW_DIR       = 'data/raw/'
PROCESSED_DIR = 'data/processed/'
SQL_DIR       = 'sql/'
REPORTS_DIR   = 'reports/'
DB_PATH       = 'bluestock_mf.db'

for d in [PROCESSED_DIR, SQL_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)


# ─── Helper ───────────────────────────────────────────────────────────────────
def save_cleaned(df: pd.DataFrame, filename: str):
    path = os.path.join(PROCESSED_DIR, filename)
    df.to_csv(path, index=False)
    print(f"   ✅ Saved → {path}  ({len(df)} rows)")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Data Cleaning
# ═══════════════════════════════════════════════════════════════════════════════

def clean_nav_history() -> pd.DataFrame:
    """
    Clean nav_history.csv:
      - Parse dates to datetime
      - Sort by amfi_code + date
      - Forward-fill missing NAV for holidays/weekends (per fund)
      - Remove duplicate (amfi_code, date) rows
      - Validate NAV > 0
    """
    print("\n── Cleaning: nav_history.csv ─────────────────────────")
    df = pd.read_csv(os.path.join(RAW_DIR, '02_nav_history.csv'))
    before = len(df)

    # Parse dates
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    invalid_dates = df['date'].isna().sum()
    if invalid_dates:
        print(f"   ⚠️  {invalid_dates} rows with unparseable dates — dropping")
        df = df.dropna(subset=['date'])

    # Sort
    df = df.sort_values(['amfi_code', 'date']).reset_index(drop=True)

    # Remove duplicates (keep last)
    dups = df.duplicated(subset=['amfi_code', 'date'], keep='last').sum()
    if dups:
        print(f"   ⚠️  {dups} duplicate (amfi_code, date) rows removed")
        df = df.drop_duplicates(subset=['amfi_code', 'date'], keep='last')

    # Forward-fill missing NAV per fund (reindex to full date range per fund)
    df = df.set_index('date')
    filled_frames = []
    for code, grp in df.groupby('amfi_code'):
        full_idx = pd.date_range(grp.index.min(), grp.index.max(), freq='D')
        grp = grp.reindex(full_idx)
        grp['amfi_code'] = code
        grp['nav'] = grp['nav'].ffill()
        filled_frames.append(grp)
    df = pd.concat(filled_frames).reset_index().rename(columns={'index': 'date'})

    # Validate NAV > 0
    neg = (df['nav'] <= 0).sum()
    if neg:
        print(f"   ⚠️  {neg} rows with NAV ≤ 0 — dropping")
        df = df[df['nav'] > 0]

    print(f"   Rows: {before} → {len(df)}  |  Cols: {list(df.columns)}")
    save_cleaned(df, '02_nav_history_clean.csv')
    return df


def clean_investor_transactions() -> pd.DataFrame:
    """
    Clean investor_transactions.csv:
      - Standardise transaction_type to SIP / Lumpsum / Redemption
      - Validate amount_inr > 0
      - Fix transaction_date format
      - Validate kyc_status enum
    """
    print("\n── Cleaning: investor_transactions.csv ──────────────────")
    df = pd.read_csv(os.path.join(RAW_DIR, '08_investor_transactions.csv'))
    before = len(df)

    # Fix dates
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
    bad_dates = df['transaction_date'].isna().sum()
    if bad_dates:
        print(f"   ⚠️  {bad_dates} rows with bad transaction_date — dropping")
        df = df.dropna(subset=['transaction_date'])

    # Standardise transaction_type
    type_map = {
        'sip': 'SIP', 'Sip': 'SIP',
        'lumpsum': 'Lumpsum', 'Lump Sum': 'Lumpsum', 'lump_sum': 'Lumpsum',
        'redemption': 'Redemption', 'REDEMPTION': 'Redemption',
    }
    df['transaction_type'] = df['transaction_type'].replace(type_map)
    valid_types = {'SIP', 'Lumpsum', 'Redemption'}
    invalid_types = ~df['transaction_type'].isin(valid_types)
    if invalid_types.sum():
        print(f"   ⚠️  {invalid_types.sum()} rows with unrecognised transaction_type — dropping")
        df = df[~invalid_types]

    # Validate amount > 0
    bad_amt = (df['amount_inr'] <= 0).sum()
    if bad_amt:
        print(f"   ⚠️  {bad_amt} rows with amount_inr ≤ 0 — dropping")
        df = df[df['amount_inr'] > 0]

    # KYC status enum check
    valid_kyc = {'Verified', 'Pending', 'Rejected'}
    bad_kyc = ~df['kyc_status'].isin(valid_kyc)
    if bad_kyc.sum():
        print(f"   ⚠️  {bad_kyc.sum()} rows with invalid kyc_status")

    print(f"   Rows: {before} → {len(df)}  |  Cols: {list(df.columns)}")
    save_cleaned(df, '08_investor_transactions_clean.csv')
    return df


def clean_scheme_performance() -> pd.DataFrame:
    """
    Clean scheme_performance.csv:
      - Validate return columns are numeric
      - Flag anomalies (returns outside [-50, 150] %)
      - Check expense_ratio_pct in [0.1, 2.5]
    """
    print("\n── Cleaning: scheme_performance.csv ──────────────────────")
    df = pd.read_csv(os.path.join(RAW_DIR, '07_scheme_performance.csv'))
    before = len(df)

    return_cols = ['return_1yr_pct', 'return_3yr_pct', 'return_5yr_pct',
                   'benchmark_3yr_pct', 'alpha', 'beta', 'sharpe_ratio',
                   'sortino_ratio', 'std_dev_ann_pct', 'max_drawdown_pct']

    for col in return_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Flag anomalous return values
    for col in ['return_1yr_pct', 'return_3yr_pct', 'return_5yr_pct']:
        if col in df.columns:
            anomalies = df[(df[col] < -50) | (df[col] > 150)][col]
            if not anomalies.empty:
                print(f"   ⚠️  {len(anomalies)} anomalous values in {col}")

    # Check expense_ratio_pct range
    if 'expense_ratio_pct' in df.columns:
        out_range = df[(df['expense_ratio_pct'] < 0.1) | (df['expense_ratio_pct'] > 2.5)]
        if not out_range.empty:
            print(f"   ⚠️  {len(out_range)} rows with expense_ratio_pct outside [0.1, 2.5]")

    print(f"   Rows: {before} → {len(df)}  (no rows dropped — flagging only)")
    save_cleaned(df, '07_scheme_performance_clean.csv')
    return df


def clean_remaining_datasets():
    """Load and lightly clean remaining datasets, save to processed/."""
    remaining = {
        '01_fund_master.csv':       '01_fund_master_clean.csv',
        '03_aum_by_fund_house.csv': '03_aum_by_fund_house_clean.csv',
        '04_monthly_sip_inflows.csv': '04_monthly_sip_inflows_clean.csv',
        '05_category_inflows.csv':  '05_category_inflows_clean.csv',
        '06_industry_folio_count.csv': '06_industry_folio_count_clean.csv',
        '09_portfolio_holdings.csv': '09_portfolio_holdings_clean.csv',
        '10_benchmark_indices.csv': '10_benchmark_indices_clean.csv',
    }
    cleaned = {}
    for raw, clean in remaining.items():
        print(f"\n── Cleaning: {raw}")
        df = pd.read_csv(os.path.join(RAW_DIR, raw))
        # Parse any 'date' or 'month' columns
        for col in ['date', 'month', 'launch_date', 'portfolio_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        # Drop full-duplicate rows
        dup = df.duplicated().sum()
        if dup:
            print(f"   ⚠️  {dup} duplicate rows removed")
            df = df.drop_duplicates()
        save_cleaned(df, clean)
        cleaned[raw] = df
    return cleaned


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SQLite Star Schema Design & Load
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- ─── Dimension Tables ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER PRIMARY KEY,
    fund_house          TEXT NOT NULL,
    scheme_name         TEXT NOT NULL,
    category            TEXT,
    sub_category        TEXT,
    plan                TEXT,
    launch_date         TEXT,
    benchmark           TEXT,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      INTEGER,
    min_lumpsum_amount  INTEGER,
    fund_manager        TEXT,
    risk_category       TEXT,
    sebi_category_code  TEXT
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     TEXT PRIMARY KEY,   -- 'YYYY-MM-DD'
    year        INTEGER,
    month       INTEGER,
    quarter     INTEGER,
    day_of_week INTEGER,
    is_weekday  INTEGER             -- 1 = weekday, 0 = weekend
);

-- ─── Fact Tables ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code   INTEGER NOT NULL,
    date_id     TEXT    NOT NULL,
    nav         REAL    NOT NULL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date_id)   REFERENCES dim_date(date_id)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id      TEXT,
    transaction_date TEXT,
    amfi_code        INTEGER,
    transaction_type TEXT,
    amount_inr       REAL,
    state            TEXT,
    city             TEXT,
    city_tier        TEXT,
    age_group        TEXT,
    gender           TEXT,
    annual_income_lakh REAL,
    payment_mode     TEXT,
    kyc_status       TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_performance (
    perf_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER,
    scheme_name         TEXT,
    fund_house          TEXT,
    category            TEXT,
    plan                TEXT,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,
    aum_crore           REAL,
    expense_ratio_pct   REAL,
    morningstar_rating  INTEGER,
    risk_grade          TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id         TEXT,
    fund_house      TEXT,
    aum_lakh_crore  REAL,
    aum_crore       REAL,
    num_schemes     INTEGER,
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);
"""


def build_dim_date(nav_df: pd.DataFrame, txn_df: pd.DataFrame,
                   aum_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_date from union of all date columns."""
    dates = set()
    for df, col in [(nav_df, 'date'), (txn_df, 'transaction_date'), (aum_df, 'date')]:
        if col in df.columns:
            valid = pd.to_datetime(df[col], errors='coerce').dropna()
            dates.update(valid.dt.strftime('%Y-%m-%d').tolist())

    date_series = pd.to_datetime(sorted(dates))
    dim = pd.DataFrame({'date_id': date_series.strftime('%Y-%m-%d')})
    dim['year']        = date_series.year
    dim['month']       = date_series.month
    dim['quarter']     = date_series.quarter
    dim['day_of_week'] = date_series.dayofweek
    dim['is_weekday']  = (date_series.dayofweek < 5).astype(int)
    return dim


def load_to_sqlite(nav_df, txn_df, perf_df, aum_df, fund_master_df):
    """Create SQLite DB, apply star schema, load all tables."""
    print(f"\n── Creating SQLite database: {DB_PATH} ─────────────────")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Execute schema DDL
    for stmt in SCHEMA_SQL.strip().split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            cursor.execute(stmt)
    conn.commit()

    # dim_fund
    fund_master_df.to_sql('dim_fund', conn, if_exists='replace', index=False)
    print(f"   ✅ dim_fund          → {len(fund_master_df)} rows")

    # dim_date
    dim_date = build_dim_date(nav_df, txn_df, aum_df)
    dim_date.to_sql('dim_date', conn, if_exists='replace', index=False)
    print(f"   ✅ dim_date          → {len(dim_date)} rows")

    # fact_nav
    nav_load = nav_df.copy()
    nav_load['date'] = pd.to_datetime(nav_load['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    nav_load = nav_load.rename(columns={'date': 'date_id'})
    nav_load[['amfi_code', 'date_id', 'nav']].to_sql('fact_nav', conn, if_exists='replace', index=False)
    print(f"   ✅ fact_nav          → {len(nav_load)} rows")

    # fact_transactions
    txn_load = txn_df.copy()
    txn_load['transaction_date'] = pd.to_datetime(txn_load['transaction_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    txn_load.to_sql('fact_transactions', conn, if_exists='replace', index=False)
    print(f"   ✅ fact_transactions → {len(txn_load)} rows")

    # fact_performance
    perf_df.to_sql('fact_performance', conn, if_exists='replace', index=False)
    print(f"   ✅ fact_performance  → {len(perf_df)} rows")

    # fact_aum
    aum_load = aum_df.copy()
    aum_load['date'] = pd.to_datetime(aum_load['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    aum_load = aum_load.rename(columns={'date': 'date_id'})
    aum_load.to_sql('fact_aum', conn, if_exists='replace', index=False)
    print(f"   ✅ fact_aum         → {len(aum_load)} rows")

    # Verify row counts
    print("\n   Row-count verification:")
    for table in ['dim_fund', 'dim_date', 'fact_nav', 'fact_transactions',
                  'fact_performance', 'fact_aum']:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"     {table:<22} → {count:>8} rows")

    conn.commit()
    conn.close()
    print(f"\n   ✅ SQLite DB saved → {DB_PATH}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SQL Queries & Data Dictionary
# ═══════════════════════════════════════════════════════════════════════════════

QUERIES_SQL = """-- ============================================================
-- Analytical SQL Queries — Bluestock MF Analytics
-- Run against: bluestock_mf.db
-- ============================================================

-- Q1: Top 5 funds by AUM (from fact_performance)
SELECT scheme_name, fund_house, aum_crore
FROM   fact_performance
ORDER  BY aum_crore DESC
LIMIT  5;

-- Q2: Average NAV per month for each fund (2022–2026)
SELECT f.scheme_name,
       d.year,
       d.month,
       ROUND(AVG(n.nav), 4) AS avg_nav
FROM   fact_nav       n
JOIN   dim_date       d ON n.date_id   = d.date_id
JOIN   dim_fund       f ON n.amfi_code = f.amfi_code
GROUP  BY f.scheme_name, d.year, d.month
ORDER  BY f.scheme_name, d.year, d.month;

-- Q3: YoY SIP growth — compare total SIP per year
SELECT d.year,
       SUM(t.amount_inr) AS total_sip_inr,
       COUNT(*)          AS transaction_count
FROM   fact_transactions t
JOIN   dim_date          d ON t.transaction_date = d.date_id
WHERE  t.transaction_type = 'SIP'
GROUP  BY d.year
ORDER  BY d.year;

-- Q4: SIP transactions by state (top 10 states by volume)
SELECT state,
       COUNT(*)           AS txn_count,
       SUM(amount_inr)    AS total_amount_inr
FROM   fact_transactions
WHERE  transaction_type = 'SIP'
GROUP  BY state
ORDER  BY total_amount_inr DESC
LIMIT  10;

-- Q5: Funds with expense_ratio_pct < 1% (low-cost funds)
SELECT scheme_name, fund_house, plan, expense_ratio_pct, aum_crore
FROM   fact_performance
WHERE  expense_ratio_pct < 1.0
ORDER  BY expense_ratio_pct ASC;

-- Q6: Best performing funds by 3-year return
SELECT scheme_name, fund_house, category, return_3yr_pct,
       benchmark_3yr_pct,
       ROUND(return_3yr_pct - benchmark_3yr_pct, 2) AS alpha_vs_benchmark
FROM   fact_performance
WHERE  return_3yr_pct IS NOT NULL
ORDER  BY return_3yr_pct DESC
LIMIT  10;

-- Q7: Gender-wise SIP amount distribution
SELECT gender,
       COUNT(*)        AS investors,
       SUM(amount_inr) AS total_amount_inr,
       ROUND(AVG(amount_inr), 2) AS avg_amount_inr
FROM   fact_transactions
WHERE  transaction_type = 'SIP'
GROUP  BY gender;

-- Q8: AUM by fund house over time
SELECT date_id, fund_house, aum_crore
FROM   fact_aum
ORDER  BY fund_house, date_id;

-- Q9: Funds with highest Sharpe ratio (best risk-adjusted returns)
SELECT scheme_name, fund_house, sharpe_ratio, sortino_ratio,
       std_dev_ann_pct, risk_grade
FROM   fact_performance
WHERE  sharpe_ratio IS NOT NULL
ORDER  BY sharpe_ratio DESC
LIMIT  10;

-- Q10: Transaction count and volume by city tier (T30 vs B30)
SELECT city_tier,
       transaction_type,
       COUNT(*)        AS txn_count,
       SUM(amount_inr) AS total_amount_inr
FROM   fact_transactions
GROUP  BY city_tier, transaction_type
ORDER  BY city_tier, transaction_type;
"""


DATA_DICTIONARY_MD = """# Data Dictionary — Bluestock MF Analytics
## Database: bluestock_mf.db  |  Schema: Star Schema

---

## dim_fund (Dimension: Fund Master)
| Column | Type | Description |
|---|---|---|
| amfi_code | INTEGER PK | AMFI scheme code (unique identifier) |
| fund_house | TEXT | Name of the Asset Management Company |
| scheme_name | TEXT | Full scheme name |
| category | TEXT | Broad category (Equity / Debt / Hybrid) |
| sub_category | TEXT | Sub-category (Large Cap, Flexi Cap, etc.) |
| plan | TEXT | Regular or Direct plan |
| launch_date | TEXT | Scheme launch date (YYYY-MM-DD) |
| benchmark | TEXT | Benchmark index name |
| expense_ratio_pct | REAL | Annual expense ratio (%) |
| exit_load_pct | REAL | Exit load percentage |
| min_sip_amount | INTEGER | Minimum SIP amount (INR) |
| min_lumpsum_amount | INTEGER | Minimum lump-sum amount (INR) |
| fund_manager | TEXT | Fund manager name |
| risk_category | TEXT | SEBI risk grade |
| sebi_category_code | TEXT | SEBI category code |

---

## dim_date (Dimension: Date)
| Column | Type | Description |
|---|---|---|
| date_id | TEXT PK | Date in YYYY-MM-DD format |
| year | INTEGER | Calendar year |
| month | INTEGER | Month (1–12) |
| quarter | INTEGER | Quarter (1–4) |
| day_of_week | INTEGER | 0=Monday … 6=Sunday |
| is_weekday | INTEGER | 1 if weekday, 0 if weekend |

---

## fact_nav (Fact: Daily NAV)
| Column | Type | Description |
|---|---|---|
| nav_id | INTEGER PK | Auto-increment surrogate key |
| amfi_code | INTEGER FK | References dim_fund.amfi_code |
| date_id | TEXT FK | References dim_date.date_id |
| nav | REAL | Net Asset Value (INR) |

Source: 02_nav_history.csv

---

## fact_transactions (Fact: Investor Transactions)
| Column | Type | Description |
|---|---|---|
| txn_id | INTEGER PK | Auto-increment surrogate key |
| investor_id | TEXT | Anonymised investor identifier |
| transaction_date | TEXT | Date of transaction (YYYY-MM-DD) |
| amfi_code | INTEGER FK | References dim_fund.amfi_code |
| transaction_type | TEXT | SIP / Lumpsum / Redemption |
| amount_inr | REAL | Transaction amount in INR |
| state | TEXT | Investor state |
| city | TEXT | Investor city |
| city_tier | TEXT | T30 (top cities) or B30 (beyond top 30) |
| age_group | TEXT | Age bracket of investor |
| gender | TEXT | Male / Female / Other |
| annual_income_lakh | REAL | Self-declared annual income (₹ lakh) |
| payment_mode | TEXT | UPI / NEFT / Cheque etc. |
| kyc_status | TEXT | Verified / Pending / Rejected |

Source: 08_investor_transactions.csv

---

## fact_performance (Fact: Scheme Performance)
| Column | Type | Description |
|---|---|---|
| perf_id | INTEGER PK | Auto-increment surrogate key |
| amfi_code | INTEGER FK | References dim_fund.amfi_code |
| scheme_name | TEXT | Scheme name |
| fund_house | TEXT | AMC name |
| category | TEXT | Fund category |
| plan | TEXT | Regular or Direct |
| return_1yr_pct | REAL | 1-year trailing return (%) |
| return_3yr_pct | REAL | 3-year trailing return (%) |
| return_5yr_pct | REAL | 5-year trailing return (%) |
| benchmark_3yr_pct | REAL | Benchmark 3-year return (%) |
| alpha | REAL | Jensen's Alpha |
| beta | REAL | Market Beta |
| sharpe_ratio | REAL | Sharpe ratio |
| sortino_ratio | REAL | Sortino ratio |
| std_dev_ann_pct | REAL | Annualised standard deviation (%) |
| max_drawdown_pct | REAL | Maximum drawdown (%) |
| aum_crore | REAL | AUM in ₹ crore |
| expense_ratio_pct | REAL | Annual expense ratio (%) |
| morningstar_rating | INTEGER | Morningstar star rating (1–5) |
| risk_grade | TEXT | Low / Moderate / High / Very High |

Source: 07_scheme_performance.csv

---

## fact_aum (Fact: AUM by Fund House)
| Column | Type | Description |
|---|---|---|
| aum_id | INTEGER PK | Auto-increment surrogate key |
| date_id | TEXT FK | References dim_date.date_id |
| fund_house | TEXT | AMC name |
| aum_lakh_crore | REAL | AUM in ₹ lakh crore |
| aum_crore | REAL | AUM in ₹ crore |
| num_schemes | INTEGER | Number of active schemes |

Source: 03_aum_by_fund_house.csv
"""


def write_sql_files():
    schema_path  = os.path.join(SQL_DIR, 'schema.sql')
    queries_path = os.path.join(SQL_DIR, 'queries.sql')
    dd_path      = os.path.join(REPORTS_DIR, 'data_dictionary.md')

    with open(schema_path, 'w')  as f: f.write(SCHEMA_SQL)
    with open(queries_path, 'w') as f: f.write(QUERIES_SQL)
    with open(dd_path, 'w')      as f: f.write(DATA_DICTIONARY_MD)

    print(f"\n   📄 schema.sql         → {schema_path}")
    print(f"   📄 queries.sql        → {queries_path}")
    print(f"   📄 data_dictionary.md → {dd_path}")


def run_sample_queries():
    """Run Q1 and Q9 as a quick smoke-test."""
    print("\n── Sample Query Results ─────────────────────────────────")
    conn = sqlite3.connect(DB_PATH)

    print("\nQ1 — Top 5 funds by AUM:")
    q1 = pd.read_sql("SELECT scheme_name, fund_house, aum_crore FROM fact_performance ORDER BY aum_crore DESC LIMIT 5", conn)
    print(q1.to_string(index=False))

    print("\nQ5 — Funds with expense_ratio < 1%:")
    q5 = pd.read_sql("SELECT scheme_name, plan, expense_ratio_pct FROM fact_performance WHERE expense_ratio_pct < 1.0 ORDER BY expense_ratio_pct LIMIT 5", conn)
    print(q5.to_string(index=False))

    conn.close()


# ─── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("TASK 2 — Data Cleaning + SQL Database Design")
    print("="*55)

    # Step 1: Clean datasets
    nav_clean  = clean_nav_history()
    txn_clean  = clean_investor_transactions()
    perf_clean = clean_scheme_performance()
    others     = clean_remaining_datasets()

    fund_master = pd.read_csv(os.path.join(RAW_DIR, '01_fund_master.csv'))
    aum_df      = pd.read_csv(os.path.join(RAW_DIR, '03_aum_by_fund_house.csv'))

    # Step 2: Load to SQLite
    load_to_sqlite(nav_clean, txn_clean, perf_clean, aum_df, fund_master)

    # Step 3: Write SQL + data dictionary files
    print("\n── Writing SQL & documentation files ────────────────────")
    write_sql_files()

    # Step 4: Smoke-test queries
    run_sample_queries()

    print("\n✅ Task 2 — Data Cleaning + SQL Database Design complete.")
