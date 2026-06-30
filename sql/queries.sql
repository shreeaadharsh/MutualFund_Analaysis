-- ==============================================================================
-- Mutual Fund Analytics - Day 2
-- File: queries.sql
-- Purpose: 10 analytical SQL queries on bluestock_mf.db
-- ==============================================================================


-- ==============================================================================
-- QUERY 1: Top 5 Funds by AUM (latest snapshot)
-- Business question: Which fund houses manage the most money today?
-- ==============================================================================

SELECT
    fund_house,
    SUM(aum_crore)          AS total_aum_crore,
    COUNT(*)                AS num_snapshots,
    ROUND(SUM(aum_crore) / 100000.0, 2) AS aum_lakh_crore
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
GROUP BY fund_house
ORDER BY total_aum_crore DESC
LIMIT 5;


-- ==============================================================================
-- QUERY 2: Average NAV per Month for Top 5 Large Cap Schemes
-- Business question: How did Large Cap NAVs trend month-over-month?
-- ==============================================================================

SELECT
    n.amfi_code,
    f.scheme_name,
    SUBSTR(n.date, 1, 7)        AS month,
    ROUND(AVG(n.nav), 4)        AS avg_nav,
    ROUND(MIN(n.nav), 4)        AS min_nav,
    ROUND(MAX(n.nav), 4)        AS max_nav
FROM fact_nav n
JOIN dim_fund f ON n.amfi_code = f.amfi_code
WHERE f.category = 'Equity'
  AND f.sub_category = 'Large Cap'
  AND f.plan = 'Regular'
GROUP BY n.amfi_code, f.scheme_name, SUBSTR(n.date, 1, 7)
ORDER BY n.amfi_code, month;


-- ==============================================================================
-- QUERY 3: SIP Inflow YoY Growth Trend
-- Business question: How has the SIP industry grown year-over-year?
-- ==============================================================================

SELECT
    SUBSTR(month, 1, 4)              AS year,
    ROUND(SUM(sip_inflow_crore), 0)  AS total_sip_crore,
    ROUND(AVG(sip_inflow_crore), 0)  AS avg_monthly_sip_crore,
    ROUND(AVG(yoy_growth_pct), 2)    AS avg_yoy_growth_pct,
    ROUND(MAX(sip_inflow_crore), 0)  AS peak_month_sip_crore
FROM fact_sip_inflows
GROUP BY year
ORDER BY year;


-- ==============================================================================
-- QUERY 4: Total Transaction Volume by State
-- Business question: Which states contribute most to MF investments?
-- ==============================================================================

SELECT
    state,
    COUNT(*)                          AS num_transactions,
    ROUND(SUM(amount_inr), 0)         AS total_amount_inr,
    ROUND(AVG(amount_inr), 0)         AS avg_amount_inr,
    COUNT(DISTINCT investor_id)       AS unique_investors
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_inr DESC
LIMIT 15;


-- ==============================================================================
-- QUERY 5: Funds with Expense Ratio < 1% (Low-Cost Funds)
-- Business question: Which funds offer the lowest cost to investors?
-- ==============================================================================

SELECT
    p.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    f.plan,
    p.expense_ratio_pct,
    p.return_3yr_pct,
    p.sharpe_ratio,
    p.aum_crore
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
WHERE p.expense_ratio_pct < 1.0
ORDER BY p.expense_ratio_pct ASC;


-- ==============================================================================
-- QUERY 6: Risk-Adjusted Return Leaders (Sharpe Ratio > 1.0)
-- Business question: Which funds give the best return per unit of risk?
-- ==============================================================================

SELECT
    p.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    p.sharpe_ratio,
    p.sortino_ratio,
    p.return_3yr_pct,
    p.alpha,
    p.beta,
    p.max_drawdown_pct,
    p.morningstar_rating
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
WHERE p.sharpe_ratio > 1.0
ORDER BY p.sharpe_ratio DESC;


-- ==============================================================================
-- QUERY 7: SIP vs Lumpsum vs Redemption -- Monthly Transaction Analysis
-- Business question: What is the monthly split of transaction types?
-- ==============================================================================

SELECT
    SUBSTR(transaction_date, 1, 7)   AS month,
    transaction_type,
    COUNT(*)                          AS num_transactions,
    ROUND(SUM(amount_inr), 0)         AS total_amount_inr,
    ROUND(AVG(amount_inr), 0)         AS avg_amount_inr
FROM fact_transactions
GROUP BY month, transaction_type
ORDER BY month, transaction_type;


-- ==============================================================================
-- QUERY 8: Fund Performance vs Benchmark (Alpha Analysis)
-- Business question: Which funds consistently beat their benchmark?
-- ==============================================================================

SELECT
    p.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    p.return_3yr_pct,
    p.benchmark_3yr_pct,
    ROUND(p.return_3yr_pct - p.benchmark_3yr_pct, 2) AS outperformance_pct,
    p.alpha,
    p.alpha_category,
    p.morningstar_rating
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
ORDER BY outperformance_pct DESC;


-- ==============================================================================
-- QUERY 9: Investor Demographics -- City Tier Analysis
-- Business question: How do T30 vs B30 city investors differ?
-- ==============================================================================

SELECT
    city_tier,
    COUNT(*)                           AS num_transactions,
    COUNT(DISTINCT investor_id)        AS unique_investors,
    ROUND(SUM(amount_inr), 0)          AS total_invested_inr,
    ROUND(AVG(amount_inr), 0)          AS avg_transaction_inr,
    ROUND(100.0 * SUM(CASE WHEN transaction_type = 'SIP' THEN 1 ELSE 0 END)
          / COUNT(*), 1)               AS sip_pct,
    ROUND(100.0 * SUM(CASE WHEN kyc_status = 'Verified' THEN 1 ELSE 0 END)
          / COUNT(*), 1)               AS kyc_verified_pct
FROM fact_transactions
GROUP BY city_tier
ORDER BY total_invested_inr DESC;


-- ==============================================================================
-- QUERY 10: AUM Growth Rate by Fund House (2022 to Latest)
-- Business question: Which fund houses grew their AUM the fastest?
-- ==============================================================================

WITH base AS (
    SELECT fund_house, aum_crore AS aum_2022
    FROM fact_aum
    WHERE date = (SELECT MIN(date) FROM fact_aum)
),
latest AS (
    SELECT fund_house, aum_crore AS aum_latest
    FROM fact_aum
    WHERE date = (SELECT MAX(date) FROM fact_aum)
)
SELECT
    l.fund_house,
    ROUND(b.aum_2022 / 100000.0, 2)      AS aum_2022_lakh_crore,
    ROUND(l.aum_latest / 100000.0, 2)    AS aum_latest_lakh_crore,
    ROUND((l.aum_latest - b.aum_2022) / b.aum_2022 * 100, 1) AS growth_pct
FROM latest l
JOIN base b ON l.fund_house = b.fund_house
ORDER BY growth_pct DESC;
