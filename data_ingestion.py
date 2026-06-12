"""
data_ingestion.py — Task 1: Project Setup + Data Ingestion (ETL)
Capstone Project - I | Bluestock Mutual Fund Analytics

Covers:
 - Loading all 10 CSV datasets and printing shape, dtypes, head()
 - Documenting anomalies / quality summary
 - AMFI code validation (every fund_master code present in nav_history)
 - Explore fund_master: unique fund houses, categories, sub-categories, risk grades
"""

import pandas as pd
import os
import json

# ─── Path configuration ───────────────────────────────────────────────────────
RAW_DIR       = 'data/raw/'
PROCESSED_DIR = 'data/processed/'
REPORTS_DIR   = 'reports/'

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR,   exist_ok=True)


# ─── 1. Inspect all datasets ──────────────────────────────────────────────────
def inspect_datasets():
    """Load all CSV files from data/raw/, print shape, dtypes, and head()."""
    csv_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith('.csv')])

    if not csv_files:
        print("Error: No CSV files found in 'data/raw/'. Please check your folder.")
        return {}

    print(f"Found {len(csv_files)} datasets. Beginning ingestion and inspection...\n")
    datasets = {}

    for file in csv_files:
        file_path = os.path.join(RAW_DIR, file)
        print(f"{'='*55}")
        print(f"📄 DATASET: {file}")
        print(f"{'='*55}")

        try:
            df = pd.read_csv(file_path)
            datasets[file] = df

            print(f"\n📌 SHAPE (Rows × Columns): {df.shape}")
            print(f"\n📌 DATA TYPES:\n{df.dtypes}")
            print(f"\n📌 FIRST 5 ROWS:\n{df.head()}\n")
        except Exception as e:
            print(f"⚠️  Error reading {file}: {e}\n")

    return datasets


# ─── 2. Data quality / anomaly report ─────────────────────────────────────────
def document_anomalies(datasets: dict) -> dict:
    """
    For each dataset check for:
      - Missing values
      - Duplicate rows
      - Numeric columns with zero or negative values (where inappropriate)
    Returns a dict summary and writes reports/data_quality_summary.md
    """
    print("\n" + "="*55)
    print("🔍 DATA QUALITY / ANOMALY REPORT")
    print("="*55)

    quality_summary = {}

    for name, df in datasets.items():
        missing      = df.isnull().sum()
        missing_pct  = (missing / len(df) * 100).round(2)
        dup_rows     = df.duplicated().sum()

        anomalies = []

        # Missing values
        missing_cols = missing[missing > 0]
        if not missing_cols.empty:
            for col, cnt in missing_cols.items():
                anomalies.append(f"Missing: {col} → {cnt} nulls ({missing_pct[col]}%)")

        # Duplicates
        if dup_rows:
            anomalies.append(f"Duplicate rows: {dup_rows}")

        # Domain-specific checks
        if 'nav' in df.columns:
            neg_nav = (df['nav'] <= 0).sum()
            if neg_nav:
                anomalies.append(f"nav ≤ 0: {neg_nav} rows")

        if 'amount_inr' in df.columns:
            neg_amt = (df['amount_inr'] <= 0).sum()
            if neg_amt:
                anomalies.append(f"amount_inr ≤ 0: {neg_amt} rows")

        if 'expense_ratio_pct' in df.columns:
            out_of_range = ((df['expense_ratio_pct'] < 0.1) |
                            (df['expense_ratio_pct'] > 2.5)).sum()
            if out_of_range:
                anomalies.append(f"expense_ratio_pct outside [0.1–2.5]: {out_of_range} rows")

        quality_summary[name] = {
            'rows': len(df),
            'cols': len(df.columns),
            'missing_cells': int(missing.sum()),
            'duplicate_rows': int(dup_rows),
            'anomalies': anomalies,
        }

        status = "✅ CLEAN" if not anomalies else "⚠️  ANOMALIES FOUND"
        print(f"\n{status} — {name}")
        if anomalies:
            for a in anomalies:
                print(f"   • {a}")

    # Write markdown report
    md_lines = ["# Data Quality Summary\n"]
    for name, info in quality_summary.items():
        md_lines.append(f"## {name}")
        md_lines.append(f"- Rows: {info['rows']}  |  Cols: {info['cols']}")
        md_lines.append(f"- Missing cells: {info['missing_cells']}  |  "
                        f"Duplicate rows: {info['duplicate_rows']}")
        if info['anomalies']:
            md_lines.append("- **Anomalies:**")
            for a in info['anomalies']:
                md_lines.append(f"  - {a}")
        else:
            md_lines.append("- No anomalies detected.")
        md_lines.append("")

    report_path = os.path.join(REPORTS_DIR, 'data_quality_summary.md')
    with open(report_path, 'w') as fh:
        fh.write('\n'.join(md_lines))
    print(f"\n📝 Quality report written → {report_path}")

    return quality_summary


# ─── 3. Explore fund_master ────────────────────────────────────────────────────
def explore_fund_master(fund_master: pd.DataFrame):
    """Print unique fund houses, categories, sub-categories, and risk grades."""
    print("\n" + "="*55)
    print("📊 FUND MASTER EXPLORATION")
    print("="*55)

    print(f"\n📌 Unique Fund Houses ({fund_master['fund_house'].nunique()}):")
    for fh in sorted(fund_master['fund_house'].unique()):
        print(f"   • {fh}")

    print(f"\n📌 Unique Categories ({fund_master['category'].nunique()}):")
    for cat in sorted(fund_master['category'].unique()):
        print(f"   • {cat}")

    print(f"\n📌 Unique Sub-categories ({fund_master['sub_category'].nunique()}):")
    for sc in sorted(fund_master['sub_category'].unique()):
        print(f"   • {sc}")

    print(f"\n📌 Unique Risk Grades ({fund_master['risk_category'].nunique()}):")
    for rg in sorted(fund_master['risk_category'].unique()):
        print(f"   • {rg}")


# ─── 4. AMFI code validation ──────────────────────────────────────────────────
def validate_amfi_codes(fund_master: pd.DataFrame, nav_history: pd.DataFrame):
    """Confirm every amfi_code in fund_master exists in nav_history."""
    print("\n" + "="*55)
    print("🔍 AMFI CODE VALIDATION")
    print("="*55)

    master_codes = set(fund_master['amfi_code'].dropna().unique())
    nav_codes    = set(nav_history['amfi_code'].dropna().unique())

    print(f"Total unique AMFI codes in Fund Master : {len(master_codes)}")
    print(f"Total unique AMFI codes in NAV History : {len(nav_codes)}")

    missing_in_nav = master_codes - nav_codes
    if not missing_in_nav:
        print("\n✅ VALIDATION PASSED: Every AMFI code in fund_master exists in nav_history.")
    else:
        print(f"\n⚠️  VALIDATION WARNING: {len(missing_in_nav)} codes in fund_master missing from nav_history.")
        print(f"   Sample: {sorted(list(missing_in_nav))[:5]}")

    extra_in_nav = nav_codes - master_codes
    if extra_in_nav:
        print(f"\nℹ️  INFO: {len(extra_in_nav)} AMFI codes in nav_history have no entry in fund_master.")


# ─── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    datasets = inspect_datasets()

    if datasets:
        fund_master = datasets.get('01_fund_master.csv')
        nav_history = datasets.get('02_nav_history.csv')

        document_anomalies(datasets)
        explore_fund_master(fund_master)
        validate_amfi_codes(fund_master, nav_history)

        print("\n✅ Task 1 — Data Ingestion & ETL complete.")
