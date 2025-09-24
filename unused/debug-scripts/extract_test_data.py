#!/usr/bin/env python3
"""
Extract first 250 rows from part 2 Excel files for testing bulk upload endpoints.
Creates test CSV files and curl command scripts.
"""

import pandas as pd
import json
import os
from pathlib import Path

def extract_test_data():
    """Extract first 250 rows from part 2 files and create test CSVs"""
    
    base_dir = Path(__file__).parent / "data"
    
    # File paths
    annual_file = base_dir / "bulk_upload_files" / "annual_predictions_part_2.xlsx"
    quarterly_file = base_dir / "quarterly_upload_files" / "quarterly_predictions_part_2.xlsx"
    
    # Output files
    annual_test_csv = "test_annual_250_rows.csv"
    quarterly_test_csv = "test_quarterly_250_rows.csv"
    
    print("🔄 Processing Annual Predictions Part 2...")
    
    # Process Annual Predictions Part 2
    if annual_file.exists():
        try:
            annual_df = pd.read_excel(annual_file)
            print(f"📊 Total rows in annual part 2: {len(annual_df)}")
            print(f"📋 Columns: {list(annual_df.columns)}")
            
            # Take first 250 rows
            annual_test = annual_df.head(250)
            
            # Save to CSV
            annual_test.to_csv(annual_test_csv, index=False)
            print(f"✅ Created {annual_test_csv} with {len(annual_test)} rows")
            
            # Display sample data
            print("\n📋 Annual Data Sample (first 3 rows):")
            print(annual_test.head(3).to_string())
            
        except Exception as e:
            print(f"❌ Error processing annual file: {e}")
            return False
    else:
        print(f"❌ Annual file not found: {annual_file}")
        return False
    
    print("\n" + "="*60)
    print("🔄 Processing Quarterly Predictions Part 2...")
    
    # Process Quarterly Predictions Part 2
    if quarterly_file.exists():
        try:
            quarterly_df = pd.read_excel(quarterly_file)
            print(f"📊 Total rows in quarterly part 2: {len(quarterly_df)}")
            print(f"📋 Columns: {list(quarterly_df.columns)}")
            
            # Take first 250 rows
            quarterly_test = quarterly_df.head(250)
            
            # Save to CSV
            quarterly_test.to_csv(quarterly_test_csv, index=False)
            print(f"✅ Created {quarterly_test_csv} with {len(quarterly_test)} rows")
            
            # Display sample data
            print("\n📋 Quarterly Data Sample (first 3 rows):")
            print(quarterly_test.head(3).to_string())
            
        except Exception as e:
            print(f"❌ Error processing quarterly file: {e}")
            return False
    else:
        print(f"❌ Quarterly file not found: {quarterly_file}")
        return False
    
    return True, annual_test_csv, quarterly_test_csv

def create_curl_scripts(annual_csv, quarterly_csv):
    """Create curl command scripts for bulk upload testing"""
    
    # Test users for different roles
    test_users = [
        {
            "name": "super_admin",
            "email": "admin@defaultrate.com",
            "password": "admin123",
            "description": "Super Admin - can upload system-wide data"
        },
        {
            "name": "morgan_admin", 
            "email": "risk.director@morganstanley.com",
            "password": "director123",
            "description": "Morgan Stanley Org Admin - can upload org data"
        },
        {
            "name": "jpmorgan_admin",
            "email": "analytics.head@jpmorgan.com", 
            "password": "head123",
            "description": "JPMorgan Org Admin - can upload org data"
        },
        {
            "name": "tenant_admin",
            "email": "ceo@defaultrate.com",
            "password": "ceo123", 
            "description": "Tenant Admin - can upload cross-org data"
        }
    ]
    
    # Create curl script for each user and prediction type
    for user in test_users:
        # Annual predictions curl script
        annual_script = f"""#!/bin/bash
# Bulk Upload Test Script - Annual Predictions
# User: {user['description']}
# File: {annual_csv}

API_BASE="http://localhost:8000/api/v1"

echo "🔐 Authenticating as {user['name']} ({user['email']})..."

# Get access token
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username={user['email']}" \\
  -d "password={user['password']}" \\
  -d "grant_type=password")

# Extract token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Authentication failed!"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo "🚀 Starting bulk upload for annual predictions..."

# Upload annual predictions
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/predictions/annual/bulk-upload-async" \\
  -H "Authorization: Bearer $ACCESS_TOKEN" \\
  -F "file=@{annual_csv}")

echo "📊 Upload Response:"
echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

# Extract job_id for status checking
JOB_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ ! -z "$JOB_ID" ]; then
    echo "\\n🔍 Checking job status..."
    sleep 2
    
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/predictions/jobs/$JOB_ID/status" \\
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "📋 Job Status:"
    echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"
fi

echo "\\n✅ Annual bulk upload test completed for {user['name']}!"
"""
        
        # Quarterly predictions curl script
        quarterly_script = f"""#!/bin/bash
# Bulk Upload Test Script - Quarterly Predictions  
# User: {user['description']}
# File: {quarterly_csv}

API_BASE="http://localhost:8000/api/v1"

echo "🔐 Authenticating as {user['name']} ({user['email']})..."

# Get access token
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username={user['email']}" \\
  -d "password={user['password']}" \\
  -d "grant_type=password")

# Extract token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Authentication failed!"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo "🚀 Starting bulk upload for quarterly predictions..."

# Upload quarterly predictions
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/predictions/quarterly/bulk-upload-async" \\
  -H "Authorization: Bearer $ACCESS_TOKEN" \\
  -F "file=@{quarterly_csv}")

echo "📊 Upload Response:"
echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

# Extract job_id for status checking
JOB_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ ! -z "$JOB_ID" ]; then
    echo "\\n🔍 Checking job status..."
    sleep 2
    
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/predictions/jobs/$JOB_ID/status" \\
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "📋 Job Status:"
    echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"
fi

echo "\\n✅ Quarterly bulk upload test completed for {user['name']}!"
"""
        
        # Write scripts to files
        annual_script_file = f"curl_annual_{user['name']}.sh"
        quarterly_script_file = f"curl_quarterly_{user['name']}.sh"
        
        with open(annual_script_file, 'w') as f:
            f.write(annual_script)
        
        with open(quarterly_script_file, 'w') as f:
            f.write(quarterly_script)
        
        # Make scripts executable
        os.chmod(annual_script_file, 0o755)
        os.chmod(quarterly_script_file, 0o755)
        
        print(f"✅ Created {annual_script_file}")
        print(f"✅ Created {quarterly_script_file}")

def main():
    """Main execution"""
    print("🚀 Excel Data Extraction and Curl Script Generator")
    print("="*60)
    
    # Extract test data
    result = extract_test_data()
    
    if result and len(result) == 3:
        success, annual_csv, quarterly_csv = result
        
        if success:
            print("\\n" + "="*60)
            print("🔧 Creating Curl Scripts...")
            
            create_curl_scripts(annual_csv, quarterly_csv)
            
            print("\\n" + "="*60)
            print("✅ All files created successfully!")
            print("\\n📁 Generated Files:")
            print(f"   📊 {annual_csv} - Annual test data (250 rows)")
            print(f"   📊 {quarterly_csv} - Quarterly test data (250 rows)")
            print("   📝 curl_annual_[user].sh - Annual upload scripts for each user")
            print("   📝 curl_quarterly_[user].sh - Quarterly upload scripts for each user")
            
            print("\\n🧪 To test bulk uploads:")
            print("   1. Start your API server: uvicorn main:app --reload")
            print("   2. Run any curl script: ./curl_annual_super_admin.sh")
            print("   3. Check job status and results")
            
        else:
            print("❌ Failed to extract test data")
    else:
        print("❌ Failed to process files")

if __name__ == "__main__":
    main()
