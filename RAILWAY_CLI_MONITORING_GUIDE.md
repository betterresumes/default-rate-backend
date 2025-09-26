# Railway CLI Setup and Log Monitoring Guide

## Quick Setup

### 1. Install Railway CLI
```bash
# Install Railway CLI globally
npm install -g @railway/cli

# Or if you get permission errors:
sudo npm install -g @railway/cli
```

### 2. Login to Railway
```bash
railway login
```
This will open your browser for authentication.

### 3. Navigate to Your Project
```bash
# If you're in a project directory with railway.toml:
railway status

# Or link to specific project:
railway link
```

## Real-time Log Monitoring Commands

### Basic Log Commands
```bash
# Stream all logs in real-time
railway logs --follow

# Get last 100 log entries
railway logs --tail 100

# Get logs from last hour
railway logs --since 1h

# Get logs from specific time
railway logs --since "2024-01-01 10:00:00"
```

### Advanced Log Filtering
```bash
# Filter by service (if you have multiple services)
railway logs --follow --service backend

# Filter by deployment
railway logs --follow --deployment <deployment-id>

# Combine filters
railway logs --follow --service backend --tail 50
```

## Performance Testing with Log Monitoring

### Step-by-Step Process

1. **Terminal 1**: Start log monitoring
```bash
cd /path/to/your/backend
railway logs --follow
```

2. **Terminal 2**: Run performance tests
```bash
cd /path/to/your/backend
source test_env/bin/activate
python3 manual_performance_test.py
```

3. **Watch for these log patterns**:
   - Job creation and processing
   - Database operations
   - Celery worker activity
   - Error messages
   - Performance metrics

## Key Log Patterns to Monitor

### Job Processing Logs
```
[INFO] Created bulk upload job: job_id=abc123
[INFO] Starting bulk upload processing for job abc123
[INFO] Processing batch 1/10 for job abc123
[INFO] Processed 25/100 rows (25.0%) - Job abc123
[INFO] Bulk upload job abc123 completed: 100/100 rows successful
```

### Performance Metrics
```
[INFO] ML prediction batch processed in 2.3 seconds
[INFO] Database insert batch (10 rows) completed in 0.8 seconds
[INFO] Row processing rate: 3.2 rows/second
```

### Error Patterns
```
[ERROR] Database connection timeout for job abc123
[ERROR] ML model prediction failed for row 45
[WARNING] High memory usage detected: 85%
[ERROR] Celery worker timeout processing job abc123
```

### Database Performance
```
[INFO] Database query executed in 0.045 seconds
[WARNING] Slow query detected: 2.5 seconds
[INFO] Connection pool: 8/20 connections active
```

## Alternative: Manual Railway Dashboard Monitoring

If CLI doesn't work, use the web dashboard:

1. Go to https://railway.app/dashboard
2. Select your project
3. Click on your service
4. Go to **"Observability"** tab
5. View real-time logs

## Log Analysis Tips

### What to Look For During Testing

1. **Timing Information**
   - Job start/end timestamps
   - Processing duration per batch
   - Database query times
   - ML model prediction times

2. **Throughput Metrics**
   - Rows processed per second
   - Batches completed per minute
   - Queue processing rate

3. **Resource Usage**
   - Memory consumption
   - CPU usage spikes
   - Database connection counts

4. **Error Rates**
   - Failed row processing
   - Timeout occurrences
   - Database constraint violations

### Sample Log Analysis
```bash
# Count successful job completions
railway logs --since 1h | grep "completed:" | wc -l

# Find error patterns
railway logs --since 1h | grep -i error

# Check processing times
railway logs --since 1h | grep "processing time"

# Monitor memory usage
railway logs --since 1h | grep -i memory
```

## Troubleshooting Railway CLI

### Common Issues and Solutions

1. **Command not found**
```bash
# Check if CLI is installed
railway --version

# If not installed:
npm install -g @railway/cli
```

2. **Permission denied**
```bash
# Use sudo for global install
sudo npm install -g @railway/cli
```

3. **Not logged in**
```bash
railway login
railway whoami  # Verify login
```

4. **Project not linked**
```bash
railway link     # Link to existing project
railway status   # Check project status
```

5. **No services found**
```bash
railway status   # Check available services
railway logs --service <service-name>
```

## Real-time Performance Monitoring Script

Here's a script to run alongside your tests:

```bash
#!/bin/bash
# monitor_performance.sh

echo "🔍 Starting Railway performance monitoring..."

# Create log file with timestamp
LOG_FILE="railway_performance_$(date +%Y%m%d_%H%M%S).log"

# Start monitoring in background
railway logs --follow > "$LOG_FILE" &
LOG_PID=$!

echo "📝 Logging to: $LOG_FILE"
echo "🆔 Log process PID: $LOG_PID"

# Monitor for specific patterns
echo "🎯 Monitoring performance patterns..."
tail -f "$LOG_FILE" | grep --line-buffered -E "(completed|error|processing|seconds|rows)" &
FILTER_PID=$!

echo "⏹️  Press Ctrl+C to stop monitoring"

# Cleanup function
cleanup() {
    echo "🛑 Stopping monitoring..."
    kill $LOG_PID 2>/dev/null
    kill $FILTER_PID 2>/dev/null
    echo "📊 Performance logs saved to: $LOG_FILE"
    exit 0
}

# Set trap for cleanup
trap cleanup INT

# Wait for interruption
wait
```

Save this as `monitor_performance.sh` and run it during testing:
```bash
chmod +x monitor_performance.sh
./monitor_performance.sh
```

## Performance Test Execution Plan

### Complete Testing Workflow

1. **Prepare Environment**
```bash
cd /Users/nikhil/Downloads/pranit/work/final/default-rate/backend
source test_env/bin/activate
```

2. **Start Log Monitoring**
```bash
# Terminal 1
railway logs --follow | tee performance_logs_$(date +%Y%m%d_%H%M%S).txt
```

3. **Run Performance Tests**
```bash
# Terminal 2
echo "https://default-rate-backend-production.up.railway.app" | python3 manual_performance_test.py
```

4. **Analyze Results**
   - Review test output for performance metrics
   - Analyze logs for bottlenecks
   - Calculate averages and extrapolations

This setup will give you comprehensive real-time monitoring of your Railway application during performance testing!
