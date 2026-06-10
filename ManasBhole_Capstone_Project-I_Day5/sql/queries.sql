-- ============================================================
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
