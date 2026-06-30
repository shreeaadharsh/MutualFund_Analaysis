import os
import sys
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
CHARTS_DIR = os.path.join(BASE_DIR, "reports", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Load datasets
df_aum = pd.read_csv(os.path.join(PROC_DIR, "aum_by_fund_house_clean.csv"))
df_sip = pd.read_csv(os.path.join(PROC_DIR, "monthly_sip_inflows_clean.csv"))
df_cat = pd.read_csv(os.path.join(PROC_DIR, "category_inflows_clean.csv"))
df_folio = pd.read_csv(os.path.join(PROC_DIR, "industry_folio_count_clean.csv"))
df_scorecard = pd.read_csv(os.path.join(PROC_DIR, "fund_scorecard.csv"))
df_tx = pd.read_csv(os.path.join(PROC_DIR, "investor_transactions_clean.csv"))
df_perf = pd.read_csv(os.path.join(PROC_DIR, "scheme_performance_clean.csv"))
df_bench = pd.read_csv(os.path.join(PROC_DIR, "benchmark_indices_clean.csv"))

# Parse dates for time series
df_bench['date'] = pd.to_datetime(df_bench['date'])

# Merge aum_crore into scorecard
df_scorecard = pd.merge(df_scorecard, df_perf[['amfi_code', 'aum_crore']], on='amfi_code', how='left')

# Theme colors (Bluestock theme: Navy/Slate/Cyan/Teal)
C_BG = "#0f172a"        # Dark slate background
C_CARD = "#1e293b"      # Card background
C_TEXT = "#f8fafc"      # White text
C_PRIMARY = "#3b82f6"   # Soft blue
C_ACCENT = "#06b6d4"    # Cyan
C_TEAL = "#14b8a6"      # Teal
C_MUTED = "#64748b"     # Grey text

plt.rcParams['text.color'] = C_TEXT
plt.rcParams['axes.labelcolor'] = C_TEXT
plt.rcParams['xtick.color'] = C_TEXT
plt.rcParams['ytick.color'] = C_TEXT
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'

# ==============================================================================
# PAGE 1: INDUSTRY OVERVIEW
# ==============================================================================

fig = plt.figure(figsize=(16, 10), facecolor=C_BG)
gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.4, wspace=0.3)

# Title Header
fig.text(0.05, 0.95, "BLUESTOCK MUTUAL FUND ANALYTICS", fontsize=18, fontweight='bold', color=C_ACCENT)
fig.text(0.05, 0.91, "Page 1: Industry Overview & Market Growth", fontsize=14, color=C_TEXT)

# KPI Cards
kpis = [
    ("Total Industry AUM", "₹81.5L Cr", "+14.2% YoY"),
    ("Monthly SIP Inflows", "₹31,002 Cr", "All-time High"),
    ("Total Folio Count", "26.12 Cr", "Double vs 2022"),
    ("Active Schemes", "1,908", "SEBI Registered")
]

for idx, (title, val, sub) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, idx], facecolor=C_CARD)
    ax.text(0.5, 0.7, title, fontsize=12, color=C_MUTED, ha='center', va='center')
    ax.text(0.5, 0.4, val, fontsize=22, color=C_TEXT, fontweight='bold', ha='center', va='center')
    ax.text(0.5, 0.15, sub, fontsize=10, color=C_TEAL, ha='center', va='center')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)

# Chart 1: Industry AUM Growth Trend
ax1 = fig.add_subplot(gs[1:, 0:2], facecolor=C_CARD)
df_aum_grouped = df_aum.groupby('date')['aum_crore'].sum().reset_index()
df_aum_grouped['date'] = pd.to_datetime(df_aum_grouped['date'])
ax1.plot(df_aum_grouped['date'], df_aum_grouped['aum_crore'] / 100000.0, color=C_ACCENT, linewidth=3, marker='o')
ax1.fill_between(df_aum_grouped['date'], df_aum_grouped['aum_crore'] / 100000.0, color=C_ACCENT, alpha=0.15)
ax1.set_title("Industry Total AUM Trend (Lakh Crore INR)", fontsize=12, fontweight='bold', pad=15)
ax1.grid(True, color="#334155", linestyle=':')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color(C_MUTED)
ax1.spines['bottom'].set_color(C_MUTED)

# Chart 2: AUM by AMC (Latest Snapshot)
ax2 = fig.add_subplot(gs[1:, 2:4], facecolor=C_CARD)
df_latest_aum = df_aum[df_aum['date'] == df_aum['date'].max()].sort_values('aum_crore', ascending=False).head(10)
bars = ax2.barh(df_latest_aum['fund_house'].str.replace(" Mutual Fund", ""), df_latest_aum['aum_crore'] / 100000.0, color=C_PRIMARY)
ax2.invert_yaxis()
ax2.set_title("Top 10 Asset Management Companies by AUM (Lakh Cr)", fontsize=12, fontweight='bold', pad=15)
ax2.grid(True, axis='x', color="#334155", linestyle=':')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_color(C_MUTED)
ax2.spines['bottom'].set_color(C_MUTED)

# Annotate values on the bar chart
for bar in bars:
    width = bar.get_width()
    ax2.text(width + 0.2, bar.get_y() + bar.get_height()/2, f"{width:.2f}L", 
             va='center', ha='left', fontsize=9, color=C_TEXT)

plt.savefig(os.path.join(CHARTS_DIR, "Dashboard_Page1.png"), dpi=150, facecolor=C_BG)
plt.close()

# ==============================================================================
# PAGE 2: FUND PERFORMANCE
# ==============================================================================

fig = plt.figure(figsize=(16, 10), facecolor=C_BG)
gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.4, wspace=0.3)

fig.text(0.05, 0.95, "BLUESTOCK MUTUAL FUND ANALYTICS", fontsize=18, fontweight='bold', color=C_ACCENT)
fig.text(0.05, 0.91, "Page 2: Fund Risk-Return Performance", fontsize=14, color=C_TEXT)

# Left Pane: Slicers Simulation
ax_slice = fig.add_subplot(gs[0:, 0], facecolor=C_CARD)
ax_slice.text(0.1, 0.9, "FILTERS / SLICERS", fontsize=12, fontweight='bold', color=C_ACCENT)
filters = [
    ("Fund House", ["SBI Mutual Fund", "HDFC Mutual Fund", "ICICI Prudential", "Nippon India", "Kotak Mutual Fund"]),
    ("Category", ["Equity", "Debt"]),
    ("Plan", ["Direct", "Regular"])
]
y_pos = 0.75
for category, options in filters:
    ax_slice.text(0.1, y_pos, f"■ {category}", fontsize=11, fontweight='bold', color=C_TEXT)
    y_pos -= 0.04
    for opt in options[:3]:
        ax_slice.text(0.15, y_pos, f"  [x] {opt}", fontsize=9, color=C_MUTED)
        y_pos -= 0.03
    ax_slice.text(0.15, y_pos, "  ... More", fontsize=9, color=C_ACCENT)
    y_pos -= 0.06

ax_slice.set_xticks([])
ax_slice.set_yticks([])
ax_slice.spines['top'].set_visible(False)
ax_slice.spines['right'].set_visible(False)
ax_slice.spines['bottom'].set_visible(False)
ax_slice.spines['left'].set_visible(False)

# Chart 1: Return (X) vs Volatility (Y) Scatter Plot
ax_scatter = fig.add_subplot(gs[0:2, 1:4], facecolor=C_CARD)
sc = ax_scatter.scatter(
    df_scorecard['cagr_3yr_pct'], 
    df_scorecard['max_drawdown_pct'].abs(),  # Volatility / Risk proxy
    s=df_scorecard['aum_crore'] / 100, 
    c=df_scorecard['sharpe_ratio'], 
    cmap='viridis', 
    alpha=0.8, 
    edgecolors='white'
)
ax_scatter.set_title("Risk-Return Map: 3Yr Return (X) vs. Max Drawdown (Y)", fontsize=12, fontweight='bold', pad=15)
ax_scatter.set_xlabel("3-Year CAGR Return (%)")
ax_scatter.set_ylabel("Maximum Drawdown (%)")
ax_scatter.grid(True, color="#334155", linestyle=':')
ax_scatter.spines['top'].set_visible(False)
ax_scatter.spines['right'].set_visible(False)
ax_scatter.spines['left'].set_color(C_MUTED)
ax_scatter.spines['bottom'].set_color(C_MUTED)

# Add colorbar
cbar = fig.colorbar(sc, ax=ax_scatter, label="Sharpe Ratio")
cbar.ax.yaxis.label.set_color(C_TEXT)
cbar.ax.tick_params(colors=C_TEXT)

# Table: Fund Scorecard Table
ax_table = fig.add_subplot(gs[2, 1:4], facecolor=C_CARD)
ax_table.text(0.02, 0.85, "Rank  Scheme Name                                             Score   3Yr CAGR   Sharpe   Expense", fontsize=11, fontweight='bold', color=C_ACCENT)
ax_table.text(0.02, 0.78, "------------------------------------------------------------------------------------------------", color=C_MUTED)

y_offset = 0.65
for idx, row in df_scorecard.head(5).iterrows():
    name_truncated = row['scheme_name'][:50]
    line_str = f"{row['final_rank']:02d}    {name_truncated:<55} {row['composite_score']:.1f}    {row['cagr_3yr_pct']:.1f}%      {row['sharpe_ratio']:.2f}     {row['expense_ratio_pct']:.2f}%"
    ax_table.text(0.02, y_offset, line_str, fontsize=10, color=C_TEXT, fontfamily='monospace')
    y_offset -= 0.13

ax_table.set_xticks([])
ax_table.set_yticks([])
ax_table.spines['top'].set_visible(False)
ax_table.spines['right'].set_visible(False)
ax_table.spines['bottom'].set_visible(False)
ax_table.spines['left'].set_visible(False)

plt.savefig(os.path.join(CHARTS_DIR, "Dashboard_Page2.png"), dpi=150, facecolor=C_BG)
plt.close()

# ==============================================================================
# PAGE 3: INVESTOR ANALYTICS
# ==============================================================================

fig = plt.figure(figsize=(16, 10), facecolor=C_BG)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.3)

fig.text(0.05, 0.95, "BLUESTOCK MUTUAL FUND ANALYTICS", fontsize=18, fontweight='bold', color=C_ACCENT)
fig.text(0.05, 0.91, "Page 3: Retail Investor Demographics & Transaction Analytics", fontsize=14, color=C_TEXT)

# Chart 1: Donut Chart - SIP vs Lumpsum vs Redemption
ax_donut = fig.add_subplot(gs[0, 0], facecolor=C_CARD)
tx_types = df_tx['transaction_type'].value_counts()
ax_donut.pie(tx_types, labels=tx_types.index, autopct='%1.1f%%', startangle=90, pctdistance=0.75,
             colors=[C_PRIMARY, C_ACCENT, C_TEAL], textprops={'color': C_TEXT})
centre_circle = plt.Circle((0,0),0.55,fc=C_BG)
ax_donut.add_artist(centre_circle)
ax_donut.set_title("Transaction Type Share", fontsize=12, fontweight='bold', pad=15)

# Chart 2: Bar Chart - Age Group vs Avg SIP Amount
ax_age = fig.add_subplot(gs[0, 1], facecolor=C_CARD)
df_sip_tx = df_tx[df_tx['transaction_type'] == 'SIP']
age_sip = df_sip_tx.groupby('age_group')['amount_inr'].mean().reset_index()
ax_age.bar(age_sip['age_group'], age_sip['amount_inr'], color=C_TEAL)
ax_age.set_title("Average SIP Amount by Age Group", fontsize=12, fontweight='bold', pad=15)
ax_age.set_ylabel("Avg SIP Amount (INR)")
ax_age.spines['top'].set_visible(False)
ax_age.spines['right'].set_visible(False)

# Chart 3: Horizontal Bar Chart - Transaction Amount by State
ax_state = fig.add_subplot(gs[1, 0:2], facecolor=C_CARD)
state_totals = df_tx.groupby('state')['amount_inr'].sum().reset_index().sort_values('amount_inr', ascending=False).head(10)
ax_state.barh(state_totals['state'], state_totals['amount_inr'] / 10000000.0, color=C_ACCENT)
ax_state.invert_yaxis()
ax_state.set_title("Top 10 States by Total Investment Volume (Crore INR)", fontsize=12, fontweight='bold', pad=15)
ax_state.set_xlabel("Total Amount (Crore INR)")
ax_state.spines['top'].set_visible(False)
ax_state.spines['right'].set_visible(False)

# Chart 4: Monthly Transaction Volume Line
ax_line = fig.add_subplot(gs[0:, 2], facecolor=C_CARD)
df_tx['month_dt'] = pd.to_datetime(df_tx['transaction_date']).dt.strftime('%Y-%m')
tx_monthly = df_tx.groupby('month_dt').size().reset_index(name='count')
ax_line.plot(tx_monthly['month_dt'], tx_monthly['count'], color=C_PRIMARY, linewidth=3, marker='o')
ax_line.set_title("Monthly Transaction Volume", fontsize=12, fontweight='bold', pad=15)
ax_line.set_ylabel("Number of Transactions")
plt.xticks(rotation=45)
ax_line.grid(True, color="#334155", linestyle=':')
ax_line.spines['top'].set_visible(False)
ax_line.spines['right'].set_visible(False)

plt.savefig(os.path.join(CHARTS_DIR, "Dashboard_Page3.png"), dpi=150, facecolor=C_BG)
plt.close()

# ==============================================================================
# PAGE 4: SIP & MARKET TRENDS
# ==============================================================================

fig = plt.figure(figsize=(16, 10), facecolor=C_BG)
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

fig.text(0.05, 0.95, "BLUESTOCK MUTUAL FUND ANALYTICS", fontsize=18, fontweight='bold', color=C_ACCENT)
fig.text(0.05, 0.91, "Page 4: Industry SIP Trends & Category Market Inflows", fontsize=14, color=C_TEXT)

# Chart 1: Dual-axis - SIP Inflow (bar) + Nifty 50 (line)
ax_sip_bar = fig.add_subplot(gs[0, 0], facecolor=C_CARD)
df_sip['month_dt'] = pd.to_datetime(df_sip['month'])

# Align Nifty 50 prices
df_nifty = df_bench[df_bench['index_name'] == 'NIFTY50'].groupby(df_bench['date'].dt.to_period('M')).first().reset_index(drop=True)
df_nifty['month_dt'] = pd.to_datetime(df_nifty['date'])

df_merged_sip = pd.merge(df_sip, df_nifty[['month_dt', 'close_value']], on='month_dt', how='inner')

ax_sip_bar.bar(df_merged_sip['month_dt'], df_merged_sip['sip_inflow_crore'], width=20, color=C_PRIMARY, alpha=0.8, label="SIP Inflow (Cr)")
ax_sip_bar.set_ylabel("SIP Inflow (Crore INR)", color=C_PRIMARY)
ax_sip_bar.tick_params(axis='y', labelcolor=C_PRIMARY)
ax_sip_bar.set_title("Monthly SIP Inflow vs Nifty 50 Index (2022 - 2025)", fontsize=12, fontweight='bold', pad=15)

ax_nifty_line = ax_sip_bar.twinx()
ax_nifty_line.plot(df_merged_sip['month_dt'], df_merged_sip['close_value'], color=C_ACCENT, linewidth=2.5, label="Nifty 50")
ax_nifty_line.set_ylabel("Nifty 50 Close Value", color=C_ACCENT)
ax_nifty_line.tick_params(axis='y', labelcolor=C_ACCENT)
ax_nifty_line.spines['top'].set_visible(False)

# Chart 2: Top 5 Categories by Net Inflow in FY25
ax_top_cat = fig.add_subplot(gs[0, 1], facecolor=C_CARD)
df_cat_fy25 = df_cat[df_cat['month'].str.startswith('2025')].groupby('category')['net_inflow_crore'].sum().reset_index()
df_top_cat = df_cat_fy25.sort_values('net_inflow_crore', ascending=False).head(5)
ax_top_cat.bar(df_top_cat['category'], df_top_cat['net_inflow_crore'] / 1000.0, color=C_TEAL)
ax_top_cat.set_title("Top 5 Categories by Net Inflow in 2025 (Thousand Crore)", fontsize=12, fontweight='bold', pad=15)
ax_top_cat.set_ylabel("Net Inflow (Thousand Crore INR)")
plt.xticks(rotation=15)
ax_top_cat.spines['top'].set_visible(False)
ax_top_cat.spines['right'].set_visible(False)

# Chart 3: Category Inflow Heatmap
ax_heatmap = fig.add_subplot(gs[1, 0:2], facecolor=C_CARD)
df_cat_pivot = df_cat.pivot(index='category', columns='month', values='net_inflow_crore')
df_cat_pivot = df_cat_pivot.loc[df_cat_pivot.mean(axis=1).sort_values(ascending=False).index]
# Render heatmap
sns.heatmap(df_cat_pivot, cmap='RdYlGn', center=0, annot=False, ax=ax_heatmap, 
            cbar_kws={'label': 'Net Inflow (Crore INR)'})
ax_heatmap.set_title("Net Inflow Intensity Heatmap across Fund Categories (2022 - 2025)", fontsize=12, fontweight='bold', pad=15)
ax_heatmap.set_xlabel("Month")
ax_heatmap.set_ylabel("SEBI Category")

plt.savefig(os.path.join(CHARTS_DIR, "Dashboard_Page4.png"), dpi=150, facecolor=C_BG)
plt.close()

# ==============================================================================
# SAVE AS PDF
# ==============================================================================

pdf_path = os.path.join(BASE_DIR, "Dashboard.pdf")
image_files = [
    os.path.join(CHARTS_DIR, "Dashboard_Page1.png"),
    os.path.join(CHARTS_DIR, "Dashboard_Page2.png"),
    os.path.join(CHARTS_DIR, "Dashboard_Page3.png"),
    os.path.join(CHARTS_DIR, "Dashboard_Page4.png")
]

images = [Image.open(f).convert("RGB") for f in image_files]
images[0].save(pdf_path, save_all=True, append_images=images[1:])

print(f"Generated dashboard screenshots and saved combined PDF: {pdf_path}")
