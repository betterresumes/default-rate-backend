#!/usr/bin/env python3
"""
Railway CLI Setup and Log Monitoring Guide
"""

import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path

class RailwayLogsMonitor:
    def __init__(self):
        self.log_file = f"railway_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def check_railway_cli(self) -> bool:
        """Check if Railway CLI is installed"""
        try:
            result = subprocess.run(['railway', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Railway CLI found: {result.stdout.strip()}")
                return True
            else:
                print("❌ Railway CLI not found")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Railway CLI not installed or not in PATH")
            return False
    
    def install_railway_cli(self):
        """Install Railway CLI"""
        print("🔧 Installing Railway CLI...")
        
        # For macOS/Linux
        install_cmd = "curl -fsSL https://railway.app/install.sh | sh"
        
        try:
            subprocess.run(install_cmd, shell=True, check=True)
            print("✅ Railway CLI installed successfully")
            print("🔄 Please restart your terminal and run this script again")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Railway CLI: {e}")
            return False
    
    def login_to_railway(self):
        """Login to Railway"""
        print("🔐 Logging into Railway...")
        print("This will open a browser window for authentication")
        
        try:
            result = subprocess.run(['railway', 'login'], timeout=60)
            if result.returncode == 0:
                print("✅ Successfully logged into Railway")
                return True
            else:
                print("❌ Railway login failed")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ Railway login timed out")
            return False
    
    def monitor_logs(self, duration_minutes: int = 10):
        """Monitor Railway logs in real-time"""
        print(f"📡 Starting log monitoring for {duration_minutes} minutes...")
        print(f"💾 Logs will be saved to: {self.log_file}")
        print("-" * 50)
        
        try:
            # Start railway logs command
            process = subprocess.Popen(
                ['railway', 'logs', '--follow'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)
            
            log_entries = []
            
            while time.time() < end_time:
                output = process.stdout.readline()
                if output:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"[{timestamp}] {output.strip()}"
                    
                    print(log_line)
                    log_entries.append(log_line)
                
                # Check if process is still running
                if process.poll() is not None:
                    break
            
            # Save logs to file
            if log_entries:
                with open(self.log_file, 'w') as f:
                    f.write("\n".join(log_entries))
                print(f"\n💾 Logs saved to: {self.log_file}")
            
            # Terminate the process
            process.terminate()
            process.wait(timeout=5)
            
        except KeyboardInterrupt:
            print("\n🛑 Log monitoring interrupted by user")
            if process:
                process.terminate()
        except Exception as e:
            print(f"❌ Error monitoring logs: {e}")

def print_setup_instructions():
    """Print Railway CLI setup instructions"""
    print("🚂 RAILWAY CLI SETUP INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1️⃣  INSTALL RAILWAY CLI:")
    print("   macOS/Linux:")
    print("   curl -fsSL https://railway.app/install.sh | sh")
    print()
    print("   Windows:")
    print("   iwr -useb https://railway.app/install.ps1 | iex")
    print()
    print("2️⃣  LOGIN TO RAILWAY:")
    print("   railway login")
    print()
    print("3️⃣  CONNECT TO YOUR PROJECT:")
    print("   railway project connect default-rate-backend-production")
    print()
    print("4️⃣  MONITOR LOGS:")
    print("   railway logs --follow")
    print()
    print("5️⃣  USEFUL COMMANDS:")
    print("   railway status          # Check deployment status")
    print("   railway ps              # List running services")
    print("   railway logs -n 100     # Show last 100 log lines")
    print("   railway logs --tail     # Follow logs in real-time")
    print("   railway env             # Show environment variables")
    print()
    print("🎯 FOR PERFORMANCE TESTING:")
    print("   1. Run: python3 railway_logs_monitor.py")
    print("   2. In another terminal: python3 railway_performance_test.py")
    print("   3. Monitor logs in real-time while tests run")
    print()

def main():
    """Main function"""
    print_setup_instructions()
    
    monitor = RailwayLogsMonitor()
    
    if monitor.check_railway_cli():
        print("✅ Railway CLI is ready!")
        print("\n🎯 Would you like to start log monitoring? (y/n): ", end="")
        if input().lower().startswith('y'):
            print("🔐 Make sure you're logged in and connected to your project")
            print("Press Enter to continue or Ctrl+C to cancel...")
            input()
            monitor.monitor_logs(duration_minutes=15)
    else:
        print("\n❌ Please install Railway CLI first using the instructions above")

if __name__ == "__main__":
    main()
