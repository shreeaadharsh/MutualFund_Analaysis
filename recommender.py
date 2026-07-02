# standalone Mutual Fund Recommender
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
        print(f"\nTop 3 Recommended Funds for '{risk.capitalize()}' Risk Profile:")
        print("-" * 100)
        print(df_rec.to_string(index=False))
        print("-" * 100)
    else:
        print("No schemes match the criteria.")

if __name__ == "__main__":
    main()
