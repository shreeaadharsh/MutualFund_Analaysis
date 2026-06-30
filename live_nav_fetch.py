"""
==============================================================================
Mutual Fund Analytics - Day 1
File: live_nav_fetch.py
Purpose: Fetch live NAV data from mfapi.in for 6 key schemes,
         parse JSON responses, and persist as raw CSV files.

API: https://api.mfapi.in/mf/{scheme_code}
Docs: https://www.mfapi.in/
==============================================================================
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime

# Force UTF-8 output on Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ==============================================================================
# CONFIGURATION
# ==============================================================================

DATA_RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
os.makedirs(DATA_RAW_DIR, exist_ok=True)

BASE_URL = "https://api.mfapi.in/mf/{code}"

# 6 key schemes: HDFC Top 100 Direct (Task 4) + 5 Bluechip/Large Cap (Task 5)
KEY_SCHEMES = {
    125497: "HDFC Top 100 Fund - Direct Plan - Growth",
    119551: "SBI Bluechip Fund - Regular Plan - Growth",
    120503: "ICICI Pru Bluechip Fund - Regular - Growth",
    118632: "Nippon India Large Cap Fund - Regular - Growth",
    119092: "Axis Bluechip Fund - Regular - Growth",
    120841: "Kotak Bluechip Fund - Regular - Growth",
}

REQUEST_TIMEOUT = 15
RETRY_ATTEMPTS  = 3
RETRY_DELAY     = 2

SEP  = "=" * 80
SEP2 = "-" * 60


# ==============================================================================
# HELPERS
# ==============================================================================

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def subsection(title):
    print(f"\n{SEP2}\n  {title}\n{SEP2}")


def fetch_nav(scheme_code):
    """
    Fetch NAV JSON from mfapi.in with retry/back-off.
    Returns parsed dict on success, None on failure.
    """
    url = BASE_URL.format(code=scheme_code)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            print(f"    Attempt {attempt}/{RETRY_ATTEMPTS}  ->  GET {url}")
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            record_count = len(data.get("data", []))
            print(f"    [OK] HTTP {resp.status_code} -- {record_count:,} NAV records returned")
            return data
        except requests.exceptions.HTTPError as e:
            print(f"    [ERROR] HTTP Error: {e}")
        except requests.exceptions.ConnectionError:
            print("    [ERROR] Connection Error -- check network/DNS")
        except requests.exceptions.Timeout:
            print(f"    [ERROR] Timeout after {REQUEST_TIMEOUT}s")
        except (json.JSONDecodeError, ValueError):
            print("    [ERROR] Invalid JSON in response")

        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_DELAY * attempt
            print(f"    Retrying in {wait}s ...")
            time.sleep(wait)

    return None


def parse_nav_response(code, data):
    """
    Parse raw mfapi.in response into a clean DataFrame.

    Expected JSON structure:
    {
      "meta": { "fund_house": ..., "scheme_type": ..., "scheme_name": ... },
      "data": [ { "date": "DD-MM-YYYY", "nav": "123.456" }, ... ]
    }
    """
    if not data or "data" not in data:
        print("    [ERROR] No 'data' key in response -- skipping")
        return None

    meta    = data.get("meta", {})
    records = data["data"]

    if not records:
        print("    [ERROR] Empty data array -- no NAV records")
        return None

    df = pd.DataFrame(records)
    df.rename(columns={"date": "nav_date", "nav": "nav_value"}, inplace=True)

    df["nav_date"]        = pd.to_datetime(df["nav_date"], format="%d-%m-%Y", errors="coerce")
    df["nav_value"]       = pd.to_numeric(df["nav_value"], errors="coerce")
    df["amfi_code"]       = code
    df["scheme_name"]     = meta.get("scheme_name", "")
    df["fund_house"]      = meta.get("fund_house",  "")
    df["scheme_type"]     = meta.get("scheme_type", "")
    df["scheme_category"] = meta.get("scheme_category", "")
    df["fetched_at"]      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df.sort_values("nav_date", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    null_nav = df["nav_value"].isna().sum()
    if null_nav > 0:
        print(f"    [WARN] {null_nav} unparseable NAV value(s) set to NaN")

    return df


def save_nav_csv(code, df):
    """Save fetched NAV DataFrame to data/raw/."""
    filename  = f"live_nav_{code}.csv"
    file_path = os.path.join(DATA_RAW_DIR, filename)
    df.to_csv(file_path, index=False)
    return file_path


# ==============================================================================
# MAIN FETCH PIPELINE
# ==============================================================================

def fetch_all_schemes():
    section("LIVE NAV FETCH -- mfapi.in")
    print(f"  Fetching {len(KEY_SCHEMES)} schemes ...\n")

    results = {}

    for code, friendly_name in KEY_SCHEMES.items():
        subsection(f"Code: {code}  |  {friendly_name}")

        raw_data = fetch_nav(code)

        if raw_data is None:
            print(f"    [FAILED] Could not fetch data for scheme {code}")
            results[code] = {"status": "FAILED", "records": 0, "file": None}
            continue

        df = parse_nav_response(code, raw_data)

        if df is None:
            results[code] = {"status": "FAILED", "records": 0, "file": None}
            continue

        file_path    = save_nav_csv(code, df)
        latest_nav   = df["nav_value"].iloc[-1]
        earliest_nav = df["nav_value"].iloc[0]
        total_return = round(((latest_nav - earliest_nav) / earliest_nav) * 100, 2)

        print(f"\n    ---- Summary ----------------------------------------")
        print(f"    Records        : {len(df):,}")
        print(f"    Date Range     : {df['nav_date'].min().date()}  to  {df['nav_date'].max().date()}")
        print(f"    Latest NAV     : Rs. {latest_nav:.4f}")
        print(f"    Earliest NAV   : Rs. {earliest_nav:.4f}")
        print(f"    Total Return   : {total_return:+.2f}% (full history from API)")
        print(f"    Saved to       : {file_path}")

        results[code] = {
            "status"      : "SUCCESS",
            "scheme_name" : df["scheme_name"].iloc[0],
            "fund_house"  : df["fund_house"].iloc[0],
            "records"     : len(df),
            "min_date"    : str(df["nav_date"].min().date()),
            "max_date"    : str(df["nav_date"].max().date()),
            "latest_nav"  : latest_nav,
            "total_return": total_return,
            "file"        : file_path,
        }

        # Polite delay between requests
        time.sleep(0.5)

    return results


def print_summary(results):
    section("FETCH SUMMARY")

    success = [k for k, v in results.items() if v["status"] == "SUCCESS"]
    failed  = [k for k, v in results.items() if v["status"] == "FAILED"]

    print(f"\n  [OK]   Successful : {len(success)} / {len(results)}")
    if failed:
        print(f"  [FAIL] Failed     : {len(failed)} -- codes: {failed}")

    header = f"\n  {'Code':<10} {'Scheme':<52} {'Records':>8}  {'Latest NAV':>12}  {'Return':>10}"
    print(header)
    print("  " + "-" * 98)

    for code, info in results.items():
        if info["status"] == "SUCCESS":
            name = KEY_SCHEMES[code][:50]
            print(
                f"  {code:<10} {name:<52} {info['records']:>8,}"
                f"  Rs.{info['latest_nav']:>9.4f}  {info['total_return']:>+9.2f}%"
            )
        else:
            print(f"  {code:<10} {'FETCH FAILED':<52}")

    # Save consolidated summary CSV
    summary_df = pd.DataFrame([
        {
            "amfi_code"   : code,
            "scheme_name" : v.get("scheme_name", KEY_SCHEMES.get(code, "")),
            "fund_house"  : v.get("fund_house", ""),
            "status"      : v["status"],
            "records"     : v["records"],
            "min_date"    : v.get("min_date", ""),
            "max_date"    : v.get("max_date", ""),
            "latest_nav"  : v.get("latest_nav"),
            "total_return": v.get("total_return"),
        }
        for code, v in results.items()
    ])

    summary_path = os.path.join(DATA_RAW_DIR, "live_nav_fetch_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"\n  [OK] Summary saved -> {summary_path}")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main():
    print(SEP)
    print("  MUTUAL FUND ANALYTICS -- DAY 1: LIVE NAV FETCH")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    results = fetch_all_schemes()
    print_summary(results)

    section("DONE")
    print("  All live NAV files saved to data/raw/\n")


if __name__ == "__main__":
    main()
