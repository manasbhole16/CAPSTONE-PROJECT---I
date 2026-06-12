import requests
import pandas as pd
import os

def fetch_live_nav():
    # Dictionary of the exact scheme names and AMFI codes required for the task
    schemes = {
        "HDFC Top 100 Direct": 125497,
        "SBI Bluechip": 119551,
        "ICICI Bluechip": 120503,
        "Nippon Large Cap": 118632,
        "Axis Bluechip": 119092,
        "Kotak Bluechip": 120841
    }
    
    # Ensure the raw data directory exists just in case
    output_dir = 'data/raw/'
    os.makedirs(output_dir, exist_ok=True)

    print("Starting Live NAV Fetch via mfapi.in...\n")
    print("-" * 50)

    for name, code in schemes.items():
        print(f"📡 Fetching: {name} (AMFI Code: {code})")
        url = f"https://api.mfapi.in/mf/{code}"
        
        try:
            # Make the GET request to the API
            response = requests.get(url)
            response.raise_for_status() # Check for connection errors
            
            # Parse the JSON response
            json_data = response.json()
            
            # The API returns 'meta' and 'data'. We want the historical NAV 'data'.
            if 'data' in json_data and len(json_data['data']) > 0:
                # Convert the JSON array into a Pandas DataFrame
                df = pd.DataFrame(json_data['data'])
                
                # Save it as a raw CSV
                file_path = os.path.join(output_dir, f"{code}_live_nav.csv")
                df.to_csv(file_path, index=False)
                
                print(f"✅ Success! Saved {len(df)} days of NAV history to {file_path}\n")
            else:
                print(f"⚠️ Warning: No historical data returned for {name}\n")
                
        except Exception as e:
            print(f"❌ Error fetching {name}: {e}\n")

if __name__ == "__main__":
    fetch_live_nav()