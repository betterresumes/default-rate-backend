#!/usr/bin/env python3

import json, pandas as pd, io, base64
from app.core.database import get_session_local, BulkUploadJob

def debug_job():
    db = get_session_local()()
    
    try:
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == '888f39e4-0748-4b79-846f-b0adeec5294a').first()
        
        if not job:
            print("❌ Job not found!")
            return
            
        print(f"✅ Job found: {job.id}")
        print(f"📄 Filename: {job.original_filename}")
        print(f"📊 Status: {job.status}")
        print(f"🔢 Total rows: {job.total_rows}")
        
        if not job.file_data:
            print("❌ No file_data in job!")
            return
            
        print(f"💾 File data length: {len(job.file_data)} bytes")
        
        # Try to decode and process the file
        try:
            file_content = base64.b64decode(job.file_data)
            print(f"✅ Base64 decoded: {len(file_content)} bytes")
            
            df = pd.read_excel(io.BytesIO(file_content))
            print(f"✅ Excel loaded: {len(df)} rows, {len(df.columns)} columns")
            print(f"📋 Columns: {list(df.columns)}")
            
            # Convert to records format (same as API does)
            data = df.to_dict('records')
            print(f"✅ Data converted: {len(data)} records")
            
            if len(data) > 0:
                first_row = data[0]
                print(f"🔍 First row keys: {list(first_row.keys())}")
                print(f"🔍 First row sample:")
                for key, value in first_row.items():
                    print(f"   {key}: {value}")
            else:
                print("❌ Data is EMPTY after conversion!")
                
        except Exception as e:
            print(f"❌ Error processing file data: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_job()