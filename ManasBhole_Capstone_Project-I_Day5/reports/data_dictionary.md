# Data Dictionary — Bluestock MF Analytics
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
