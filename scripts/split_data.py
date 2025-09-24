import pandas as pd
import os

# Load the Excel file
try:
    df = pd.read_excel('./data/quarterly_predictions_part_1.xlsx', sheet_name='Sheet1_Table 1')
    print(f"✅ Successfully loaded Excel file with {len(df)} rows")
except Exception as e:
    print(f"❌ Error loading Excel file: {e}")
    exit(1)

# Define the row ranges for each file (0-based index, excluding header for slicing)
ranges = [
    (0, 20),    # Rows 1–20
    (20, 40),   # Rows 21–40
    (40, 60),   # Rows 41–60
    (60, 80),   # Rows 61–80
    (80, 100)   # Rows 81–100
]

# Define file names (save to data directory)
file_names = [
    './data/others/quarterly_predictions_q1_batch.xlsx',
    './data/others/quarterly_predictions_q2_batch.xlsx',
    './data/others/quarterly_predictions_q3_batch.xlsx',
    './data/others/quarterly_predictions_q4_batch.xlsx',
    './data/others/quarterly_predictions_final_batch.xlsx'
]

# Split and save each file
for i, ((start, end), file_name) in enumerate(zip(ranges, file_names), 1):
    try:
        # Extract the subset of rows (including header)
        df_subset = df.iloc[start:end]
        # Save to Excel
        df_subset.to_excel(file_name, index=False)
        print(f"✅ Created file {i}: {file_name} ({len(df_subset)} rows)")
    except Exception as e:
        print(f"❌ Error creating file {file_name}: {e}")

print(f"\n🎉 Successfully split data into {len(file_names)} files!")