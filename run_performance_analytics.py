import os
import sys
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import linregress
from datetime import datetime

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
df_bench = pd.read_csv(os.path.join(PROC_DIR, "benchmark_indices_clean.csv"))

# Parse dates
df_nav['date'] = pd.to_datetime(df_nav['date'])
df_bench['date'] = pd.to_datetime(df_bench['date'])

print(f"Loaded NAV data: {df_nav.shape} rows.")
print(f"Loaded Fund Master: {df_fund.shape} rows.")
print(f"Loaded Benchmarks: {df_bench.shape} rows.")

# Create pivot tables
df_nav_pivot = df_nav.pivot(index='date', columns='amfi_code', values='nav')
df_bench_pivot = df_bench.pivot(index='date', columns='index_name', values='close_value')

# 1. Compute Daily Returns
df_nav_returns = df_nav_pivot.pct_change()
df_bench_returns = df_bench_pivot.pct_change()

print("Computed daily returns.")

# ==============================================================================
# COMPUTE CAGR (1Yr, 3Yr, and Inception 4.4Yr)
# ==============================================================================

end_date = df_nav_pivot.index.max()

# Helper to find closest available date in the index
def get_closest_nav(date_target, df_pivot):
    if date_target in df_pivot.index:
        return df_pivot.loc[date_target]
    # find closest date after or before
    idx = df_pivot.index.get_indexer([date_target], method='nearest')[0]
    return df_pivot.iloc[idx]

# Targets: 1 Year ago, 3 Years ago, Inception (Start of series)
date_1yr = end_date - pd.DateOffset(years=1)
date_3yr = end_date - pd.DateOffset(years=3)
date_start = df_nav_pivot.index.min()

nav_end = df_nav_pivot.loc[end_date]
nav_1yr = get_closest_nav(date_1yr, df_nav_pivot)
nav_3yr = get_closest_nav(date_3yr, df_nav_pivot)
nav_start = df_nav_pivot.loc[date_start]

# Actual years elapsed for CAGR precision
y_1yr = (end_date - date_1yr).days / 365.25
y_3yr = (end_date - date_3yr).days / 365.25
y_start = (end_date - date_start).days / 365.25

cagr_1yr = (nav_end / nav_1yr) ** (1.0 / y_1yr) - 1.0
cagr_3yr = (nav_end / nav_3yr) ** (1.0 / y_3yr) - 1.0
cagr_inception = (nav_end / nav_start) ** (1.0 / y_start) - 1.0

# ==============================================================================
# COMPUTE RISK METRICS (Sharpe, Sortino, Alpha, Beta, Max Drawdown)
# ==============================================================================

Rf = 0.065  # Risk-Free Rate = 6.5%
results = []

for code in df_nav_pivot.columns:
    scheme_name = df_fund[df_fund['amfi_code'] == code]['scheme_name'].values[0]
    fund_house = df_fund[df_fund['amfi_code'] == code]['fund_house'].values[0]
    expense_ratio = df_fund[df_fund['amfi_code'] == code]['expense_ratio_pct'].values[0]
    
    # Returns series
    r_series = df_nav_returns[code].dropna()
    
    # Sharpe Ratio
    rp_annual = r_series.mean() * 252
    std_daily = r_series.std()
    std_annual = std_daily * np.sqrt(252)
    sharpe = (rp_annual - Rf) / std_annual if std_annual > 0 else 0
    
    # Sortino Ratio
    downside_returns = r_series[r_series < 0]
    downside_std_daily = np.sqrt(np.mean(downside_returns ** 2)) if len(downside_returns) > 0 else 0
    downside_std_annual = downside_std_daily * np.sqrt(252)
    sortino = (rp_annual - Rf) / downside_std_annual if downside_std_annual > 0 else 0
    
    # Alpha & Beta vs Nifty 100
    # Align dates
    df_align = pd.concat([r_series, df_bench_returns['NIFTY100']], axis=1, join='inner').dropna()
    slope, intercept, r_val, p_val, std_err = linregress(df_align['NIFTY100'], df_align[code])
    beta = slope
    alpha = intercept * 252  # Annualized Alpha
    
    # Max Drawdown & Date Range
    nav_series = df_nav_pivot[code].dropna()
    running_max = nav_series.cummax()
    drawdowns = nav_series / running_max - 1.0
    max_dd = drawdowns.min()
    
    # Find dates
    trough_idx = drawdowns.idxmin()
    peak_idx = nav_series.loc[:trough_idx].idxmax()
    
    # Recovery date
    post_trough = nav_series.loc[trough_idx:]
    recovery_idx = post_trough[post_trough >= nav_series[peak_idx]].index.min()
    if pd.isna(recovery_idx):
        recovery_date_str = "Not Recovered"
    else:
        recovery_date_str = recovery_idx.strftime('%Y-%m-%d')
        
    results.append({
        'amfi_code': code,
        'scheme_name': scheme_name,
        'fund_house': fund_house,
        'expense_ratio_pct': expense_ratio,
        'cagr_1yr_pct': cagr_1yr[code] * 100.0,
        'cagr_3yr_pct': cagr_3yr[code] * 100.0,
        'cagr_inception_pct': cagr_inception[code] * 100.0,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'beta': beta,
        'alpha_pct': alpha * 100.0,
        'max_drawdown_pct': max_dd * 100.0,
        'drawdown_peak_date': peak_idx.strftime('%Y-%m-%d'),
        'drawdown_trough_date': trough_idx.strftime('%Y-%m-%d'),
        'drawdown_recovery_date': recovery_date_str
    })

df_metrics = pd.DataFrame(results)

# Save Alpha Beta csv
df_metrics[['amfi_code', 'scheme_name', 'beta', 'alpha_pct']].to_csv(
    os.path.join(PROC_DIR, "alpha_beta.csv"), index=False
)
print("Saved alpha_beta.csv.")

# ==============================================================================
# COMPUTE SCORECARD
# ==============================================================================

# Normalise ranks (0 to 100, where 100 is best)
# For return, Sharpe, Alpha: higher is better
# For expense ratio, Max Drawdown: lower is better (less negative for drawdown)
df_metrics['rank_return'] = df_metrics['cagr_3yr_pct'].rank(pct=True) * 100.0
df_metrics['rank_sharpe'] = df_metrics['sharpe_ratio'].rank(pct=True) * 100.0
df_metrics['rank_alpha']  = df_metrics['alpha_pct'].rank(pct=True) * 100.0
df_metrics['rank_expense'] = (-df_metrics['expense_ratio_pct']).rank(pct=True) * 100.0
df_metrics['rank_drawdown'] = df_metrics['max_drawdown_pct'].rank(pct=True) * 100.0  # since max drawdown is negative, less negative is larger

df_metrics['composite_score'] = (
    0.30 * df_metrics['rank_return'] +
    0.25 * df_metrics['rank_sharpe'] +
    0.20 * df_metrics['rank_alpha'] +
    0.15 * df_metrics['rank_expense'] +
    0.10 * df_metrics['rank_drawdown']
)

# Sort and rank by scorecard
df_metrics = df_metrics.sort_values('composite_score', ascending=False).reset_index(drop=True)
df_metrics['final_rank'] = df_metrics.index + 1

scorecard_cols = [
    'final_rank', 'amfi_code', 'scheme_name', 'fund_house', 'composite_score',
    'cagr_1yr_pct', 'cagr_3yr_pct', 'cagr_inception_pct', 'sharpe_ratio',
    'sortino_ratio', 'beta', 'alpha_pct', 'max_drawdown_pct', 'expense_ratio_pct'
]
df_metrics[scorecard_cols].to_csv(os.path.join(PROC_DIR, "fund_scorecard.csv"), index=False)
print("Saved fund_scorecard.csv.")

# Print top 5 funds
print("\nTop 5 Funds by Scorecard:")
print(df_metrics[['final_rank', 'scheme_name', 'composite_score', 'cagr_3yr_pct', 'sharpe_ratio']].head(5).to_string(index=False))

# ==============================================================================
# BENCHMARK COMPARISON CHART (Last 3 Years)
# ==============================================================================

# Get top 5 funds
top_5_codes = df_metrics['amfi_code'].head(5).tolist()

# Define 3 year window: target date 2023-05-29 to 2026-05-29
three_yr_start = pd.Timestamp('2023-05-29')
df_nav_3y = df_nav_pivot.loc[three_yr_start:end_date]
df_bench_3y = df_bench_pivot.loc[three_yr_start:end_date]

# Normalize to 100
df_nav_norm = (df_nav_3y / df_nav_3y.iloc[0]) * 100.0
df_bench_norm = (df_bench_3y / df_bench_3y.iloc[0]) * 100.0

plt.figure(figsize=(14, 7))

# Plot top 5 funds
for code in top_5_codes:
    s_name = df_fund[df_fund['amfi_code'] == code]['scheme_name'].values[0].split(' - ')[0]
    plt.plot(df_nav_norm.index, df_nav_norm[code], label=s_name, linewidth=1.5)

# Plot Benchmarks
plt.plot(df_bench_norm.index, df_bench_norm['NIFTY50'], label='NIFTY 50 (Benchmark)', color='black', linestyle='--', linewidth=2)
plt.plot(df_bench_norm.index, df_bench_norm['NIFTY100'], label='NIFTY 100 (Benchmark)', color='red', linestyle='-.', linewidth=2)

plt.title('Top 5 Mutual Funds vs Key Benchmarks - 3-Year Growth of ₹100 (2023 - 2026)')
plt.xlabel('Date')
plt.ylabel('Normalized Value (Base 100)')
plt.legend(loc='upper left')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "benchmark_comparison.png"), dpi=150)
plt.close()
print("Saved benchmark_comparison.png.")

# ==============================================================================
# COMPUTE TRACKING ERROR
# ==============================================================================

print("\nTracking Error vs Nifty 100 (Last 3 Years):")
for code in top_5_codes:
    s_name = df_fund[df_fund['amfi_code'] == code]['scheme_name'].values[0]
    f_ret = df_nav_returns.loc[three_yr_start:end_date, code]
    b_ret = df_bench_returns.loc[three_yr_start:end_date, 'NIFTY100']
    
    # Align returns
    df_align = pd.concat([f_ret, b_ret], axis=1).dropna()
    active_return = df_align[code] - df_align['NIFTY100']
    tracking_error = active_return.std() * np.sqrt(252)
    print(f"  {s_name:<60}: {tracking_error * 100.0:.2f}%")

print("\nAll calculations completed successfully.")
