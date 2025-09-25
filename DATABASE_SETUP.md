# Database Setup Instructions for Railway

## Option 1: Add PostgreSQL via Railway Dashboard
1. In your Railway project dashboard
2. Click "Add Service" → "Database" → "PostgreSQL" 
3. Railway will automatically provide DATABASE_URL environment variable

## Option 2: Use External Database
- Set DATABASE_URL manually in Railway variables

## Database Migration Commands
After database is set up, run migrations:

```bash
# If using Alembic
railway run alembic upgrade head

# If using Django
railway run python manage.py migrate

# If using custom migration scripts
railway run python scripts/setup_database.py
```

## Test Database Connection
```python
# Test script to verify database connection
import os
import asyncpg

async def test_db():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Database connected: {result}")
        await conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
```
