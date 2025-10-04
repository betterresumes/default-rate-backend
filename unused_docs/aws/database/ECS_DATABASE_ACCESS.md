# 🐳 Use Your ECS Container to Access Database

## Method 1: ECS Exec (Recommended)
Your running ECS container already has access to the RDS.

### Step 1: Enable ECS Exec on your service
```bash
aws ecs update-service \
  --cluster your-cluster-name \
  --service your-service-name \
  --enable-execute-command
```

### Step 2: Connect to running container
```bash
aws ecs execute-command \
  --cluster your-cluster-name \
  --task your-task-id \
  --container your-container-name \
  --interactive \
  --command "/bin/bash"
```

### Step 3: Inside container, connect to DB
```bash
# Install psql if not available
apt-get update && apt-get install -y postgresql-client

# Connect to database
PGPASSWORD='AccuNode2024!SecurePass' psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432

# List tables
\dt

# Run queries
SELECT * FROM pg_tables WHERE schemaname = 'public';
```

## Method 2: Use Your Application's Database Connection
Since your FastAPI app is already running and connected:

### Step 1: Add a debug endpoint to your app
Add this to your FastAPI app temporarily:

```python
@app.get("/debug/db-tables")
async def debug_db_tables():
    """Debug endpoint to list database tables"""
    db = next(get_db())
    try:
        result = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        return {"tables": tables}
    finally:
        db.close()

@app.get("/debug/db-info") 
async def debug_db_info():
    """Debug endpoint for database info"""
    db = next(get_db())
    try:
        # Get database info
        result = db.execute(text("SELECT current_database(), current_user, version()"))
        info = result.fetchone()
        
        # Get table count
        result = db.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"))
        table_count = result.fetchone()[0]
        
        return {
            "database": info[0],
            "user": info[1], 
            "version": info[2],
            "table_count": table_count
        }
    finally:
        db.close()
```

### Step 2: Access via your app URL
```bash
curl https://your-app-url.com/debug/db-tables
curl https://your-app-url.com/debug/db-info
```

## Method 3: Railway CLI (if using Railway)
```bash
railway connect postgres
```

## 🔍 Find Your ECS Details
```bash
# List clusters
aws ecs list-clusters

# List services in cluster  
aws ecs list-services --cluster your-cluster-name

# List tasks
aws ecs list-tasks --cluster your-cluster-name --service-name your-service-name

# Get task details
aws ecs describe-tasks --cluster your-cluster-name --tasks your-task-arn
```
