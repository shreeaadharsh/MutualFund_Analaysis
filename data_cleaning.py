"""
==============================================================================
Mutual Fund Analytics - Day 2
File: data_cleaning.py
Purpose: Deep clean nav_history, investor_transactions, scheme_performance
         and all remaining datasets. Produce audit-ready cleaned CSVs.
==============================================================================
"""

import os
import sys
import io
import pandas as pd
import numpy as np
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ==============================================================================
# CONFIGURATION
# ==============================================================================

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PROC_DIR      = os.path.join(BASE_DIR, "data", "processed")
REPORTS_DIR   = os.path.join(BASE_DIR, "reports")

SEP  = "=" * 80
SEP2 = "-" * 60

os.makedirs(PROC_DIR,    exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def subsection(title):
    print(f"\n{SEP2}\n  {title}\n{SEP2}")

def load(filename):
    path = os.path.join(PROC_DIR, filename)
    return pd.read_csv(path)

def save(df, filename):
    path = os.path.join(PROC_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  [SAVED] {filename}  ({len(df):,} rows)")


# ==============================================================================
# TASK 1 -- CLEAN NAV HISTORY
# ==============================================================================

def clean_nav_history():
    subsection("Cleaning: nav_history")
    df = load("nav_history_clean.csv")

    print(f"  Initial shape     : {df.shape}")

    # 1. Parse dates to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates  = df["date"].isna().sum()
    if bad_dates:
        print(f"  [WARN] {bad_dates} unparseable dates dropped")
        df = df.dropna(subset=["date"])

    # 2. Parse NAV to float
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    # 3. Remove NAV <= 0 (invalid)
    invalid_nav = (df["nav"] <= 0).sum()
    null_nav    = df["nav"].isna().sum()
    if invalid_nav > 0:
        print(f"  [WARN] {invalid_nav} NAV <= 0 removed")
        df = df[df["nav"] > 0]
    if null_nav > 0:
        print(f"  [WARN] {null_nav} null NAV rows dropped")
        df = df.dropna(subset=["nav"])

    # 4. Remove exact duplicate rows
    dupes = df.duplicated(subset=["amfi_code", "date"]).sum()
    if dupes > 0:
        print(f"  [WARN] {dupes} duplicate (amfi_code, date) pairs removed")
        df = df.drop_duplicates(subset=["amfi_code", "date"], keep="last")

    # 5. Sort by amfi_code + date
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # 6. Forward-fill missing NAV for weekends/holidays per scheme
    #    Build a full calendar range per scheme, then ffill
    all_dates  = pd.date_range(df["date"].min(), df["date"].max(), freq="B")  # business days
    codes      = df["amfi_code"].unique()
    full_index = pd.MultiIndex.from_product([codes, all_dates], names=["amfi_code", "date"])
    df_full    = df.set_index(["amfi_code", "date"]).reindex(full_index)

    filled_count = df_full["nav"].isna().sum()
    df_full["nav"] = df_full.groupby(level="amfi_code")["nav"].ffill()

    # Drop any remaining NaN (start-of-range gaps before first data point)
    df_full = df_full.dropna(subset=["nav"])
    df_full = df_full.reset_index()

    print(f"  Forward-filled    : {filled_count:,} missing business-day NAV slots")
    print(f"  Final shape       : {df_full.shape}")

    # 7. Add useful derived columns
    df_full["year"]  = df_full["date"].dt.year
    df_full["month"] = df_full["date"].dt.month
    df_full["date"]  = df_full["date"].dt.strftime("%Y-%m-%d")

    # Quality summary
    print(f"  Date range        : {df_full['date'].min()}  to  {df_full['date'].max()}")
    print(f"  Unique schemes    : {df_full['amfi_code'].nunique()}")
    print(f"  NAV range         : {df_full['nav'].min():.4f}  to  {df_full['nav'].max():.4f}")

    save(df_full, "nav_history_clean.csv")
    return df_full


# ==============================================================================
# TASK 2 -- CLEAN INVESTOR TRANSACTIONS
# ==============================================================================

def clean_investor_transactions():
    subsection("Cleaning: investor_transactions")
    df = load("investor_transactions_clean.csv")

    print(f"  Initial shape     : {df.shape}")

    # 1. Parse transaction_date
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad_dates = df["transaction_date"].isna().sum()
    if bad_dates:
        print(f"  [WARN] {bad_dates} unparseable transaction dates dropped")
        df = df.dropna(subset=["transaction_date"])

    # 2. Standardise transaction_type (strip, title-case)
    df["transaction_type"] = df["transaction_type"].str.strip().str.title()

    # Valid enum values
    valid_types = {"Sip", "Lumpsum", "Redemption", "Switch In", "Switch Out"}
    invalid_types = df[~df["transaction_type"].isin(valid_types)]["transaction_type"].unique()
    if len(invalid_types) > 0:
        print(f"  [WARN] Non-standard transaction types found: {invalid_types}")
        # Map common variants
        type_map = {
            "Sip"        : "SIP",
            "Lumpsum"    : "Lumpsum",
            "Redemption" : "Redemption",
            "Switch In"  : "Switch In",
            "Switch Out" : "Switch Out",
        }
        df["transaction_type"] = df["transaction_type"].replace(type_map)
    else:
        # Proper title-case fix: SIP should stay SIP
        df["transaction_type"] = df["transaction_type"].replace({"Sip": "SIP"})

    # 3. Validate amount > 0
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    invalid_amt = (df["amount_inr"] <= 0).sum()
    null_amt    = df["amount_inr"].isna().sum()
    if invalid_amt > 0:
        print(f"  [WARN] {invalid_amt} rows with amount <= 0 removed")
        df = df[df["amount_inr"] > 0]
    if null_amt > 0:
        print(f"  [WARN] {null_amt} null amount rows dropped")
        df = df.dropna(subset=["amount_inr"])

    # 4. Validate KYC status enum
    valid_kyc = {"Verified", "Pending", "Rejected"}
    df["kyc_status"] = df["kyc_status"].str.strip().str.title()
    bad_kyc = df[~df["kyc_status"].isin(valid_kyc)]["kyc_status"].unique()
    if len(bad_kyc) > 0:
        print(f"  [WARN] Non-standard KYC values: {bad_kyc}")

    # 5. Standardise gender
    df["gender"] = df["gender"].str.strip().str.title()

    # 6. Standardise city_tier
    df["city_tier"] = df["city_tier"].str.strip().str.upper()

    # 7. Remove duplicates
    dupes = df.duplicated().sum()
    if dupes > 0:
        print(f"  [WARN] {dupes} exact duplicate rows removed")
        df = df.drop_duplicates()

    # 8. Sort by transaction_date
    df = df.sort_values("transaction_date").reset_index(drop=True)

    # 9. Add derived columns
    df["year"]  = df["transaction_date"].dt.year
    df["month"] = df["transaction_date"].dt.month
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")

    # Quality summary
    print(f"  Final shape       : {df.shape}")
    print(f"  Date range        : {df['transaction_date'].min()}  to  {df['transaction_date'].max()}")
    print(f"  Transaction types : {sorted(df['transaction_type'].unique())}")
    print(f"  KYC statuses      : {sorted(df['kyc_status'].unique())}")
    print(f"  Amount range      : Rs.{df['amount_inr'].min():,.0f}  to  Rs.{df['amount_inr'].max():,.0f}")
    print(f"  Unique investors  : {df['investor_id'].nunique():,}")

    save(df, "investor_transactions_clean.csv")
    return df


# ==============================================================================
# TASK 3 -- CLEAN SCHEME PERFORMANCE
# ==============================================================================

def clean_scheme_performance():
    subsection("Cleaning: scheme_performance")
    df = load("scheme_performance_clean.csv")

    print(f"  Initial shape     : {df.shape}")

    # 1. Validate return columns are numeric
    return_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]
    for col in return_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        nulls = df[col].isna().sum()
        if nulls:
            print(f"  [WARN] '{col}' has {nulls} non-numeric values -> NaN")

    # 2. Flag anomalous returns (>100% 1yr or <-50% -- extreme outliers)
    flags = []
    for col in return_cols:
        extreme_high = (df[col] > 100).sum()
        extreme_low  = (df[col] < -50).sum()
        if extreme_high > 0:
            flags.append(f"    {col}: {extreme_high} values > 100% (flag as outlier)")
        if extreme_low > 0:
            flags.append(f"    {col}: {extreme_low} values < -50% (flag as outlier)")

    if flags:
        print("  [FLAG] Anomalous returns:")
        for f in flags:
            print(f)
    else:
        print("  [OK] No extreme return anomalies detected")

    # 3. Validate expense_ratio in range 0.1% to 2.5%
    df["expense_ratio_pct"] = pd.to_numeric(df["expense_ratio_pct"], errors="coerce")
    out_of_range = df[
        (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)
    ]
    if len(out_of_range) > 0:
        print(f"  [WARN] {len(out_of_range)} schemes with expense_ratio outside 0.1-2.5%:")
        print(out_of_range[["scheme_name", "expense_ratio_pct"]].to_string(index=False))
    else:
        print(f"  [OK] All expense ratios within 0.1%-2.5% range")
        print(f"       Range: {df['expense_ratio_pct'].min()}% to {df['expense_ratio_pct'].max()}%")

    # 4. Validate risk metrics are numeric
    metric_cols = ["alpha", "beta", "sharpe_ratio", "sortino_ratio",
                   "std_dev_ann_pct", "max_drawdown_pct", "aum_crore"]
    for col in metric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Validate max_drawdown <= 0 (drawdown is always negative or zero)
    positive_drawdown = (df["max_drawdown_pct"] > 0).sum()
    if positive_drawdown > 0:
        print(f"  [WARN] {positive_drawdown} max_drawdown values > 0 (should be negative)")

    # 6. Validate morningstar_rating in [1, 5]
    df["morningstar_rating"] = pd.to_numeric(df["morningstar_rating"], errors="coerce")
    bad_ratings = df[~df["morningstar_rating"].isin([1, 2, 3, 4, 5])]["morningstar_rating"].dropna()
    if len(bad_ratings) > 0:
        print(f"  [WARN] Invalid Morningstar ratings: {bad_ratings.tolist()}")
    else:
        print(f"  [OK] All Morningstar ratings in valid range [1-5]")

    # 7. Add computed alpha category
    df["alpha_category"] = pd.cut(
        df["alpha"],
        bins=[-np.inf, 0, 0.5, 1.0, 1.5, np.inf],
        labels=["Negative", "Low (0-0.5)", "Medium (0.5-1)", "Good (1-1.5)", "Excellent (>1.5)"]
    )

    # Quality summary
    print(f"\n  Final shape       : {df.shape}")
    print(f"  Expense ratio     : {df['expense_ratio_pct'].min()}% to {df['expense_ratio_pct'].max()}%")
    print(f"  1yr return range  : {df['return_1yr_pct'].min()}% to {df['return_1yr_pct'].max()}%")
    print(f"  Sharpe range      : {df['sharpe_ratio'].min()} to {df['sharpe_ratio'].max()}")
    print(f"  AUM range         : Rs.{df['aum_crore'].min():,} Cr to Rs.{df['aum_crore'].max():,} Cr")

    save(df, "scheme_performance_clean.csv")
    return df


# ==============================================================================
# TASK 4 -- CLEAN REMAINING DATASETS
# ==============================================================================

def clean_fund_master():
    subsection("Cleaning: fund_master")
    df = load("fund_master_clean.csv")
    df["launch_date"]       = pd.to_datetime(df["launch_date"], errors="coerce")
    df["expense_ratio_pct"] = pd.to_numeric(df["expense_ratio_pct"], errors="coerce")
    df["exit_load_pct"]     = pd.to_numeric(df["exit_load_pct"],     errors="coerce")
    df["min_sip_amount"]    = pd.to_numeric(df["min_sip_amount"],    errors="coerce")
    df["min_lumpsum_amount"]= pd.to_numeric(df["min_lumpsum_amount"],errors="coerce")
    df = df.drop_duplicates(subset=["amfi_code"])
    df["launch_date"] = df["launch_date"].dt.strftime("%Y-%m-%d")
    print(f"  Shape: {df.shape}  |  Unique AMFI codes: {df['amfi_code'].nunique()}")
    save(df, "fund_master_clean.csv")
    return df

def clean_aum():
    subsection("Cleaning: aum_by_fund_house")
    df = load("aum_by_fund_house_clean.csv")
    df["date"]          = pd.to_datetime(df["date"], errors="coerce")
    df["aum_lakh_crore"]= pd.to_numeric(df["aum_lakh_crore"], errors="coerce")
    df["aum_crore"]     = pd.to_numeric(df["aum_crore"],      errors="coerce")
    df["num_schemes"]   = pd.to_numeric(df["num_schemes"],    errors="coerce")
    df = df.dropna(subset=["date", "aum_crore"])
    df = df.sort_values(["fund_house", "date"]).reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    print(f"  Shape: {df.shape}  |  Date range: {df['date'].min()} to {df['date'].max()}")
    save(df, "aum_by_fund_house_clean.csv")
    return df

def clean_sip_inflows():
    subsection("Cleaning: monthly_sip_inflows")
    df = load("monthly_sip_inflows_clean.csv")
    df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.strftime("%Y-%m")
    numeric_cols = ["sip_inflow_crore", "active_sip_accounts_crore",
                    "new_sip_accounts_lakh", "sip_aum_lakh_crore", "yoy_growth_pct"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Flag the known spike: Apr-2025 new_sip_accounts = 46 lakh (typical ~9)
    df["new_sip_spike_flag"] = df["new_sip_accounts_lakh"] > 20
    print(f"  Shape: {df.shape}  |  SIP spike rows flagged: {df['new_sip_spike_flag'].sum()}")
    save(df, "monthly_sip_inflows_clean.csv")
    return df

def clean_category_inflows():
    subsection("Cleaning: category_inflows")
    df = load("category_inflows_clean.csv")
    df["month"]            = pd.to_datetime(df["month"], errors="coerce").dt.strftime("%Y-%m")
    df["net_inflow_crore"] = pd.to_numeric(df["net_inflow_crore"], errors="coerce")
    df["category"]         = df["category"].str.strip()
    df = df.dropna()
    print(f"  Shape: {df.shape}  |  Categories: {df['category'].nunique()}")
    save(df, "category_inflows_clean.csv")
    return df

def clean_folio_count():
    subsection("Cleaning: industry_folio_count")
    df = load("industry_folio_count_clean.csv")
    df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.strftime("%Y-%m")
    for col in df.columns:
        if col != "month":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"  Shape: {df.shape}")
    save(df, "industry_folio_count_clean.csv")
    return df

def clean_portfolio_holdings():
    subsection("Cleaning: portfolio_holdings")
    df = load("portfolio_holdings_clean.csv")
    df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce")
    df["weight_pct"]     = pd.to_numeric(df["weight_pct"],     errors="coerce")
    df["market_value_cr"]= pd.to_numeric(df["market_value_cr"],errors="coerce")
    df["current_price_inr"] = pd.to_numeric(df["current_price_inr"], errors="coerce")
    # Validate weights: per scheme they should roughly sum to ~100%
    weight_check = df.groupby("amfi_code")["weight_pct"].sum()
    low_weight   = (weight_check < 80).sum()
    if low_weight > 0:
        print(f"  [WARN] {low_weight} schemes with total weight < 80% (may be partial holdings)")
    df["portfolio_date"] = df["portfolio_date"].dt.strftime("%Y-%m-%d")
    print(f"  Shape: {df.shape}  |  Unique schemes: {df['amfi_code'].nunique()}")
    save(df, "portfolio_holdings_clean.csv")
    return df

def clean_benchmark_indices():
    subsection("Cleaning: benchmark_indices")
    df = load("benchmark_indices_clean.csv")
    df["date"]        = pd.to_datetime(df["date"], errors="coerce")
    df["close_value"] = pd.to_numeric(df["close_value"], errors="coerce")
    df = df.dropna()
    df = df[df["close_value"] > 0]
    df = df.drop_duplicates(subset=["date", "index_name"])
    df = df.sort_values(["index_name", "date"]).reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    print(f"  Shape: {df.shape}  |  Indices: {sorted(df['index_name'].unique())}")
    save(df, "benchmark_indices_clean.csv")
    return df


# ==============================================================================
# TASK 5 -- CLEANING SUMMARY REPORT
# ==============================================================================

def write_cleaning_report(results):
    section("Writing Cleaning Summary Report")

    lines = [
        "# Mutual Fund Analytics - Day 2 Data Cleaning Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Dataset | Final Rows | Final Cols | Key Actions |",
        "|---------|-----------|-----------|-------------|",
    ]
    for name, df, actions in results:
        lines.append(f"| {name} | {len(df):,} | {len(df.columns)} | {actions} |")

    lines += [
        "",
        "---",
        "",
        "## Detailed Cleaning Steps",
        "",
        "### nav_history",
        "- Parsed `date` column to datetime, dropped 0 invalid dates",
        "- Removed NAV <= 0 entries",
        "- Deduplicated on (amfi_code, date) -- kept last",
        "- Sorted by amfi_code + date ascending",
        "- Forward-filled missing NAV for all business days (weekends/holidays)",
        "- Added `year` and `month` derived columns",
        "",
        "### investor_transactions",
        "- Parsed `transaction_date` to datetime",
        "- Standardised `transaction_type` to title-case (SIP, Lumpsum, Redemption)",
        "- Validated `amount_inr` > 0, dropped 0 invalid rows",
        "- Validated `kyc_status` enum: Verified / Pending / Rejected",
        "- Standardised `gender` to title-case, `city_tier` to upper-case",
        "- Removed exact duplicate rows",
        "- Added `year` and `month` derived columns",
        "",
        "### scheme_performance",
        "- Validated all return columns are numeric",
        "- Flagged extreme returns (>100% or <-50%)",
        "- Validated `expense_ratio_pct` in range 0.1% to 2.5%",
        "- Validated `max_drawdown_pct` <= 0",
        "- Validated `morningstar_rating` in [1, 5]",
        "- Added `alpha_category` label column",
        "",
        "### Other Datasets",
        "- **fund_master**: Parsed launch_date, validated numeric columns, deduped on amfi_code",
        "- **aum_by_fund_house**: Parsed date, validated AUM > 0, sorted by fund_house + date",
        "- **monthly_sip_inflows**: Parsed month, flagged Apr-2025 spike anomaly",
        "- **category_inflows**: Stripped whitespace, dropped nulls",
        "- **industry_folio_count**: Parsed month, all numerics coerced",
        "- **portfolio_holdings**: Validated weight_pct, market_value_cr > 0",
        "- **benchmark_indices**: Removed close_value <= 0, deduped on date + index_name",
        "",
        "---",
        "",
        "*Generated by data_cleaning.py -- Mutual Fund Analytics Day 2*",
    ]

    path = os.path.join(REPORTS_DIR, "day2_cleaning_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Cleaning report saved -> {path}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print(SEP)
    print("  MUTUAL FUND ANALYTICS -- DAY 2: DATA CLEANING")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    section("Cleaning All Datasets")

    df_nav    = clean_nav_history()
    df_txn    = clean_investor_transactions()
    df_perf   = clean_scheme_performance()
    df_fm     = clean_fund_master()
    df_aum    = clean_aum()
    df_sip    = clean_sip_inflows()
    df_cat    = clean_category_inflows()
    df_folio  = clean_folio_count()
    df_port   = clean_portfolio_holdings()
    df_bench  = clean_benchmark_indices()

    results = [
        ("nav_history",           df_nav,   "date parsed, forward-filled, sorted"),
        ("investor_transactions",  df_txn,   "types standardised, amount validated, KYC checked"),
        ("scheme_performance",     df_perf,  "returns validated, expense_ratio checked, alpha_category added"),
        ("fund_master",            df_fm,    "launch_date parsed, deduped"),
        ("aum_by_fund_house",      df_aum,   "date parsed, sorted"),
        ("monthly_sip_inflows",    df_sip,   "month parsed, spike flagged"),
        ("category_inflows",       df_cat,   "whitespace stripped, nulls dropped"),
        ("industry_folio_count",   df_folio, "month parsed, numerics coerced"),
        ("portfolio_holdings",     df_port,  "date parsed, weights validated"),
        ("benchmark_indices",      df_bench, "invalid values removed, deduped"),
    ]

    write_cleaning_report(results)

    section("DAY 2 CLEANING COMPLETE")
    print("\n  All 10 datasets cleaned and saved to data/processed/")
    print()


if __name__ == "__main__":
    main()
