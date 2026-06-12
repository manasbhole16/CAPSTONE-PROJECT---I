import pandas as pd

def explore_and_validate():
    print("Loading datasets for validation...\n")
    
    # Load the specific datasets needed for Phase 4
    try:
        fund_master = pd.read_csv('data/raw/01_fund_master.csv')
        nav_history = pd.read_csv('data/raw/02_nav_history.csv')
    except FileNotFoundError as e:
        print(f"Error loading files. Make sure they are in data/raw/ - {e}")
        return

    print("="*50)
    print("📊 FUND MASTER EXPLORATION")
    print("="*50)
    
    # Print unique values as requested by the task
    print("\n📌 Unique Fund Houses:")
    print(fund_master['fund_house'].unique())
    
    print("\n📌 Unique Categories:")
    print(fund_master['category'].unique())
    
    print("\n📌 Unique Sub-categories:")
    print(fund_master['sub_category'].unique())
    
    print("\n📌 Unique Risk Grades:")
    print(fund_master['risk_category'].unique())

    print("\n" + "="*50)
    print("🔍 AMFI CODE VALIDATION")
    print("="*50)
    
    # Extract unique AMFI codes into Python Sets for fast comparison
    master_codes = set(fund_master['amfi_code'].dropna().unique())
    nav_codes = set(nav_history['amfi_code'].dropna().unique())
    
    print(f"Total unique AMFI codes in Fund Master: {len(master_codes)}")
    print(f"Total unique AMFI codes in NAV History: {len(nav_codes)}")
    
    # Check if every code in fund_master exists in nav_history
    missing_in_nav = master_codes - nav_codes
    
    if not missing_in_nav:
        print("\n✅ VALIDATION PASSED: Every AMFI code in fund_master exists in nav_history.")
    else:
        print(f"\n⚠️ VALIDATION WARNING: {len(missing_in_nav)} AMFI codes in fund_master are MISSING from nav_history.")
        # Print the first few missing codes as an example
        print(f"Sample missing codes: {list(missing_in_nav)[:5]}")

if __name__ == "__main__":
    explore_and_validate()