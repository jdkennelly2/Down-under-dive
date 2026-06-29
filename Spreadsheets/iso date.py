import pandas as pd
import os

# Define the exact file path
file_path = r'C:\Users\penny\Desktop\SQL\DOWN UNDER DIVE\Test spreadsheets\pax_all_era2.csv'

if not os.path.exists(file_path):
    print(f"❌ Error: Could not find the file at {file_path}")
else:
    try:
        # Load the CSV file
        df = pd.read_csv(file_path)
        
        # Convert dates using 'mixed' format evaluation to safely parse standard Australian formats (D/M/YYYY)
        df['date'] = pd.to_datetime(df['date'], format='mixed', dayfirst=True).dt.strftime('%Y-%m-%d')
        
        # Overwrite the file back with the clean date formats
        df.to_csv(file_path, index=False)
        print("✅ Success! All dates have been converted to standard SQL 'YYYY-MM-DD' format.")
        
        # Show a sneak peek to verify
        print("\nFirst 3 rows of updated file:")
        print(df.head(3).to_string(index=False))
        
    except Exception as e:
        print(f"❌ Something went wrong: {e}")