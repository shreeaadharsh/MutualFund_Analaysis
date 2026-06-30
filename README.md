# 📊 Mutual Fund Analytics

> A comprehensive end-to-end Mutual Fund data analytics project using Python, SQL, Pandas, Plotly, and Streamlit/Dash.

---

## 🗂️ Project Structure

```
mf proj/
├── data/
│   ├── raw/            # Original CSVs + live API data
│   └── processed/      # Cleaned & type-cast datasets
├── notebooks/          # Jupyter EDA notebooks
├── sql/                # SQL queries and schema
├── dashboard/          # Plotly/Streamlit dashboard files
├── reports/            # Auto-generated analysis reports
├── scripts/            # Utility / helper scripts
├── data_ingestion.py   # Day 1: Load & validate all 10 datasets
├── live_nav_fetch.py   # Day 1: Live NAV from mfapi.in
└── requirements.txt    # Python dependencies
```

---

## 📦 Datasets

| # | File | Rows | Description |
|---|------|------|-------------|
| 01 | `fund_master.csv` | 41 | Scheme metadata — AMFI codes, fund houses, categories |
| 02 | `nav_history.csv` | ~46,001 | Daily NAV records per scheme |
| 03 | `aum_by_fund_house.csv` | 91 | Bi-annual AUM figures per fund house |
| 04 | `monthly_sip_inflows.csv` | 49 | Industry-wide monthly SIP inflow statistics |
| 05 | `category_inflows.csv` | 145 | Monthly net inflows by category |
| 06 | `industry_folio_count.csv` | 22 | Quarterly folio count breakdown |
| 07 | `scheme_performance.csv` | 41 | Risk-adjusted returns, alpha, beta, Sharpe |
| 08 | `investor_transactions.csv` | ~32,779 | Individual investor transaction records |
| 09 | `portfolio_holdings.csv` | ~323 | Scheme-level stock holdings |
| 10 | `benchmark_indices.csv` | ~8,051 | Daily NIFTY / BSE index levels |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd "mf proj"

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate       # Windows
# source venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run data ingestion (Day 1)
python data_ingestion.py

# 5. Fetch live NAV data
python live_nav_fetch.py
```

---

## 📅 Project Roadmap

| Day | Focus | Status |
|-----|-------|--------|
| 1 | Data Ingestion + ETL | ✅ Complete |
| 2 | EDA + Visualisations | 🔜 |
| 3 | SQL Analytics | 🔜 |
| 4 | Performance Metrics | 🔜 |
| 5 | Risk Analysis | 🔜 |
| 6 | Dashboard | 🔜 |
| 7 | Reporting | 🔜 |

---

## 🔑 Key APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| mfapi.in | `GET https://api.mfapi.in/mf/{code}` | Free, real-time NAV data |

---

## 📝 Author

Mutual Fund Analytics Project — 2024–2026
