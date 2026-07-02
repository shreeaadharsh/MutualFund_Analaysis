# Power BI Dashboard Setup Guide

This document provides step-by-step instructions to recreate the **Mutual Fund Performance Dashboard** in Power BI Desktop using the processed CSV files.

---

## 1. Import Datasets
1. Open **Power BI Desktop**.
2. Click **Get Data** → **Text/CSV**.
3. Load all 10 cleaned datasets from `data/processed/`:
   - `fund_master_clean.csv` (Rename to `dim_fund`)
   - `investor_transactions_clean.csv` (Rename to `fact_transactions`)
   - `scheme_performance_clean.csv` (Rename to `fact_performance`)
   - `nav_history_clean.csv` (Rename to `fact_nav`)
   - `aum_by_fund_house_clean.csv` (Rename to `fact_aum`)
   - `monthly_sip_inflows_clean.csv` (Rename to `fact_sip_inflows`)
   - `category_inflows_clean.csv` (Rename to `fact_category_inflows`)
   - `industry_folio_count_clean.csv` (Rename to `fact_folio_count`)
   - `benchmark_indices_clean.csv` (Rename to `fact_benchmark`)
   - `portfolio_holdings_clean.csv` (Rename to `fact_portfolio_holdings`)

---

## 2. Establish Model Relationships
Go to the **Model View** and establish the following relationships (Ensure they are 1-to-many where applicable):

1. **`dim_fund[amfi_code]`** (1) ─── (0..*) **`fact_nav[amfi_code]`**
2. **`dim_fund[amfi_code]`** (1) ─── (0..*) **`fact_transactions[amfi_code]`**
3. **`dim_fund[amfi_code]`** (1) ─── (1) **`fact_performance[amfi_code]`**
4. **`dim_fund[amfi_code]`** (1) ─── (0..*) **`fact_portfolio_holdings[amfi_code]`**
5. **`fact_transactions[investor_id]`** (0..*) ─── (1) **`dim_investor`** (Create this dimension from transaction data by clicking *New Table* in modeling tab with: `dim_investor = SUMMARIZE(fact_transactions, fact_transactions[investor_id], fact_transactions[age_group], fact_transactions[gender], fact_transactions[state], fact_transactions[city], fact_transactions[city_tier], fact_transactions[annual_income_lakh], fact_transactions[kyc_status])`)
6. **`fact_nav[date]`** (0..*) ─── (1) **`fact_benchmark[date]`** (Active relationship for daily comparisons)

---

## 3. Create DAX Measures
Create a dedicated table named `_Measures` and add the following DAX equations:

### Total AUM (Page 1 KPI)
```dax
Total_AUM_Crore = SUM(fact_performance[aum_crore])
```

### Total AUM Formatted
```dax
Total_AUM_Formatted = 
VAR AUM = [Total_AUM_Crore]
RETURN
    IF(AUM >= 100000, 
        FORMAT(AUM / 100000, "₹0.00") & "L Cr", 
        FORMAT(AUM, "₹#,##0") & " Cr"
    )
```

### SIP Inflows (Page 1 KPI)
```dax
Latest_SIP_Inflow = 
CALCULATE(
    SUM(fact_sip_inflows[sip_inflow_crore]),
    FILTER(fact_sip_inflows, fact_sip_inflows[month] = "2025-12")
)
```

### Total Folios (Page 1 KPI)
```dax
Latest_Folios = 
CALCULATE(
    SUM(fact_folio_count[total_folios_crore]),
    FILTER(fact_folio_count, fact_folio_count[month] = "2025-12")
)
```

### Average Sharpe Ratio (Page 2)
```dax
Avg_Sharpe = AVERAGE(fact_performance[sharpe_ratio])
```

### Monthly Active SIPs
```dax
Active_SIP_Mandates = SUM(fact_sip_inflows[active_sip_accounts_crore])
```

---

## 4. Dashboard Visual Layouts

### Bluestock Brand Theme Settings:
- Background Color: Dark Slate `#0F172A`
- Card Color: Dark Grey/Blue `#1E293B`
- Primary Visual Color: Blue `#3B82F6`
- Accent Highlight: Cyan `#06B6D4`
- Positive Growth Color: Teal `#14B8A6`
- Negative/Correction Color: Red `#EF4444`

---

### Page 1: Industry Overview
1. **KPI Cards:**
   - Visual 1: `Total_AUM_Formatted` measure (Display: **₹81.5L Cr**)
   - Visual 2: `Latest_SIP_Inflow` measure (Display: **₹31,002 Cr**)
   - Visual 3: `Latest_Folios` measure (Display: **26.12 Cr**)
   - Visual 4: Count of unique AMFI codes (Display: **1,908** for industry)
2. **Total AUM Growth Trend (Line Chart):**
   - Axis: `fact_aum[date]` (Year/Month)
   - Values: `fact_aum[aum_crore]`
3. **Top AMCs by AUM (Horizontal Bar Chart):**
   - Y-Axis: `fact_aum[fund_house]`
   - X-Axis: `fact_aum[aum_crore]`

---

### Page 2: Fund Performance
1. **Slicers Panel (Left Side):**
   - Fund House (`dim_fund[fund_house]`)
   - Category (`dim_fund[category]`)
   - Plan (`dim_fund[plan]`)
2. **Risk-Return Bubble Chart (Scatter Plot):**
   - X-Axis: `fact_performance[return_3yr_pct]` (Returns)
   - Y-Axis: `fact_performance[max_drawdown_pct]` (Risk proxy)
   - Size: `fact_performance[aum_crore]`
   - Legend: `dim_fund[category]`
3. **Scorecard (Table Visual):**
   - Columns: `Rank`, `Scheme Name`, `Score`, `3Yr Return`, `Sharpe`, `Expense Ratio`

---

### Page 3: Investor Analytics
1. **Slicers Panel:**
   - State (`dim_investor[state]`)
   - Age Group (`dim_investor[age_group]`)
   - City Tier (`dim_investor[city_tier]`)
2. **Transaction Share (Donut Chart):**
   - Legend: `fact_transactions[transaction_type]` (SIP vs Lumpsum vs Redemption)
   - Values: Count of `fact_transactions[txn_id]`
3. **Geographic Distribution (Horizontal Bar Chart):**
   - Y-Axis: `fact_transactions[state]`
   - X-Axis: Sum of `fact_transactions[amount_inr]`
4. **SIP Ticket Size (Grouped Bar Chart):**
   - X-Axis: `dim_investor[age_group]`
   - Y-Axis: Average of `fact_transactions[amount_inr]`

---

### Page 4: SIP & Market Trends
1. **SIP vs Nifty 50 Index (Dual Axis Chart):**
   - X-Axis: `fact_sip_inflows[month]`
   - Column Values (Y-Axis 1): `fact_sip_inflows[sip_inflow_crore]`
   - Line Values (Y-Axis 2): `fact_benchmark[close_value]` (Filtered where `index_name = "NIFTY50"`)
2. **Category Net Inflow (Column Chart):**
   - X-Axis: `fact_category_inflows[category]`
   - Y-Axis: Sum of `fact_category_inflows[net_inflow_crore]`
3. **Net Inflow Intensity Heatmap:**
   - Visual type: Matrix visual with conditional formatting (Color scales)
   - Rows: `fact_category_inflows[category]`
   - Columns: `fact_category_inflows[month]`
   - Values: Sum of `fact_category_inflows[net_inflow_crore]`
