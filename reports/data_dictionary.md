# Mutual Fund Analytics - Data Dictionary

**Project:** Mutual Fund Analytics  
**Day:** 2 - Data Cleaning + SQL Database Design  
**Database:** bluestock_mf.db (SQLite)  
**Last Updated:** 2026-06-30  

---

## Table of Contents

1. [dim_fund](#1-dim_fund)
2. [dim_date](#2-dim_date)
3. [dim_investor](#3-dim_investor)
4. [fact_nav](#4-fact_nav)
5. [fact_transactions](#5-fact_transactions)
6. [fact_performance](#6-fact_performance)
7. [fact_aum](#7-fact_aum)
8. [fact_sip_inflows](#8-fact_sip_inflows)
9. [fact_category_inflows](#9-fact_category_inflows)
10. [fact_portfolio_holdings](#10-fact_portfolio_holdings)
11. [fact_benchmark](#11-fact_benchmark)
12. [fact_folio_count](#12-fact_folio_count)

---

## Schema Overview

```
Star Schema Design
==================
DIMENSIONS          FACTS
----------          -----
dim_fund       -->  fact_nav
dim_fund       -->  fact_transactions
dim_fund       -->  fact_performance
dim_date       -->  fact_nav (via date join)
dim_investor   -->  fact_transactions
               -->  fact_aum
               -->  fact_sip_inflows
               -->  fact_category_inflows
               -->  fact_portfolio_holdings
               -->  fact_benchmark
               -->  fact_folio_count
```

---

## 1. dim_fund

**Source:** `01_fund_master.csv`  
**Description:** Master dimension table for all registered mutual fund schemes. One row per AMFI scheme code.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `amfi_code` | INTEGER | No | PRIMARY KEY | Unique 6-digit AMFI scheme identifier assigned by AMFI India |
| `fund_house` | TEXT | No | NOT NULL | Name of the Asset Management Company (AMC) e.g. SBI Mutual Fund |
| `scheme_name` | TEXT | No | NOT NULL | Full official scheme name as registered with SEBI |
| `category` | TEXT | No | NOT NULL | Broad asset class: Equity / Debt |
| `sub_category` | TEXT | No | NOT NULL | SEBI-defined sub-category: Large Cap, Mid Cap, Small Cap, Gilt, Liquid, etc. |
| `plan` | TEXT | No | NOT NULL | Direct (no distributor commission) or Regular (sold via distributor) |
| `launch_date` | TEXT | Yes | YYYY-MM-DD | Date scheme was launched and NAV started |
| `benchmark` | TEXT | Yes | | Index used to measure scheme performance e.g. NIFTY 100 TRI |
| `expense_ratio_pct` | REAL | No | 0.0 to 3.0 | Annual % of AUM charged as management fee (SEBI cap: 2.25% equity, 2.0% debt) |
| `exit_load_pct` | REAL | Yes | Default 0.0 | % charged on redemption within lock-in period |
| `min_sip_amount` | REAL | Yes | | Minimum monthly SIP amount in INR |
| `min_lumpsum_amount` | REAL | Yes | | Minimum one-time investment amount in INR |
| `fund_manager` | TEXT | Yes | | Name of the portfolio manager responsible for investment decisions |
| `risk_category` | TEXT | Yes | | SEBI risk-o-meter category: Low / Moderate / Moderately High / High / Very High |
| `sebi_category_code` | TEXT | Yes | | SEBI internal classification code e.g. EC01, DC02 |

**Key Facts:**
- 40 schemes across 10 fund houses
- All AMFI codes are 6-digit numeric identifiers
- Direct plans have ~0.55x the expense ratio of Regular plans

---

## 2. dim_date

**Source:** Generated (2022-01-01 to 2026-12-31)  
**Description:** Complete date dimension for time-series slicing and dicing.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `date_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `full_date` | TEXT | No | UNIQUE, YYYY-MM-DD | Calendar date |
| `year` | INTEGER | No | | Calendar year (2022-2026) |
| `quarter` | INTEGER | No | 1-4 | Calendar quarter |
| `month` | INTEGER | No | 1-12 | Calendar month number |
| `month_name` | TEXT | No | | Full month name e.g. January |
| `week_of_year` | INTEGER | No | 1-53 | ISO week number |
| `day_of_week` | INTEGER | No | 0=Monday, 6=Sunday | Day index within week |
| `day_name` | TEXT | No | | Full day name e.g. Monday |
| `is_month_end` | INTEGER | No | 0 or 1 | Flag: 1 if last day of calendar month |
| `is_quarter_end` | INTEGER | No | 0 or 1 | Flag: 1 if last day of March/June/September/December |

---

## 3. dim_investor

**Source:** `08_investor_transactions.csv` (derived — unique investor profiles)  
**Description:** Unique investor dimension with demographic profile. Built by aggregating first-seen values per investor_id.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `investor_id` | TEXT | No | PRIMARY KEY | Unique investor identifier e.g. INV003054 |
| `age_group` | TEXT | Yes | | Age bracket: 18-25 / 26-35 / 36-45 / 46-55 / 56+ |
| `gender` | TEXT | Yes | | Male / Female |
| `state` | TEXT | Yes | | Indian state of residence |
| `city` | TEXT | Yes | | City name |
| `city_tier` | TEXT | Yes | | T30 (Top 30 cities) or B30 (Beyond Top 30) per AMFI classification |
| `annual_income_lakh` | REAL | Yes | | Self-reported annual income in lakhs INR |
| `kyc_status` | TEXT | Yes | Verified / Pending / Rejected | Know Your Customer verification status |

---

## 4. fact_nav

**Source:** `02_nav_history.csv`  
**Description:** Daily Net Asset Value for each scheme. Forward-filled for business days where market is closed (weekends/holidays).

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `nav_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `amfi_code` | INTEGER | No | FK -> dim_fund | AMFI scheme identifier |
| `date` | TEXT | No | UNIQUE with amfi_code, YYYY-MM-DD | Trading/valuation date |
| `nav` | REAL | No | > 0 | Net Asset Value per unit in INR on that date |
| `year` | INTEGER | Yes | | Derived: calendar year |
| `month` | INTEGER | Yes | | Derived: calendar month |

**Notes:**
- Date range: 2022-01-03 to 2026-05-29 (source data), extended to 2026-06-29 (live API)
- 1,150 records per scheme in source data
- After forward-fill for all business days: ~1,200+ records per scheme
- NAV is calculated daily after market close by the AMC

---

## 5. fact_transactions

**Source:** `08_investor_transactions.csv`  
**Description:** Individual investor transaction records. Each row is one transaction event.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `txn_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `investor_id` | TEXT | No | FK -> dim_investor | Investor identifier |
| `transaction_date` | TEXT | No | YYYY-MM-DD | Date of transaction execution |
| `amfi_code` | INTEGER | No | FK -> dim_fund | Scheme invested in |
| `transaction_type` | TEXT | No | SIP / Lumpsum / Redemption / Switch In / Switch Out | Nature of transaction |
| `amount_inr` | REAL | No | > 0 | Transaction value in Indian Rupees |
| `state` | TEXT | Yes | | Investor state at time of transaction |
| `city` | TEXT | Yes | | Investor city |
| `city_tier` | TEXT | Yes | T30 / B30 | City tier per AMFI classification |
| `age_group` | TEXT | Yes | | Investor age bracket |
| `gender` | TEXT | Yes | Male / Female | Investor gender |
| `annual_income_lakh` | REAL | Yes | | Annual income in lakhs INR |
| `payment_mode` | TEXT | Yes | | Payment method: UPI / Mandate / Net Banking / Cheque |
| `kyc_status` | TEXT | Yes | Verified / Pending / Rejected | KYC status at transaction time |
| `year` | INTEGER | Yes | | Derived: transaction year |
| `month` | INTEGER | Yes | | Derived: transaction month |

**Notes:**
- 32,778 transactions from 2024-01-01 to 2025-12-31
- SIP is the dominant transaction type
- All amounts validated > 0 during cleaning

---

## 6. fact_performance

**Source:** `07_scheme_performance.csv`  
**Description:** Snapshot of risk-return metrics per scheme. One row per scheme (point-in-time).

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `perf_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `amfi_code` | INTEGER | No | FK -> dim_fund, UNIQUE | Scheme identifier |
| `scheme_name` | TEXT | No | | Scheme name |
| `fund_house` | TEXT | No | | AMC name |
| `category` | TEXT | Yes | | Equity / Debt |
| `plan` | TEXT | Yes | | Direct / Regular |
| `return_1yr_pct` | REAL | Yes | | Absolute return over trailing 1 year (%) |
| `return_3yr_pct` | REAL | Yes | | CAGR over trailing 3 years (%) |
| `return_5yr_pct` | REAL | Yes | | CAGR over trailing 5 years (%) |
| `benchmark_3yr_pct` | REAL | Yes | | Benchmark CAGR over trailing 3 years (%) |
| `alpha` | REAL | Yes | | Jensen's Alpha: excess return vs benchmark risk-adjusted |
| `beta` | REAL | Yes | | Sensitivity to market movements (1.0 = market neutral) |
| `sharpe_ratio` | REAL | Yes | | Return per unit of total risk (higher is better) |
| `sortino_ratio` | REAL | Yes | | Return per unit of downside risk (higher is better) |
| `std_dev_ann_pct` | REAL | Yes | | Annualised standard deviation of returns (%) |
| `max_drawdown_pct` | REAL | Yes | <= 0 | Maximum peak-to-trough decline (%) — always negative |
| `aum_crore` | REAL | Yes | > 0 | Assets Under Management in crore INR |
| `expense_ratio_pct` | REAL | Yes | 0.1 to 2.5 | Annual management fee (%) |
| `morningstar_rating` | INTEGER | Yes | 1 to 5 | Morningstar star rating (5 = best) |
| `risk_grade` | TEXT | Yes | | Risk classification: Low / Moderate / High / Very High |
| `alpha_category` | TEXT | Yes | | Derived label: Negative / Low / Medium / Good / Excellent |

---

## 7. fact_aum

**Source:** `03_aum_by_fund_house.csv`  
**Description:** Bi-annual AUM snapshot per fund house. Used for market share and growth analysis.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `aum_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `date` | TEXT | No | UNIQUE with fund_house | Snapshot date (typically March/September year-end) |
| `fund_house` | TEXT | No | | AMC name |
| `aum_lakh_crore` | REAL | Yes | | AUM in lakh crore INR (1 lakh crore = 1 trillion INR) |
| `aum_crore` | REAL | No | > 0 | AUM in crore INR |
| `num_schemes` | INTEGER | Yes | | Total number of active schemes at snapshot date |

---

## 8. fact_sip_inflows

**Source:** `04_monthly_sip_inflows.csv`  
**Description:** Industry-wide monthly SIP statistics. Published by AMFI.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `sip_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `month` | TEXT | No | UNIQUE, YYYY-MM | Reference month |
| `sip_inflow_crore` | REAL | No | | Total SIP collections in crore INR for the month |
| `active_sip_accounts_crore` | REAL | Yes | | Number of active SIP mandates in crore |
| `new_sip_accounts_lakh` | REAL | Yes | | New SIP registrations in lakh |
| `sip_aum_lakh_crore` | REAL | Yes | | Total SIP AUM in lakh crore INR |
| `yoy_growth_pct` | REAL | Yes | NULL for 2022 | Year-over-year growth % vs same month prior year |
| `new_sip_spike_flag` | INTEGER | Yes | 0 or 1 | Flag: 1 if new_sip_accounts_lakh > 20 (anomaly marker) |

**Data Quality Note:** `yoy_growth_pct` is NULL for Jan-Dec 2022 (first year of data — no prior year for comparison). April 2025 shows `new_sip_accounts_lakh = 46.0` vs typical ~9 — flagged as anomaly.

---

## 9. fact_category_inflows

**Source:** `05_category_inflows.csv`  
**Description:** Monthly net inflows broken down by SEBI fund category.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `cat_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `month` | TEXT | No | UNIQUE with category, YYYY-MM | Reference month |
| `category` | TEXT | No | | Fund category: Large Cap / Mid Cap / Small Cap / Flexi Cap / Liquid / Gilt etc. |
| `net_inflow_crore` | REAL | No | | Net inflow (purchases minus redemptions) in crore INR |

---

## 10. fact_portfolio_holdings

**Source:** `09_portfolio_holdings.csv`  
**Description:** Stock-level holdings for each mutual fund scheme as of portfolio date.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `holding_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `amfi_code` | INTEGER | No | FK -> dim_fund | Scheme identifier |
| `stock_symbol` | TEXT | No | | NSE/BSE ticker symbol e.g. HDFCBANK |
| `stock_name` | TEXT | Yes | | Full company name |
| `sector` | TEXT | Yes | | GICS sector: Banking / IT / Pharma / Automobile etc. |
| `weight_pct` | REAL | Yes | 0 to 100 | % of portfolio allocated to this stock |
| `market_value_cr` | REAL | Yes | | Market value of holding in crore INR |
| `current_price_inr` | REAL | Yes | | Stock price in INR at portfolio date |
| `portfolio_date` | TEXT | Yes | YYYY-MM-DD | Date of portfolio disclosure |

---

## 11. fact_benchmark

**Source:** `10_benchmark_indices.csv`  
**Description:** Daily closing values for market benchmark indices.

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `bench_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `date` | TEXT | No | UNIQUE with index_name, YYYY-MM-DD | Trading date |
| `index_name` | TEXT | No | | Index identifier: NIFTY50 / NIFTY100 / NIFTYMIDCAP150 / BSE500 etc. |
| `close_value` | REAL | No | > 0 | Index closing level on that date |

---

## 12. fact_folio_count

**Source:** `06_industry_folio_count.csv`  
**Description:** Quarterly industry folio count (a folio = one investor account in one scheme).

| Column | Data Type | Nullable | Constraints | Business Definition |
|--------|-----------|----------|-------------|---------------------|
| `folio_id` | INTEGER | No | PRIMARY KEY AUTOINCREMENT | Surrogate key |
| `month` | TEXT | No | UNIQUE, YYYY-MM | Reference month (quarterly cadence) |
| `total_folios_crore` | REAL | Yes | | Total industry folios in crore |
| `equity_folios_crore` | REAL | Yes | | Equity scheme folios in crore |
| `debt_folios_crore` | REAL | Yes | | Debt scheme folios in crore |
| `hybrid_folios_crore` | REAL | Yes | | Hybrid scheme folios in crore |
| `others_folios_crore` | REAL | Yes | | Other category folios in crore |

---

## Glossary

| Term | Definition |
|------|-----------|
| **AMFI** | Association of Mutual Funds in India — industry body that regulates and publishes MF data |
| **NAV** | Net Asset Value — price per unit of a mutual fund scheme, calculated daily |
| **AUM** | Assets Under Management — total market value of funds managed by an AMC |
| **SIP** | Systematic Investment Plan — fixed periodic investment in a fund |
| **SEBI** | Securities and Exchange Board of India — regulator for mutual funds |
| **TER** | Total Expense Ratio — annual fee charged by the fund (same as expense_ratio_pct) |
| **Alpha** | Excess return of a fund over its benchmark on a risk-adjusted basis |
| **Beta** | Measure of a fund's sensitivity to market movements (beta=1 means market-neutral) |
| **Sharpe Ratio** | Return per unit of total volatility (std deviation) — higher is better |
| **Sortino Ratio** | Return per unit of downside volatility only — higher is better |
| **Max Drawdown** | Largest peak-to-trough decline in fund value — always negative |
| **T30** | Top 30 cities by MF investment volume per AMFI definition |
| **B30** | Beyond Top 30 — all other cities, often target of financial inclusion initiatives |
| **KYC** | Know Your Customer — regulatory identity verification requirement for all MF investors |
| **CAGR** | Compound Annual Growth Rate — annualised return over a multi-year period |
| **Direct Plan** | Fund plan with no distributor — lower expense ratio, higher returns |
| **Regular Plan** | Fund plan sold via distributor — higher expense ratio due to commission |

---

*Data Dictionary generated for Mutual Fund Analytics Project — Day 2*  
*Source: AMFI India public data + mfapi.in live API*
