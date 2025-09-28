# Bulk Upload Performance Testing Guide

## Overview
This guide helps you test the performance of your bulk upload APIs deployed on Railway and provides detailed analysis of processing times.

## Files Created
1. `generate_test_data.py` - Generates test Excel files with different row counts
2. `manual_performance_test.py` - Main testing script for Railway deployment
3. `performance_tester.py` - Advanced async testing script
4. `railway_logs_monitor.py` - Monitors Railway logs during testing
5. `test_data/` directory - Contains generated test files

## Test Data Files
- `annual_test_10_rows.xlsx` - 10 rows of annual prediction data
- `annual_test_20_rows.xlsx` - 20 rows of annual prediction data
- `annual_test_50_rows.xlsx` - 50 rows of annual prediction data
- `annual_test_100_rows.xlsx` - 100 rows of annual prediction data
- `quarterly_test_10_rows.xlsx` - 10 rows of quarterly prediction data
- `quarterly_test_20_rows.xlsx` - 20 rows of quarterly prediction data
- `quarterly_test_50_rows.xlsx` - 50 rows of quarterly prediction data
- `quarterly_test_100_rows.xlsx` - 100 rows of quarterly prediction data

## Quick Start Testing

### Step 1: Update Railway URL
Edit `manual_performance_test.py` and update the BASE_URL:
```python
BASE_URL = "https://your-actual-railway-url.railway.app"
```

### Step 2: Run Performance Test
```bash
cd /path/to/your/backend
python3 manual_performance_test.py
```

## What the Test Measures

### Upload Performance
- File upload time to Railway
- API response time
- Job creation time

### Processing Performance
- Actual row processing time
- Database insertion speed
- ML model prediction time
- Celery worker efficiency

### Key Metrics Calculated
- **Time per row**: How long each row takes to process
- **Rows per second**: Processing throughput
- **Time per 100 rows**: Benchmark for scaling estimates
- **Total processing time**: End-to-end job completion time

## Railway Logs Access

### Option 1: Railway CLI (Recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Monitor logs during testing
python3 railway_logs_monitor.py
```

### Option 2: Railway Dashboard
1. Go to https://railway.app/dashboard
2. Select your project
3. Click on your service
4. Go to 'Observability' tab
5. View real-time logs during testing

## Understanding the Results

### Sample Output Interpretation
```
🎉 COMPLETED SUCCESSFULLY!
   Total monitoring time: 45.23 seconds
   Actual processing time: 42.15 seconds
   Successful rows: 100
   Failed rows: 0
   Rows per second: 2.37
   Time per row: 0.4215 seconds
   Time per 100 rows: 42.15 seconds
```

### Key Performance Indicators
- **Rows per second < 1**: Slow processing, may need optimization
- **Rows per second 1-5**: Moderate performance, acceptable for small files
- **Rows per second > 5**: Good performance for production use
- **Failed rows > 0**: Check logs for data validation issues

### Scaling Estimates
Based on the time per row metric, you can estimate processing times:
- 500 rows: `time_per_row * 500`
- 1,000 rows: `time_per_row * 1,000`
- 10,000 rows: `time_per_row * 10,000`

## Performance Analysis Checklist

### During Testing, Monitor:
1. **API Response Times**: Should be < 2 seconds for upload
2. **Job Queue Status**: Check if jobs queue up during high load
3. **Database Performance**: Look for slow query logs
4. **Memory Usage**: Monitor for memory leaks during processing
5. **Celery Worker Status**: Ensure workers are processing jobs
6. **Error Rates**: Track failed vs successful uploads

### Log Patterns to Look For:
```
# Job creation
[INFO] Created bulk upload job: job_id=123abc

# Processing start
[INFO] Starting bulk upload processing for job 123abc

# Row processing
[INFO] Processed 25/100 rows (25.0%)

# ML predictions
[INFO] Generated predictions for batch of 10 rows

# Database operations
[INFO] Inserted 10 predictions into database

# Job completion
[INFO] Bulk upload job 123abc completed: 100/100 rows successful
```

## Troubleshooting Common Issues

### Slow Performance
- Check database connection pool settings
- Verify Celery worker configuration
- Monitor Railway resource limits
- Optimize ML model loading

### High Error Rates
- Validate input data format
- Check authentication/authorization
- Review database constraints
- Monitor API rate limits

### Timeouts
- Increase request timeout settings
- Check Railway deployment limits
- Verify database connection timeouts
- Monitor memory usage during processing

## Advanced Testing

### Load Testing
To test with higher concurrency, modify the test script to run multiple uploads simultaneously:
```python
# Run multiple tests in parallel
import asyncio
tasks = [test_upload(url, token, file, endpoint) for file in test_files]
results = await asyncio.gather(*tasks)
```

### Stress Testing
Test with larger files by creating bigger test datasets:
```python
# Generate larger test files
create_annual_test_data(500, "annual_test_500_rows.xlsx")
create_annual_test_data(1000, "annual_test_1000_rows.xlsx")
```

## Railway Resource Monitoring

### Memory Usage
```bash
railway logs | grep -i "memory\|oom"
```

### CPU Usage
```bash
railway logs | grep -i "cpu\|load"
```

### Database Connections
```bash
railway logs | grep -i "database\|connection"
```

## Expected Performance Benchmarks

### Good Performance Targets
- **Small files (< 50 rows)**: < 30 seconds total
- **Medium files (50-200 rows)**: < 2 minutes total
- **Large files (200-1000 rows)**: < 10 minutes total

### Production Recommendations
- **Process files in batches**: 100-500 rows per batch
- **Implement progress tracking**: Real-time status updates
- **Queue management**: Handle multiple concurrent uploads
- **Error recovery**: Retry failed rows automatically

## Next Steps After Testing
1. Analyze results and identify bottlenecks
2. Optimize slow components (DB queries, ML models, etc.)
3. Implement caching for frequently used data
4. Scale Railway resources if needed
5. Add monitoring and alerting for production use
