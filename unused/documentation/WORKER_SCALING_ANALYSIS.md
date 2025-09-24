# 🚀 Celery Worker Capacity & Scaling Analysis

## 📊 **Current Configuration**

### **Single Worker Setup:**
```python
# Current settings in celery_app.py
worker_pool="solo" if sys.platform == "darwin" else "prefork"
worker_concurrency=1 if sys.platform == "darwin" else None  # Default is CPU cores
```

### **Task Types & Processing Requirements:**

| Task Type | Complexity | Avg Duration | Memory Usage |
|-----------|------------|--------------|--------------|
| 📧 **Email Tasks** | Low | 1-3 seconds | 10-20 MB |
| 📊 **Bulk Predictions** | High | 30-300 seconds | 100-500 MB |
| 🔄 **Excel Processing** | Medium | 10-60 seconds | 50-200 MB |
| 📈 **Quarterly Bulk** | High | 20-180 seconds | 80-400 MB |

## 🔢 **Worker Capacity Analysis**

### **1 Worker Can Handle:**

#### **Current macOS Development (Solo Pool):**
- ⚠️ **Concurrency: 1 task at a time** (sequential processing)
- 📧 **Email tasks**: ~1200-3600 per hour
- 📊 **Small bulk uploads** (100 rows): ~12-120 per hour  
- 📊 **Large bulk uploads** (10K rows): ~1-12 per hour

#### **Production Linux (Prefork Pool):**
- ✅ **Concurrency: CPU cores** (typically 2-4 cores = 2-4 concurrent tasks)
- 📧 **Email tasks**: ~2400-14400 per hour
- 📊 **Small bulk uploads**: ~24-480 per hour
- 📊 **Large bulk uploads**: ~2-48 per hour

## 🎯 **Scaling Recommendations**

### **Scenario 1: Light Usage (< 50 users)**
```yaml
Workers: 1
Configuration:
  - Concurrency: 2-4 (based on CPU cores)
  - Memory: 512MB - 1GB
  - Queue separation: Not required
```

### **Scenario 2: Medium Usage (50-200 users)**
```yaml
Workers: 2
Configuration:
  - Worker 1: Email tasks (fast, low memory)
  - Worker 2: Bulk processing (slow, high memory)
  - Total Concurrency: 6-8 tasks
  - Memory: 1-2GB per worker
```

### **Scenario 3: Heavy Usage (200+ users)**
```yaml
Workers: 3-4
Configuration:
  - Worker 1: Email queue only
  - Worker 2-3: Bulk prediction queue
  - Worker 4: General processing
  - Total Concurrency: 12-16 tasks
  - Memory: 2GB+ per bulk worker
```

## ⚙️ **Optimal Worker Configuration**

### **For Railway Production:**
```bash
# Start specialized workers
celery -A app.workers.celery_app worker -Q emails --concurrency=4 --loglevel=info
celery -A app.workers.celery_app worker -Q bulk_predictions --concurrency=2 --loglevel=info
```

### **Updated Celery Configuration:**
```python
# Add to celery_app.py for better scaling
task_routes={
    "*.send_*_email_task": {"queue": "emails"},
    "*.process_*_bulk_*_task": {"queue": "bulk_predictions"},
    "*.process_*_excel_task": {"queue": "bulk_predictions"},
},

# Worker-specific settings
task_soft_time_limit=300,  # 5 minutes soft limit
task_time_limit=600,       # 10 minutes hard limit
worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
```

## 📈 **Performance Metrics**

### **Current Single Worker Bottlenecks:**
1. **Sequential Processing**: Only 1 task at a time on macOS
2. **Mixed Queues**: Fast email tasks blocked by slow bulk uploads
3. **Memory Competition**: Large uploads can affect other tasks

### **2 Worker Benefits:**
✅ **Queue Separation**: Email tasks never blocked by bulk processing  
✅ **Parallel Processing**: 2-6 concurrent tasks (depending on configuration)  
✅ **Memory Isolation**: Bulk tasks don't affect email performance  
✅ **Better Fault Tolerance**: One worker failure doesn't stop all tasks  

### **Resource Requirements:**

| Workers | CPU Usage | Memory Usage | Concurrent Tasks | Recommended For |
|---------|-----------|--------------|------------------|-----------------|
| 1 | 1-2 cores | 256MB-1GB | 1-4 | Development, <50 users |
| 2 | 2-4 cores | 512MB-2GB | 2-8 | Production, 50-200 users |
| 3-4 | 4-8 cores | 1-4GB | 6-16 | Heavy load, 200+ users |

## 🔧 **Implementation Plan**

### **Step 1: Enhanced Single Worker**
```python
# Update celery_app.py
worker_concurrency=4 if sys.platform != "darwin" else 1,
task_soft_time_limit=300,
task_time_limit=600,
worker_max_tasks_per_child=100,
```

### **Step 2: Queue-Based Scaling**
```bash
# Railway: Start with queue separation
celery -A app.workers.celery_app worker -Q emails,bulk_predictions --concurrency=4
```

### **Step 3: Multi-Worker Setup**
```bash
# Railway: Multiple worker processes
worker1: celery -A app.workers.celery_app worker -Q emails --concurrency=4
worker2: celery -A app.workers.celery_app worker -Q bulk_predictions --concurrency=2
```

## 🎯 **Recommendation for Your System**

### **Current State: Start with 1 Enhanced Worker**
- ✅ Enable proper concurrency (4 workers on Railway)
- ✅ Implement queue separation
- ✅ Add task timeouts and limits
- ✅ Monitor performance

### **Scale to 2 Workers When:**
- Users > 50 concurrent users
- Bulk uploads > 10 per hour
- Email delivery delays > 30 seconds
- Worker memory usage > 80%

### **Key Configuration Updates Needed:**

1. **Remove macOS limitations for production**
2. **Add task routing by queue**  
3. **Set proper concurrency limits**
4. **Add monitoring endpoints**

Would you like me to implement these optimizations to your current setup?
