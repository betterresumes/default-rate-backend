#!/usr/bin/env python3
"""
Railway Logs Monitor
Monitor and capture logs from Railway deployment during performance testing
"""

import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

class RailwayLogsMonitor:
    def __init__(self, service_name: str = None):
        self.service_name = service_name
        self.log_entries = []
        self.start_time = datetime.now()
    
    def check_railway_cli(self):
        """Check if Railway CLI is installed"""
        try:
            result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Railway CLI found: {result.stdout.strip()}")
                return True
            else:
                print("❌ Railway CLI not found")
                return False
        except FileNotFoundError:
            print("❌ Railway CLI not installed")
            return False
    
    def login_check(self):
        """Check if logged into Railway"""
        try:
            result = subprocess.run(['railway', 'whoami'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Logged in as: {result.stdout.strip()}")
                return True
            else:
                print("❌ Not logged into Railway")
                print("Please run: railway login")
                return False
        except Exception as e:
            print(f"❌ Error checking login: {e}")
            return False
    
    def list_services(self):
        """List available services"""
        try:
            result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("📋 Railway Status:")
                print(result.stdout)
                return True
            else:
                print("❌ Error getting Railway status")
                return False
        except Exception as e:
            print(f"❌ Error listing services: {e}")
            return False
    
    def stream_logs(self, duration_minutes: int = 10, save_to_file: bool = True):
        """Stream logs for specified duration"""
        if not self.check_railway_cli():
            return self.manual_logs_instructions()
        
        if not self.login_check():
            return False
        
        print(f"🎯 Streaming logs for {duration_minutes} minutes...")
        
        # Start log streaming
        cmd = ['railway', 'logs', '--follow']
        if self.service_name:
            cmd.extend(['--service', self.service_name])
        
        log_filename = f"railway_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(log_filename, 'w') as log_file:
                log_file.write(f"Railway Logs - Started: {datetime.now()}\n")
                log_file.write("=" * 80 + "\n\n")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                start_time = time.time()
                end_time = start_time + (duration_minutes * 60)
                
                print(f"📝 Saving logs to: {log_filename}")
                print("🔴 Log stream started (press Ctrl+C to stop early)...")
                
                while time.time() < end_time:
                    output = process.stdout.readline()
                    if output:
                        log_entry = f"[{datetime.now()}] {output.strip()}"
                        print(output.strip())
                        log_file.write(log_entry + "\n")
                        log_file.flush()
                    
                    if process.poll() is not None:
                        break
                    
                    time.sleep(0.1)
                
                process.terminate()
                log_file.write(f"\nLog stream ended: {datetime.now()}\n")
                
                print(f"✅ Logs saved to: {log_file.name}")
                return log_filename
                
        except KeyboardInterrupt:
            print("\n⏹️  Log streaming stopped by user")
            return log_filename
        except Exception as e:
            print(f"❌ Error streaming logs: {e}")
            return None
    
    def manual_logs_instructions(self):
        """Provide manual instructions for accessing logs"""
        print("\n📚 MANUAL RAILWAY LOGS ACCESS INSTRUCTIONS:")
        print("=" * 60)
        print("Since Railway CLI is not available, please access logs manually:")
        print()
        print("🌐 Option 1: Railway Dashboard")
        print("   1. Go to https://railway.app/dashboard")
        print("   2. Select your project")
        print("   3. Click on your service")
        print("   4. Go to 'Observability' tab")
        print("   5. View real-time logs")
        print()
        print("💻 Option 2: Install Railway CLI")
        print("   1. npm install -g @railway/cli")
        print("   2. railway login")
        print("   3. railway logs --follow")
        print()
        print("📊 What to look for in logs during testing:")
        print("   - Job creation messages")
        print("   - Processing start/end times")
        print("   - Row processing rates")
        print("   - Error messages")
        print("   - Database operations")
        print("   - Celery worker activity")
        print()
        return False

def main():
    print("🚂 RAILWAY LOGS MONITORING FOR PERFORMANCE TESTING")
    print("=" * 60)
    
    monitor = RailwayLogsMonitor()
    
    # Check if we can use Railway CLI
    if monitor.check_railway_cli() and monitor.login_check():
        print("\n🎯 Ready to monitor logs!")
        
        # List available services
        monitor.list_services()
        
        # Ask for monitoring duration
        try:
            duration = int(input("\nEnter monitoring duration in minutes (default 15): ") or "15")
        except ValueError:
            duration = 15
        
        print(f"\n🚀 Starting log monitoring for {duration} minutes...")
        print("💡 Run your performance tests in another terminal now!")
        print("   cd /path/to/your/backend")
        print("   python3 manual_performance_test.py")
        
        input("\nPress Enter when ready to start monitoring...")
        
        # Start monitoring
        log_file = monitor.stream_logs(duration)
        
        if log_file:
            print(f"\n✅ Monitoring complete! Logs saved to: {log_file}")
            print("\n📊 Analyze the logs for:")
            print("   - Job processing times")
            print("   - Database query performance")
            print("   - Celery worker efficiency")
            print("   - Memory usage patterns")
            print("   - Error rates and types")
        
    else:
        # Provide manual instructions
        monitor.manual_logs_instructions()
        
        print("\n⚠️  ALTERNATIVE: Monitor logs manually during testing")
        print("1. Open Railway dashboard in browser")
        print("2. Navigate to your service logs")
        print("3. Run the performance test:")
        print("   python3 manual_performance_test.py")
        print("4. Watch logs for performance metrics")

if __name__ == "__main__":
    main()
