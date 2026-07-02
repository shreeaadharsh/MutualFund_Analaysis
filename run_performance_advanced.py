import os
import sys
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
CHARTS_DIR = os.path.join(BASE_DIR, "reports", "charts")
os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Load clean datasets
df_nav = pd.read_csv(os.path.join(PROC_DIR, "nav_history_clean.csv"))
df_fund = pd.read_csv(os.path.join(PROC_DIR, "fund_master_clean.csv"))
df_tx = pd.read_csv(os.path.join(PROC_DIR, "investor_transactions_clean.csv"))
df_port = pd.read_csv(os.path.join(PROC_DIR, "portfolio_holdings_clean.csv"))
df_scorecard = pd.read_csv(os.path.join(PROC_DIR, "fund_scorecard.csv"))

# Parse dates
df_nav['date'] = pd.to_datetime(df_nav['date'])
df_tx['transaction_date'] = pd.to_datetime(df_tx['transaction_date'])

print("Clean datasets loaded.")

# Pivot NAV to get daily returns
df_nav_pivot = df_nav.pivot(index='date', columns='amfi_code', values='nav')
df_returns = df_nav_pivot.pct_change()

# ==============================================================================
# TASK 1: HISTORICAL VaR (95%) & CVaR (95%)
# ==============================================================================

var_cvar_results = []
for code in df_returns.columns:
    r_series = df_returns[code].dropna()
    if len(r_series) == 0:
        continue
    
    # 5th percentile of daily return distribution
    var_95_daily = r_series.quantile(0.05)
    # Mean of returns below the VaR threshold
    cvar_95_daily = r_series[r_series <= var_95_daily].mean()
    
    scheme_name = df_fund[df_fund['amfi_code'] == code]['scheme_name'].values[0]
    
    # Express as positive loss percentage
    var_cvar_results.append({
        'amfi_code': code,
        'scheme_name': scheme_name,
        'daily_var_95_pct': -var_95_daily * 100.0,
        'daily_cvar_95_pct': -cvar_95_daily * 100.0,
        'annual_var_95_pct': -var_95_daily * np.sqrt(252) * 100.0,
        'annual_cvar_95_pct': -cvar_95_daily * np.sqrt(252) * 100.0
    })

df_var_cvar = pd.DataFrame(var_cvar_results)
df_var_cvar.to_csv(os.path.join(PROC_DIR, "var_cvar_report.csv"), index=False)
print("Saved var_cvar_report.csv.")

# ==============================================================================
# TASK 2: ROLLING 90-DAY SHARPE CHART
# ==============================================================================

# Key funds
key_funds = {
    119551: 'SBI Bluechip Regular',
    120503: 'ICICI Pru Bluechip Regular',
    118632: 'Nippon India Large Cap Regular',
    119092: 'Axis Bluechip Regular',
    120841: 'Kotak Bluechip Regular'
}

Rf_daily = 0.065 / 252  # Daily Risk-Free Rate (6.5% / 252)

plt.figure(figsize=(14, 7))

for code, label in key_funds.items():
    if code in df_returns.columns:
        r_series = df_returns[code]
        # Rolling Sharpe
        rolling_mean = r_series.rolling(90).mean()
        rolling_std = r_series.rolling(90).std()
        rolling_sharpe = (rolling_mean - Rf_daily) / rolling_std * np.sqrt(252)
        
        plt.plot(rolling_sharpe.index, rolling_sharpe, label=label, linewidth=2)

plt.title('Rolling 90-Day Sharpe Ratio Comparison (2022 - 2026)')
plt.xlabel('Date')
plt.ylabel('Rolling 90-Day Sharpe Ratio')
plt.legend(loc='lower left')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "rolling_sharpe_chart.png"), dpi=150)
plt.close()
print("Saved rolling_sharpe_chart.png.")

# ==============================================================================
# TASK 3: INVESTOR COHORT ANALYSIS
# ==============================================================================

# Find first transaction date per investor
first_tx = df_tx.groupby('investor_id')['transaction_date'].min().reset_index()
first_tx['cohort_year'] = first_tx['transaction_date'].dt.year

# Join back to investor transactions
df_tx_cohort = pd.merge(df_tx, first_tx[['investor_id', 'cohort_year']], on='investor_id')

cohort_metrics = []
for year, group in df_tx_cohort.groupby('cohort_year'):
    # Avg SIP amount
    sip_group = group[group['transaction_type'] == 'SIP']
    avg_sip = sip_group['amount_inr'].mean() if len(sip_group) > 0 else 0
    
    # Total invested
    total_invested = group['amount_inr'].sum()
    
    # Top fund preference (by total invested amount)
    top_fund_code = group.groupby('amfi_code')['amount_inr'].sum().idxmax()
    top_fund_name = df_fund[df_fund['amfi_code'] == top_fund_code]['scheme_name'].values[0]
    
    cohort_metrics.append({
        'cohort_year': year,
        'unique_investors': group['investor_id'].nunique(),
        'avg_sip_amount_inr': avg_sip,
        'total_invested_crore': total_invested / 10000000.0,
        'top_fund_preference': top_fund_name
    })

df_cohorts = pd.DataFrame(cohort_metrics)
print("\nInvestor Cohort Analysis:")
print(df_cohorts.to_string(index=False))

# ==============================================================================
# TASK 4: SIP CONTINUITY ANALYSIS
# ==============================================================================

df_sip_only = df_tx[df_tx['transaction_type'] == 'SIP'].copy()
# Group by investor, count transactions
sip_counts = df_sip_only.groupby('investor_id').size()
eligible_investors = sip_counts[sip_counts >= 6].index

at_risk_investors = []
all_eligible_metrics = []

for inv_id in eligible_investors:
    inv_tx = df_sip_only[df_sip_only['investor_id'] == inv_id].sort_values('transaction_date')
    # Compute gaps in days
    gaps = inv_tx['transaction_date'].diff().dt.days.dropna()
    avg_gap = gaps.mean() if len(gaps) > 0 else 0
    
    status = "Active"
    if avg_gap > 35.0:
        status = "At-Risk"
        at_risk_investors.append(inv_id)
        
    all_eligible_metrics.append({
        'investor_id': inv_id,
        'sip_count': len(inv_tx),
        'avg_gap_days': avg_gap,
        'status': status
    })

df_sip_continuity = pd.DataFrame(all_eligible_metrics)
at_risk_pct = len(at_risk_investors) / len(eligible_investors) * 100.0
print(f"\nSIP Continuity Summary:")
print(f"  Eligible Investors (6+ SIPs): {len(eligible_investors):,}")
print(f"  At-Risk Investors (>35 day gap): {len(at_risk_investors):,}")
print(f"  At-Risk Ratio: {at_risk_pct:.2f}%")

# ==============================================================================
# TASK 5: SECTOR HHI CONCENTRATION
# ==============================================================================

# Group holdings by scheme and sector, sum the weight
df_sec_weights = df_port.groupby(['amfi_code', 'sector'])['weight_pct'].sum().reset_index()

hhi_results = []
for code, group in df_sec_weights.groupby('amfi_code'):
    # HHI = Sum of squared sector weights
    # If weights are out of 100, HHI ranges from 0 to 10000.
    hhi = np.sum(group['weight_pct'] ** 2)
    scheme_name = df_fund[df_fund['amfi_code'] == code]['scheme_name'].values[0]
    category = df_fund[df_fund['amfi_code'] == code]['category'].values[0]
    
    # Filter for Equity funds only
    if category == 'Equity':
        hhi_results.append({
            'amfi_code': code,
            'scheme_name': scheme_name,
            'sector_hhi': hhi,
            'concentration': 'High' if hhi > 2500 else ('Moderate' if hhi > 1500 else 'Low')
        })

df_hhi = pd.DataFrame(hhi_results).sort_values('sector_hhi', ascending=False).reset_index(drop=True)
print("\nTop 5 Sector Concentrated Equity Funds (HHI):")
print(df_hhi.head(5).to_string(index=False))

# ==============================================================================
# TASK 6: SIMPLE FUND RECOMMENDER (recommender.py)
# ==============================================================================

recommender_code = """# standalone Mutual Fund Recommender
import pandas as pd
import sys

def get_recommendations(risk_appetite):
    # Load scorecard & fund master
    df_score = pd.read_csv("data/processed/fund_scorecard.csv")
    df_master = pd.read_csv("data/processed/fund_master_clean.csv")
    
    # Map risk appetite to dataset risk grades
    # risk categories in dataset: Low, Moderate, Moderately High, High, Very High
    risk_appetite = risk_appetite.strip().lower()
    
    if risk_appetite == 'low':
        target_grades = ['Low', 'Moderate']
    elif risk_appetite == 'moderate':
        target_grades = ['Moderate', 'Moderately High']
    elif risk_appetite == 'high':
        target_grades = ['High', 'Very High']
    else:
        print("Invalid risk appetite. Choose from: Low, Moderate, High")
        return None
        
    # Join scorecard and master to get risk categories
    df_merged = pd.merge(df_score, df_master[['amfi_code', 'risk_category']], on='amfi_code', how='left')
    
    # Filter by risk appetite and sort by Sharpe ratio
    df_filtered = df_merged[df_merged['risk_category'].isin(target_grades)]
    df_top = df_filtered.sort_values('sharpe_ratio', ascending=False).head(3)
    
    # Select columns
    return df_top[['final_rank', 'scheme_name', 'risk_category', 'sharpe_ratio', 'cagr_3yr_pct', 'expense_ratio_pct']]

def main():
    print("=" * 60)
    print("      BLUESTOCK MUTUAL FUND RECOMMENDER SYSTEM")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        risk = sys.argv[1]
    else:
        risk = input("Enter your risk appetite (Low / Moderate / High): ")
        
    df_rec = get_recommendations(risk)
    if df_rec is not None and len(df_rec) > 0:
        print(f"\\nTop 3 Recommended Funds for '{risk.capitalize()}' Risk Profile:")
        print("-" * 100)
        print(df_rec.to_string(index=False))
        print("-" * 100)
    else:
        print("No schemes match the criteria.")

if __name__ == "__main__":
    main()
"""

with open(os.path.join(BASE_DIR, "recommender.py"), "w", encoding="utf-8") as f:
    f.write(recommender_code)
print("Saved recommender.py.")
