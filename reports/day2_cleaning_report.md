# Mutual Fund Analytics - Day 2 Data Cleaning Report
Generated: 2026-06-30 11:12:38

---

## Summary

| Dataset | Final Rows | Final Cols | Key Actions |
|---------|-----------|-----------|-------------|
| nav_history | 46,000 | 5 | date parsed, forward-filled, sorted |
| investor_transactions | 32,778 | 15 | types standardised, amount validated, KYC checked |
| scheme_performance | 40 | 20 | returns validated, expense_ratio checked, alpha_category added |
| fund_master | 40 | 15 | launch_date parsed, deduped |
| aum_by_fund_house | 90 | 5 | date parsed, sorted |
| monthly_sip_inflows | 48 | 7 | month parsed, spike flagged |
| category_inflows | 144 | 3 | whitespace stripped, nulls dropped |
| industry_folio_count | 21 | 6 | month parsed, numerics coerced |
| portfolio_holdings | 322 | 8 | date parsed, weights validated |
| benchmark_indices | 8,050 | 3 | invalid values removed, deduped |

---

## Detailed Cleaning Steps

### nav_history
- Parsed `date` column to datetime, dropped 0 invalid dates
- Removed NAV <= 0 entries
- Deduplicated on (amfi_code, date) -- kept last
- Sorted by amfi_code + date ascending
- Forward-filled missing NAV for all business days (weekends/holidays)
- Added `year` and `month` derived columns

### investor_transactions
- Parsed `transaction_date` to datetime
- Standardised `transaction_type` to title-case (SIP, Lumpsum, Redemption)
- Validated `amount_inr` > 0, dropped 0 invalid rows
- Validated `kyc_status` enum: Verified / Pending / Rejected
- Standardised `gender` to title-case, `city_tier` to upper-case
- Removed exact duplicate rows
- Added `year` and `month` derived columns

### scheme_performance
- Validated all return columns are numeric
- Flagged extreme returns (>100% or <-50%)
- Validated `expense_ratio_pct` in range 0.1% to 2.5%
- Validated `max_drawdown_pct` <= 0
- Validated `morningstar_rating` in [1, 5]
- Added `alpha_category` label column

### Other Datasets
- **fund_master**: Parsed launch_date, validated numeric columns, deduped on amfi_code
- **aum_by_fund_house**: Parsed date, validated AUM > 0, sorted by fund_house + date
- **monthly_sip_inflows**: Parsed month, flagged Apr-2025 spike anomaly
- **category_inflows**: Stripped whitespace, dropped nulls
- **industry_folio_count**: Parsed month, all numerics coerced
- **portfolio_holdings**: Validated weight_pct, market_value_cr > 0
- **benchmark_indices**: Removed close_value <= 0, deduped on date + index_name

---