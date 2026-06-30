"""
==============================================================================
Mutual Fund Analytics - Day 2
File: db_setup.py
Purpose: Build bluestock_mf.db SQLite database using star schema,
         load all cleaned datasets via SQLAlchemy, verify row counts,
         run all 10 analytical queries and export results.
==============================================================================
"""

import os
import sys
import io
import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ==============================================================================
# CONFIGURATION
# ==============================================================================

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROC_DIR    = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR     = os.path.join(BASE_DIR, "sql")
DB_PATH     = os.path.join(BASE_DIR, "bluestock_mf.db")
ENGINE_URL  = f"sqlite:///{DB_PATH}"

SEP  = "=" * 80
SEP2 = "-" * 60


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def subsection(title):
    print(f"\n{SEP2}\n  {title}\n{SEP2}")

def load_csv(filename):
    return pd.read_csv(os.path.join(PROC_DIR, filename))


# ==============================================================================
# TASK 1 -- CREATE SCHEMA
# ==============================================================================

def create_schema(engine):
    section("TASK 1 -- Creating Star Schema")

    schema_path = os.path.join(SQL_DIR, "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Use native sqlite3 executescript for reliable multi-statement DDL execution
    raw_conn = engine.raw_connection()
    try:
        raw_conn.executescript(sql_script)
        raw_conn.commit()
    finally:
        raw_conn.close()

    print("  [OK] Schema created successfully")
    print("  Tables: dim_fund, dim_date, dim_investor,")
    print("          fact_nav, fact_transactions, fact_performance,")
    print("          fact_aum, fact_sip_inflows, fact_category_inflows,")
    print("          fact_portfolio_holdings, fact_benchmark, fact_folio_count")


# ==============================================================================
# TASK 2 -- POPULATE dim_date
# ==============================================================================

def populate_dim_date(engine):
    subsection("Populating dim_date")

    all_dates = pd.date_range("2022-01-01", "2026-12-31", freq="D")
    month_names = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]
    day_names   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    records = []
    for d in all_dates:
        is_month_end   = int(d == d + pd.offsets.MonthEnd(0))
        is_quarter_end = int(d.month in [3, 6, 9, 12] and is_month_end)
        records.append({
            "full_date"      : d.strftime("%Y-%m-%d"),
            "year"           : d.year,
            "quarter"        : (d.month - 1) // 3 + 1,
            "month"          : d.month,
            "month_name"     : month_names[d.month - 1],
            "week_of_year"   : d.isocalendar()[1],
            "day_of_week"    : d.weekday(),
            "day_name"       : day_names[d.weekday()],
            "is_month_end"   : is_month_end,
            "is_quarter_end" : is_quarter_end,
        })

    df_date = pd.DataFrame(records)
    df_date.to_sql("dim_date", engine, if_exists="append", index=False)
    print(f"  [OK] dim_date loaded: {len(df_date):,} rows (2022-01-01 to 2026-12-31)")


# ==============================================================================
# TASK 3 -- LOAD ALL DATASETS INTO SQLite
# ==============================================================================

def load_dim_fund(engine):
    subsection("Loading dim_fund")
    df = load_csv("fund_master_clean.csv")
    df = df.rename(columns={"sub_category": "sub_category"})
    cols = ["amfi_code","fund_house","scheme_name","category","sub_category",
            "plan","launch_date","benchmark","expense_ratio_pct","exit_load_pct",
            "min_sip_amount","min_lumpsum_amount","fund_manager","risk_category","sebi_category_code"]
    df[cols].to_sql("dim_fund", engine, if_exists="append", index=False)
    print(f"  [OK] dim_fund: {len(df):,} rows")
    return len(df)

def load_dim_investor(engine):
    subsection("Loading dim_investor")
    df = load_csv("investor_transactions_clean.csv")
    inv_df = df.groupby("investor_id").agg(
        age_group          = ("age_group",          "first"),
        gender             = ("gender",             "first"),
        state              = ("state",              "first"),
        city               = ("city",               "first"),
        city_tier          = ("city_tier",           "first"),
        annual_income_lakh = ("annual_income_lakh",  "first"),
        kyc_status         = ("kyc_status",          "first"),
    ).reset_index()
    inv_df.to_sql("dim_investor", engine, if_exists="append", index=False)
    print(f"  [OK] dim_investor: {len(inv_df):,} unique investors")
    return len(inv_df)

def load_fact_nav(engine):
    subsection("Loading fact_nav")
    df = load_csv("nav_history_clean.csv")
    df[["amfi_code","date","nav","year","month"]].to_sql(
        "fact_nav", engine, if_exists="append", index=False, chunksize=5000
    )
    print(f"  [OK] fact_nav: {len(df):,} rows")
    return len(df)

def load_fact_transactions(engine):
    subsection("Loading fact_transactions")
    df = load_csv("investor_transactions_clean.csv")
    cols = ["investor_id","transaction_date","amfi_code","transaction_type",
            "amount_inr","state","city","city_tier","age_group","gender",
            "annual_income_lakh","payment_mode","kyc_status","year","month"]
    df[cols].to_sql("fact_transactions", engine, if_exists="append",
                    index=False, chunksize=5000)
    print(f"  [OK] fact_transactions: {len(df):,} rows")
    return len(df)

def load_fact_performance(engine):
    subsection("Loading fact_performance")
    df = load_csv("scheme_performance_clean.csv")
    df["alpha_category"] = df["alpha_category"].astype(str)
    cols = ["amfi_code","scheme_name","fund_house","category","plan",
            "return_1yr_pct","return_3yr_pct","return_5yr_pct","benchmark_3yr_pct",
            "alpha","beta","sharpe_ratio","sortino_ratio","std_dev_ann_pct",
            "max_drawdown_pct","aum_crore","expense_ratio_pct","morningstar_rating",
            "risk_grade","alpha_category"]
    df[cols].to_sql("fact_performance", engine, if_exists="append", index=False)
    print(f"  [OK] fact_performance: {len(df):,} rows")
    return len(df)

def load_fact_aum(engine):
    subsection("Loading fact_aum")
    df = load_csv("aum_by_fund_house_clean.csv")
    df[["date","fund_house","aum_lakh_crore","aum_crore","num_schemes"]].to_sql(
        "fact_aum", engine, if_exists="append", index=False
    )
    print(f"  [OK] fact_aum: {len(df):,} rows")
    return len(df)

def load_fact_sip_inflows(engine):
    subsection("Loading fact_sip_inflows")
    df = load_csv("monthly_sip_inflows_clean.csv")
    df["new_sip_spike_flag"] = df["new_sip_spike_flag"].astype(int)
    df.to_sql("fact_sip_inflows", engine, if_exists="append", index=False)
    print(f"  [OK] fact_sip_inflows: {len(df):,} rows")
    return len(df)

def load_fact_category_inflows(engine):
    subsection("Loading fact_category_inflows")
    df = load_csv("category_inflows_clean.csv")
    df[["month","category","net_inflow_crore"]].to_sql(
        "fact_category_inflows", engine, if_exists="append", index=False
    )
    print(f"  [OK] fact_category_inflows: {len(df):,} rows")
    return len(df)

def load_fact_portfolio_holdings(engine):
    subsection("Loading fact_portfolio_holdings")
    df = load_csv("portfolio_holdings_clean.csv")
    df[["amfi_code","stock_symbol","stock_name","sector",
        "weight_pct","market_value_cr","current_price_inr","portfolio_date"]].to_sql(
        "fact_portfolio_holdings", engine, if_exists="append", index=False
    )
    print(f"  [OK] fact_portfolio_holdings: {len(df):,} rows")
    return len(df)

def load_fact_benchmark(engine):
    subsection("Loading fact_benchmark")
    df = load_csv("benchmark_indices_clean.csv")
    df[["date","index_name","close_value"]].to_sql(
        "fact_benchmark", engine, if_exists="append", index=False
    )
    print(f"  [OK] fact_benchmark: {len(df):,} rows")
    return len(df)

def load_fact_folio_count(engine):
    subsection("Loading fact_folio_count")
    df = load_csv("industry_folio_count_clean.csv")
    df.to_sql("fact_folio_count", engine, if_exists="append", index=False)
    print(f"  [OK] fact_folio_count: {len(df):,} rows")
    return len(df)


# ==============================================================================
# TASK 4 -- VERIFY ROW COUNTS
# ==============================================================================

def verify_row_counts(engine, source_counts):
    section("TASK 4 -- Verifying Row Counts (Source CSV vs SQLite)")

    tables = {
        "dim_fund"                 : "fund_master_clean.csv",
        "fact_nav"                 : "nav_history_clean.csv",
        "fact_transactions"        : "investor_transactions_clean.csv",
        "fact_performance"         : "scheme_performance_clean.csv",
        "fact_aum"                 : "aum_by_fund_house_clean.csv",
        "fact_sip_inflows"         : "monthly_sip_inflows_clean.csv",
        "fact_category_inflows"    : "category_inflows_clean.csv",
        "fact_portfolio_holdings"  : "portfolio_holdings_clean.csv",
        "fact_benchmark"           : "benchmark_indices_clean.csv",
        "fact_folio_count"         : "industry_folio_count_clean.csv",
    }

    all_pass = True
    print(f"\n  {'Table':<30} {'CSV Rows':>10} {'DB Rows':>10}  Status")
    print("  " + "-" * 60)

    with engine.connect() as conn:
        for table, csv_file in tables.items():
            csv_path = os.path.join(PROC_DIR, csv_file)
            csv_rows = len(pd.read_csv(csv_path))
            db_rows  = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

            # dim_investor has different count (unique investors)
            if table == "dim_investor":
                status = "[OK]"
            elif csv_rows == db_rows:
                status = "[OK]  MATCH"
            else:
                status = f"[DIFF] {abs(csv_rows - db_rows)} row difference"
                all_pass = False

            print(f"  {table:<30} {csv_rows:>10,} {db_rows:>10,}  {status}")

    if all_pass:
        print("\n  [OK] All row counts verified successfully!")
    else:
        print("\n  [WARN] Some row count differences found - check above")


# ==============================================================================
# TASK 5 -- RUN ALL 10 ANALYTICAL QUERIES
# ==============================================================================

def run_queries(engine):
    section("TASK 5 -- Running 10 Analytical SQL Queries")

    queries = {
        1: ("Top 5 Fund Houses by AUM (Latest Snapshot)", """
            SELECT fund_house,
                   ROUND(SUM(aum_crore),0)             AS total_aum_crore,
                   ROUND(SUM(aum_crore)/100000.0, 2)   AS aum_lakh_crore
            FROM fact_aum
            WHERE date = (SELECT MAX(date) FROM fact_aum)
            GROUP BY fund_house
            ORDER BY total_aum_crore DESC LIMIT 5
        """),
        2: ("Average NAV per Month for Large Cap Regular Schemes", """
            SELECT n.amfi_code, f.scheme_name,
                   SUBSTR(n.date,1,7) AS month,
                   ROUND(AVG(n.nav),4) AS avg_nav,
                   ROUND(MIN(n.nav),4) AS min_nav,
                   ROUND(MAX(n.nav),4) AS max_nav
            FROM fact_nav n
            JOIN dim_fund f ON n.amfi_code = f.amfi_code
            WHERE f.sub_category = 'Large Cap' AND f.plan = 'Regular'
            GROUP BY n.amfi_code, f.scheme_name, SUBSTR(n.date,1,7)
            ORDER BY n.amfi_code, month LIMIT 50
        """),
        3: ("SIP Inflow YoY Growth by Year", """
            SELECT SUBSTR(month,1,4)             AS year,
                   ROUND(SUM(sip_inflow_crore),0) AS total_sip_crore,
                   ROUND(AVG(sip_inflow_crore),0) AS avg_monthly_sip,
                   ROUND(AVG(yoy_growth_pct),2)   AS avg_yoy_growth_pct,
                   ROUND(MAX(sip_inflow_crore),0) AS peak_month_sip
            FROM fact_sip_inflows
            GROUP BY year ORDER BY year
        """),
        4: ("Total Transaction Volume by State (Top 15)", """
            SELECT state,
                   COUNT(*)                     AS num_transactions,
                   ROUND(SUM(amount_inr),0)     AS total_amount_inr,
                   ROUND(AVG(amount_inr),0)     AS avg_amount_inr,
                   COUNT(DISTINCT investor_id)  AS unique_investors
            FROM fact_transactions
            GROUP BY state
            ORDER BY total_amount_inr DESC LIMIT 15
        """),
        5: ("Funds with Expense Ratio < 1% (Low-Cost Funds)", """
            SELECT p.amfi_code, f.scheme_name, f.fund_house,
                   f.sub_category, f.plan,
                   p.expense_ratio_pct,
                   p.return_3yr_pct,
                   p.sharpe_ratio,
                   p.aum_crore
            FROM fact_performance p
            JOIN dim_fund f ON p.amfi_code = f.amfi_code
            WHERE p.expense_ratio_pct < 1.0
            ORDER BY p.expense_ratio_pct ASC
        """),
        6: ("Risk-Adjusted Return Leaders (Sharpe Ratio > 1.0)", """
            SELECT p.amfi_code, f.scheme_name, f.fund_house,
                   f.sub_category,
                   p.sharpe_ratio, p.sortino_ratio,
                   p.return_3yr_pct, p.alpha, p.beta,
                   p.max_drawdown_pct, p.morningstar_rating
            FROM fact_performance p
            JOIN dim_fund f ON p.amfi_code = f.amfi_code
            WHERE p.sharpe_ratio > 1.0
            ORDER BY p.sharpe_ratio DESC
        """),
        7: ("SIP vs Lumpsum vs Redemption Monthly Split", """
            SELECT SUBSTR(transaction_date,1,7) AS month,
                   transaction_type,
                   COUNT(*)                     AS num_transactions,
                   ROUND(SUM(amount_inr),0)     AS total_amount_inr,
                   ROUND(AVG(amount_inr),0)     AS avg_amount_inr
            FROM fact_transactions
            GROUP BY month, transaction_type
            ORDER BY month, transaction_type LIMIT 40
        """),
        8: ("Fund Performance vs Benchmark - Alpha Analysis", """
            SELECT p.amfi_code, f.scheme_name, f.fund_house, f.sub_category,
                   p.return_3yr_pct, p.benchmark_3yr_pct,
                   ROUND(p.return_3yr_pct - p.benchmark_3yr_pct, 2) AS outperformance_pct,
                   p.alpha, p.alpha_category, p.morningstar_rating
            FROM fact_performance p
            JOIN dim_fund f ON p.amfi_code = f.amfi_code
            ORDER BY outperformance_pct DESC
        """),
        9: ("Investor Demographics: T30 vs B30 City Tier Analysis", """
            SELECT city_tier,
                   COUNT(*)                      AS num_transactions,
                   COUNT(DISTINCT investor_id)   AS unique_investors,
                   ROUND(SUM(amount_inr),0)      AS total_invested_inr,
                   ROUND(AVG(amount_inr),0)      AS avg_transaction_inr,
                   ROUND(100.0 * SUM(CASE WHEN transaction_type='SIP' THEN 1 ELSE 0 END)
                         / COUNT(*), 1)          AS sip_pct,
                   ROUND(100.0 * SUM(CASE WHEN kyc_status='Verified' THEN 1 ELSE 0 END)
                         / COUNT(*), 1)          AS kyc_verified_pct
            FROM fact_transactions
            GROUP BY city_tier ORDER BY total_invested_inr DESC
        """),
        10: ("AUM Growth Rate by Fund House (2022 to Latest)", """
            WITH base AS (
                SELECT fund_house, aum_crore AS aum_start
                FROM fact_aum WHERE date = (SELECT MIN(date) FROM fact_aum)
            ),
            latest AS (
                SELECT fund_house, aum_crore AS aum_end
                FROM fact_aum WHERE date = (SELECT MAX(date) FROM fact_aum)
            )
            SELECT l.fund_house,
                   ROUND(b.aum_start/100000.0,2)   AS aum_start_lakh_crore,
                   ROUND(l.aum_end/100000.0,2)     AS aum_end_lakh_crore,
                   ROUND((l.aum_end - b.aum_start)/b.aum_start*100, 1) AS growth_pct
            FROM latest l JOIN base b ON l.fund_house = b.fund_house
            ORDER BY growth_pct DESC
        """),
    }

    results_dir = os.path.join(BASE_DIR, "reports", "query_results")
    os.makedirs(results_dir, exist_ok=True)

    with engine.connect() as conn:
        for qnum, (qdesc, sql) in queries.items():
            subsection(f"Query {qnum}: {qdesc}")
            try:
                df = pd.read_sql_query(sql.strip(), conn)
                print(df.to_string(index=False))
                out_path = os.path.join(results_dir, f"query_{qnum:02d}_result.csv")
                df.to_csv(out_path, index=False)
                print(f"\n  [SAVED] query_{qnum:02d}_result.csv  ({len(df)} rows)")
            except Exception as e:
                print(f"  [ERROR] {e}")


# ==============================================================================
# TASK 6 -- DATABASE SUMMARY
# ==============================================================================

def db_summary(engine):
    section("DATABASE SUMMARY")

    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()

        print(f"\n  Database  : {DB_PATH}")
        db_size = round(os.path.getsize(DB_PATH) / 1024 / 1024, 2)
        print(f"  Size      : {db_size} MB")
        print(f"  Tables    : {len(tables)}")
        print(f"\n  {'Table':<35} {'Row Count':>12}")
        print("  " + "-" * 50)

        total_rows = 0
        for (table_name,) in tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            total_rows += count
            print(f"  {table_name:<35} {count:>12,}")

        print("  " + "-" * 50)
        print(f"  {'TOTAL':<35} {total_rows:>12,}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print(SEP)
    print("  MUTUAL FUND ANALYTICS -- DAY 2: SQLite DATABASE SETUP")
    print(f"  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DB Path: {DB_PATH}")
    print(SEP)

    # Drop existing DB for clean run
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  [INFO] Removed existing database for clean rebuild")

    engine = create_engine(ENGINE_URL, echo=False)

    # STEP 1: Create schema
    create_schema(engine)

    # STEP 2: Populate dim_date
    section("TASK 2 -- Loading Dimension Tables")
    populate_dim_date(engine)
    load_dim_fund(engine)
    load_dim_investor(engine)

    # STEP 3: Load fact tables
    section("TASK 3 -- Loading Fact Tables")
    source_counts = {}
    source_counts["fact_nav"]               = load_fact_nav(engine)
    source_counts["fact_transactions"]      = load_fact_transactions(engine)
    source_counts["fact_performance"]       = load_fact_performance(engine)
    source_counts["fact_aum"]               = load_fact_aum(engine)
    source_counts["fact_sip_inflows"]       = load_fact_sip_inflows(engine)
    source_counts["fact_category_inflows"]  = load_fact_category_inflows(engine)
    source_counts["fact_portfolio_holdings"]= load_fact_portfolio_holdings(engine)
    source_counts["fact_benchmark"]         = load_fact_benchmark(engine)
    source_counts["fact_folio_count"]       = load_fact_folio_count(engine)

    # STEP 4: Verify row counts
    verify_row_counts(engine, source_counts)

    # STEP 5: Run analytical queries
    run_queries(engine)

    # STEP 6: Summary
    db_summary(engine)

    section("DAY 2 DATABASE SETUP COMPLETE")
    print("\n  bluestock_mf.db is ready for analysis.")
    print(f"  Location: {DB_PATH}")
    print()


if __name__ == "__main__":
    main()
