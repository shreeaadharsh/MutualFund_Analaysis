-- ==============================================================================
-- Mutual Fund Analytics - Day 2
-- File: schema.sql
-- Purpose: Star schema DDL for SQLite database (bluestock_mf.db)
--
-- Schema Design:
--   Dimension tables : dim_fund, dim_date, dim_investor
--   Fact tables      : fact_nav, fact_transactions, fact_performance, fact_aum
-- ==============================================================================


-- ==============================================================================
-- DIMENSION TABLES
-- ==============================================================================

-- dim_fund: Master dimension for all mutual fund schemes
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code            INTEGER PRIMARY KEY,
    fund_house           TEXT    NOT NULL,
    scheme_name          TEXT    NOT NULL,
    category             TEXT    NOT NULL,        -- Equity / Debt
    sub_category         TEXT    NOT NULL,        -- Large Cap / Mid Cap etc.
    plan                 TEXT    NOT NULL,        -- Direct / Regular
    launch_date          TEXT,                   -- YYYY-MM-DD
    benchmark            TEXT,
    expense_ratio_pct    REAL    NOT NULL CHECK (expense_ratio_pct BETWEEN 0.0 AND 3.0),
    exit_load_pct        REAL    DEFAULT 0.0,
    min_sip_amount       REAL,
    min_lumpsum_amount   REAL,
    fund_manager         TEXT,
    risk_category        TEXT,                   -- Low / Moderate / High / Very High
    sebi_category_code   TEXT
);

-- dim_date: Date dimension for time-series analysis
CREATE TABLE IF NOT EXISTS dim_date (
    date_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    full_date      TEXT    NOT NULL UNIQUE,       -- YYYY-MM-DD
    year           INTEGER NOT NULL,
    quarter        INTEGER NOT NULL,              -- 1-4
    month          INTEGER NOT NULL,              -- 1-12
    month_name     TEXT    NOT NULL,              -- January..December
    week_of_year   INTEGER NOT NULL,
    day_of_week    INTEGER NOT NULL,              -- 0=Monday..6=Sunday
    day_name       TEXT    NOT NULL,              -- Monday..Sunday
    is_month_end   INTEGER NOT NULL DEFAULT 0,    -- 1 if last day of month
    is_quarter_end INTEGER NOT NULL DEFAULT 0     -- 1 if last day of quarter
);

-- dim_investor: Investor profile dimension (derived from transactions)
CREATE TABLE IF NOT EXISTS dim_investor (
    investor_id          TEXT    PRIMARY KEY,
    age_group            TEXT,                   -- 18-25 / 26-35 / 36-45 / 46-55 / 56+
    gender               TEXT,                   -- Male / Female
    state                TEXT,
    city                 TEXT,
    city_tier            TEXT,                   -- T30 / B30
    annual_income_lakh   REAL,
    kyc_status           TEXT    CHECK (kyc_status IN ('Verified', 'Pending', 'Rejected'))
);


-- ==============================================================================
-- FACT TABLES
-- ==============================================================================

-- fact_nav: Daily NAV fact table
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code    INTEGER NOT NULL,
    date         TEXT    NOT NULL,
    nav          REAL    NOT NULL CHECK (nav > 0),
    year         INTEGER,
    month        INTEGER,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    UNIQUE (amfi_code, date)
);

-- fact_transactions: Investor transaction fact table
CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id        TEXT    NOT NULL,
    transaction_date   TEXT    NOT NULL,
    amfi_code          INTEGER NOT NULL,
    transaction_type   TEXT    NOT NULL CHECK (transaction_type IN ('SIP','Lumpsum','Redemption','Switch In','Switch Out')),
    amount_inr         REAL    NOT NULL CHECK (amount_inr > 0),
    state              TEXT,
    city               TEXT,
    city_tier          TEXT,
    age_group          TEXT,
    gender             TEXT,
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT,
    year               INTEGER,
    month              INTEGER,
    FOREIGN KEY (amfi_code)   REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (investor_id) REFERENCES dim_investor(investor_id)
);

-- fact_performance: Scheme risk-return performance metrics
CREATE TABLE IF NOT EXISTS fact_performance (
    perf_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code          INTEGER NOT NULL UNIQUE,
    scheme_name        TEXT    NOT NULL,
    fund_house         TEXT    NOT NULL,
    category           TEXT,
    plan               TEXT,
    return_1yr_pct     REAL,
    return_3yr_pct     REAL,
    return_5yr_pct     REAL,
    benchmark_3yr_pct  REAL,
    alpha              REAL,
    beta               REAL,
    sharpe_ratio       REAL,
    sortino_ratio      REAL,
    std_dev_ann_pct    REAL,
    max_drawdown_pct   REAL,
    aum_crore          REAL    CHECK (aum_crore > 0),
    expense_ratio_pct  REAL    CHECK (expense_ratio_pct BETWEEN 0.1 AND 2.5),
    morningstar_rating INTEGER CHECK (morningstar_rating BETWEEN 1 AND 5),
    risk_grade         TEXT,
    alpha_category     TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- fact_aum: AUM by fund house (bi-annual)
CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT    NOT NULL,
    fund_house       TEXT    NOT NULL,
    aum_lakh_crore   REAL,
    aum_crore        REAL    NOT NULL CHECK (aum_crore > 0),
    num_schemes      INTEGER,
    UNIQUE (date, fund_house)
);

-- fact_sip_inflows: Monthly SIP industry inflow data
CREATE TABLE IF NOT EXISTS fact_sip_inflows (
    sip_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    month                     TEXT    NOT NULL UNIQUE,
    sip_inflow_crore          REAL    NOT NULL,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh     REAL,
    sip_aum_lakh_crore        REAL,
    yoy_growth_pct            REAL,
    new_sip_spike_flag        INTEGER DEFAULT 0
);

-- fact_category_inflows: Monthly inflows by fund category
CREATE TABLE IF NOT EXISTS fact_category_inflows (
    cat_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    month              TEXT    NOT NULL,
    category           TEXT    NOT NULL,
    net_inflow_crore   REAL    NOT NULL,
    UNIQUE (month, category)
);

-- fact_portfolio_holdings: Scheme-level stock holdings
CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    holding_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code         INTEGER NOT NULL,
    stock_symbol      TEXT    NOT NULL,
    stock_name        TEXT,
    sector            TEXT,
    weight_pct        REAL    CHECK (weight_pct BETWEEN 0 AND 100),
    market_value_cr   REAL,
    current_price_inr REAL,
    portfolio_date    TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- fact_benchmark: Daily benchmark index values
CREATE TABLE IF NOT EXISTS fact_benchmark (
    bench_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT    NOT NULL,
    index_name   TEXT    NOT NULL,
    close_value  REAL    NOT NULL CHECK (close_value > 0),
    UNIQUE (date, index_name)
);

-- fact_folio_count: Quarterly industry folio count
CREATE TABLE IF NOT EXISTS fact_folio_count (
    folio_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    month                   TEXT    NOT NULL UNIQUE,
    total_folios_crore      REAL,
    equity_folios_crore     REAL,
    debt_folios_crore       REAL,
    hybrid_folios_crore     REAL,
    others_folios_crore     REAL
);


-- ==============================================================================
-- INDEXES FOR QUERY PERFORMANCE
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_nav_amfi_date    ON fact_nav(amfi_code, date);
CREATE INDEX IF NOT EXISTS idx_nav_date         ON fact_nav(date);
CREATE INDEX IF NOT EXISTS idx_txn_date         ON fact_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_amfi         ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_txn_investor     ON fact_transactions(investor_id);
CREATE INDEX IF NOT EXISTS idx_txn_type         ON fact_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_txn_state        ON fact_transactions(state);
CREATE INDEX IF NOT EXISTS idx_perf_aum         ON fact_performance(aum_crore);
CREATE INDEX IF NOT EXISTS idx_aum_date         ON fact_aum(date);
CREATE INDEX IF NOT EXISTS idx_bench_date       ON fact_benchmark(date, index_name);
CREATE INDEX IF NOT EXISTS idx_holdings_amfi    ON fact_portfolio_holdings(amfi_code);
