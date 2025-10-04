from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import get_db

# Add this to your main.py or create new debug router
debug_router = APIRouter(prefix="/debug", tags=["debug"])

@debug_router.get("/db-tables")
async def list_db_tables():
    """List all database tables"""
    db = next(get_db())
    try:
        result = db.execute(text("""
            SELECT 
                schemaname, 
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        
        tables = []
        for row in result:
            tables.append({
                "schema": row[0],
                "table": row[1], 
                "owner": row[2]
            })
        
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@debug_router.get("/db-info")
async def get_db_info():
    """Get database connection and version info"""
    db = next(get_db())
    try:
        # Database info
        result = db.execute(text("SELECT current_database(), current_user, version()"))
        info = result.fetchone()
        
        # Table stats
        result = db.execute(text("""
            SELECT 
                count(*) as table_count,
                sum(n_tup_ins - n_tup_del) as total_rows
            FROM pg_stat_user_tables
        """))
        stats = result.fetchone()
        
        return {
            "database": info[0],
            "user": info[1],
            "version": info[2][:50] + "..." if len(info[2]) > 50 else info[2],
            "table_count": stats[0] if stats[0] else 0,
            "total_rows": stats[1] if stats[1] else 0
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@debug_router.get("/table-details/{table_name}")
async def get_table_details(table_name: str):
    """Get details about a specific table"""
    db = next(get_db())
    try:
        # Table structure
        result = db.execute(text(f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND table_schema = 'public'
            ORDER BY ordinal_position
        """))
        
        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2],
                "default": row[3]
            })
        
        # Row count
        result = db.execute(text(f"SELECT count(*) FROM {table_name}"))
        row_count = result.fetchone()[0]
        
        return {
            "table": table_name,
            "columns": columns,
            "row_count": row_count
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

# Add to your main.py:
# app.include_router(debug_router)
