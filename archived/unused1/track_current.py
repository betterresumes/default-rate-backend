#!/usr/bin/env python3
"""
Current Record Tracker
Shows exactly which record is currently being processed in the bulk script.
"""

import os
import time
from datetime import datetime

def track_current_record():
    """Track current record being processed"""
    print("📍 Current Record Tracker")
    print("=" * 40)
    
    log_files = [
        "logs/log1_main.log",
        "logs/log4_success.log", 
        "logs/log3_errors.log"
    ]
    
    print("🔄 Monitoring logs every 3 seconds...")
    print("=" * 40)
    
    last_lines = {}
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Checking logs...")
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            if lines:
                                latest_line = lines[-1].strip()
                                if log_file not in last_lines or last_lines[log_file] != latest_line:
                                    print(f"  📄 {log_file}: {latest_line}")
                                    last_lines[log_file] = latest_line
                    except Exception as e:
                        print(f"  ❌ Error reading {log_file}: {e}")
                else:
                    print(f"  📄 {log_file}: [File not found]")
            
            print("-" * 40)
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n🛑 Tracking stopped")

if __name__ == "__main__":
    track_current_record()
