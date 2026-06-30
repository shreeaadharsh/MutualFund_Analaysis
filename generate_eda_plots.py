import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure target directories exist
os.makedirs("reports/charts", exist_ok=True)
os.makedirs("notebooks", exist_ok=True)

# Load datasets
proc_dir = "data/processed"
df_fund = pd.read_csv(f"{proc_dir}/fund_master_clean.csv")
df_nav = pd.read_csv(f"{proc_dir}/nav_history_clean.csv")
df_aum = pd.read_csv(f"{proc_dir}/aum_by_fund_house_clean.csv")
df_sip = pd.read_csv(f"{proc_dir}/monthly_sip_inflows_clean.csv")
df_cat = pd.read_csv(f"{proc_dir}/category_inflows_clean.csv")
df_folio = pd.read_csv(f"{proc_dir}/industry_folio_count_clean.csv")
df_perf = pd.read_csv(f"{proc_dir}/scheme_performance_clean.csv")
df_tx = pd.read_csv(f"{proc_dir}/investor_transactions_clean.csv")
df_port = pd.read_csv(f"{proc_dir}/portfolio_holdings_clean.csv")
df_bench = pd.read_csv(f"{proc_dir}/benchmark_indices_clean.csv")

# Set seaborn style for clean visualizations
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 11

# ==============================================================================
# GENERATE STATS & CHARTS FOR DELIVERABLES
# ==============================================================================

# Chart 1: Daily NAV Trend for all 40 schemes (2022-2026)
plt.figure(figsize=(14, 7))
df_nav_pivot = df_nav.pivot(index='date', columns='amfi_code', values='nav')
df_nav_pivot.index = pd.to_datetime(df_nav_pivot.index)
for col in df_nav_pivot.columns:
    plt.plot(df_nav_pivot.index, df_nav_pivot[col], alpha=0.3, color='blue', linewidth=0.5)

# Highlight a few key schemes
sbi_blue = df_nav_pivot[119551] # SBI Bluechip Regular
hdfc_100 = df_nav_pivot[125497] # HDFC Top 100 Direct
plt.plot(df_nav_pivot.index, sbi_blue, label='SBI Bluechip Regular (119551)', color='darkorange', linewidth=2)
plt.plot(df_nav_pivot.index, hdfc_100, label='HDFC Top 100 Direct (125497)', color='green', linewidth=2)

plt.axvspan(pd.Timestamp('2023-04-01'), pd.Timestamp('2023-12-31'), color='green', alpha=0.1, label='2023 Bull Run')
plt.axvspan(pd.Timestamp('2024-03-01'), pd.Timestamp('2024-06-01'), color='red', alpha=0.1, label='2024 Market Correction')
plt.title('Daily NAV Trend for 40 Schemes (2022 - 2026)')
plt.xlabel('Date')
plt.ylabel('NAV (INR)')
plt.legend(loc='upper left')
plt.tight_layout()
plt.savefig('reports/charts/nav_trends.png', dpi=150)
plt.close()

# Chart 2: Grouped AUM Growth Bar Chart (2022-2025)
plt.figure(figsize=(14, 7))
df_aum['year'] = pd.to_datetime(df_aum['date']).dt.year
# Group AUM by year and fund house
df_aum_annual = df_aum.groupby(['year', 'fund_house'])['aum_crore'].sum().reset_index()
# Filter for top fund houses
top_houses = df_aum.groupby('fund_house')['aum_crore'].max().nlargest(6).index
df_aum_top = df_aum_annual[df_aum_annual['fund_house'].isin(top_houses)]
sns.barplot(data=df_aum_top, x='year', y='aum_crore', hue='fund_house', palette='deep')
plt.title('AUM Growth by Top Fund House (2022 - 2025)')
plt.xlabel('Year')
plt.ylabel('Total AUM (Crore INR)')
# Annotate SBI AUM Dominance
plt.annotate('SBI leads with ₹12.5L Cr AUM (Dec 2025)', xy=(3, 1250000), xytext=(1.5, 1100000),
             arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))
plt.legend(title='Fund House', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('reports/charts/aum_growth.png', dpi=150)
plt.close()

# Chart 3: Monthly SIP Inflow Time-Series
plt.figure(figsize=(12, 6))
df_sip['month_dt'] = pd.to_datetime(df_sip['month'])
plt.plot(df_sip['month_dt'], df_sip['sip_inflow_crore'], marker='o', color='teal', linewidth=2)
# Annotate the peak in Dec 2025
peak_row = df_sip.loc[df_sip['sip_inflow_crore'].idxmax()]
plt.annotate(f"All-time High: ₹{peak_row['sip_inflow_crore']:,} Cr\n(Dec 2025)", 
             xy=(peak_row['month_dt'], peak_row['sip_inflow_crore']), 
             xytext=(pd.Timestamp('2024-06-01'), 25000),
             arrowprops=dict(facecolor='darkred', shrink=0.08, width=1.5, headwidth=8))
plt.title('Monthly Mutual Fund SIP Inflows (Jan 2022 - Dec 2025)')
plt.xlabel('Month')
plt.ylabel('SIP Inflow (Crore INR)')
plt.tight_layout()
plt.savefig('reports/charts/sip_inflow_trend.png', dpi=150)
plt.close()

# Chart 4: Category Inflow Heatmap
plt.figure(figsize=(14, 8))
# Pivot for heatmap
df_cat_pivot = df_cat.pivot(index='category', columns='month', values='net_inflow_crore')
# Sort categories by average net inflow
df_cat_pivot = df_cat_pivot.loc[df_cat_pivot.mean(axis=1).sort_values(ascending=False).index]
sns.heatmap(df_cat_pivot, cmap='RdYlGn', center=0, annot=False, cbar_kws={'label': 'Net Inflow (Crore INR)'})
plt.title('Monthly Net Inflows by Mutual Fund Category (Jan 2022 - Dec 2025)')
plt.xlabel('Month')
plt.ylabel('SEBI Category')
plt.tight_layout()
plt.savefig('reports/charts/category_inflows_heatmap.png', dpi=150)
plt.close()

# Chart 5: Investor Age Group Distribution Pie Chart
plt.figure(figsize=(8, 8))
age_counts = df_tx['age_group'].value_counts()
plt.pie(age_counts, labels=age_counts.index, autopct='%1.1f%%', startangle=140, 
        colors=sns.color_palette('pastel')[0:len(age_counts)])
plt.title('Investor Age Group Distribution')
plt.tight_layout()
plt.savefig('reports/charts/age_distribution_pie.png', dpi=150)
plt.close()

# Chart 6: SIP Amount Box Plot by Age Group
plt.figure(figsize=(10, 6))
df_sip_tx = df_tx[df_tx['transaction_type'] == 'SIP']
sns.boxplot(data=df_sip_tx, x='age_group', y='amount_inr', palette='Set2')
plt.yscale('log') # Log scale since transaction amounts vary heavily
plt.title('Monthly SIP Transaction Amount Distribution by Age Group')
plt.xlabel('Age Group')
plt.ylabel('SIP Amount (INR, Log Scale)')
plt.tight_layout()
plt.savefig('reports/charts/sip_amount_by_age_boxplot.png', dpi=150)
plt.close()

# Chart 7: Gender Split in Transactions
plt.figure(figsize=(7, 7))
gender_counts = df_tx['gender'].value_counts()
plt.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90, 
        colors=['lightblue', 'lightpink'])
plt.title('Investor Gender Split')
plt.tight_layout()
plt.savefig('reports/charts/gender_split_pie.png', dpi=150)
plt.close()

# Chart 8: Horizontal Bar Chart of SIP Amount by State
plt.figure(figsize=(10, 8))
state_sip = df_sip_tx.groupby('state')['amount_inr'].sum().reset_index()
state_sip = state_sip.sort_values('amount_inr', ascending=False)
sns.barplot(data=state_sip, x='amount_inr', y='state', palette='viridis')
plt.title('Total SIP Investments by State')
plt.xlabel('Total Invested (INR)')
plt.ylabel('State')
plt.tight_layout()
plt.savefig('reports/charts/sip_by_state.png', dpi=150)
plt.close()

# Chart 9: T30 vs B30 City Tier Pie Chart
plt.figure(figsize=(7, 7))
tier_counts = df_tx['city_tier'].value_counts()
plt.pie(tier_counts, labels=['T30 (Top 30 Cities)', 'B30 (Beyond Top 30)'], autopct='%1.1f%%', startangle=120, 
        colors=['#4f81bd', '#c0504d'])
plt.title('T30 vs B30 Investor Split')
plt.tight_layout()
plt.savefig('reports/charts/city_tier_split_pie.png', dpi=150)
plt.close()

# Chart 10: Folio Count Growth Line Chart
plt.figure(figsize=(12, 6))
df_folio['month_dt'] = pd.to_datetime(df_folio['month'])
plt.plot(df_folio['month_dt'], df_folio['total_folios_crore'], marker='s', color='navy', linewidth=2.5, label='Total Folios')
plt.plot(df_folio['month_dt'], df_folio['equity_folios_crore'], marker='o', color='green', linewidth=1.5, label='Equity Folios')
plt.plot(df_folio['month_dt'], df_folio['debt_folios_crore'], marker='^', color='red', linewidth=1.5, label='Debt Folios')

# Mark milestones
plt.axvline(pd.Timestamp('2024-03-01'), color='grey', linestyle='--', alpha=0.7)
plt.text(pd.Timestamp('2024-03-15'), 20, '20 Cr Folios Crossed\n(Mar 2024)', fontsize=10, color='indigo')

plt.title('Growth of Mutual Fund Folio Counts (Jan 2022 - Dec 2025)')
plt.xlabel('Month')
plt.ylabel('Folios (Crores)')
plt.legend()
plt.tight_layout()
plt.savefig('reports/charts/folio_count_growth.png', dpi=150)
plt.close()

# Chart 11: NAV Return Correlation Matrix Heatmap
# Calculate daily returns for 10 selected funds
selected_funds = df_fund['amfi_code'].head(10).tolist()
df_nav_selected = df_nav[df_nav['amfi_code'].isin(selected_funds)].pivot(index='date', columns='amfi_code', values='nav')
df_returns = df_nav_selected.pct_change().dropna()
# Rename columns to scheme names
name_map = dict(zip(df_fund['amfi_code'], df_fund['scheme_name'].str.split(' - ').str[0]))
df_returns.columns = [name_map.get(c, str(c)) for c in df_returns.columns]

plt.figure(figsize=(12, 10))
corr = df_returns.corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1)
plt.title('Daily NAV Return Correlation Matrix (10 Selected Funds)')
plt.tight_layout()
plt.savefig('reports/charts/nav_returns_correlation.png', dpi=150)
plt.close()

# Chart 12: Sector Allocation Donut Chart
plt.figure(figsize=(9, 9))
sector_weights = df_port.groupby('sector')['weight_pct'].sum().reset_index()
sector_weights = sector_weights.sort_values('weight_pct', ascending=False).head(8) # Top 8 sectors
# Add 'Others' category for remaining sectors
remaining_weight = df_port['weight_pct'].sum() - sector_weights['weight_pct'].sum()
if remaining_weight > 0:
    sector_weights = pd.concat([sector_weights, pd.DataFrame([{'sector': 'Others/Cash', 'weight_pct': remaining_weight}])], ignore_index=True)

plt.pie(sector_weights['weight_pct'], labels=sector_weights['sector'], autopct='%1.1f%%', startangle=90,
        pctdistance=0.85, colors=sns.color_palette('tab10'))
# Draw inner circle to make it a donut
centre_circle = plt.Circle((0,0),0.70,fc='white')
fig = plt.gcf()
fig.gca().add_artist(centre_circle)
plt.title('Aggregate Sector Allocation Across Equity Funds')
plt.tight_layout()
plt.savefig('reports/charts/sector_allocation_donut.png', dpi=150)
plt.close()

# Chart 13: Morningstar Star Rating Distribution
plt.figure(figsize=(8, 5))
sns.countplot(data=df_perf, x='morningstar_rating', palette='Blues_r')
plt.title('Morningstar Rating Distribution of Schemes')
plt.xlabel('Morningstar Star Rating')
plt.ylabel('Number of Schemes')
plt.tight_layout()
plt.savefig('reports/charts/morningstar_ratings.png', dpi=150)
plt.close()

# Chart 14: Expense Ratio vs 3-Year Returns Scatter Plot
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df_perf, x='expense_ratio_pct', y='return_3yr_pct', hue='category', style='plan', s=100, palette='Set1')
plt.title('Mutual Fund Expense Ratio vs. 3-Year Returns')
plt.xlabel('Expense Ratio (%)')
plt.ylabel('3-Year CAGR Return (%)')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('reports/charts/expense_vs_return.png', dpi=150)
plt.close()

# Chart 15: Risk Category vs Category Cross-tab Heatmap
plt.figure(figsize=(8, 6))
crosstab = pd.crosstab(df_fund['risk_category'], df_fund['category'])
sns.heatmap(crosstab, annot=True, cmap='Blues', fmt='d', cbar=False)
plt.title('Scheme Count by Risk Category and Asset Category')
plt.ylabel('Risk Category')
plt.xlabel('Asset Category')
plt.tight_layout()
plt.savefig('reports/charts/risk_vs_category_heatmap.png', dpi=150)
plt.close()

print("All 15 static charts generated successfully.")
