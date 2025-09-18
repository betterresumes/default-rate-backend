#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
    tables = [row[0] for row in result]
    print('📋 Created Tables:')
    for table in tables:
        print(f'   ✅ {table}')
    
    print('\n🔍 Checking users table...')
    result = conn.execute(text("SELECT count(*) FROM users"))
    user_count = result.fetchone()[0]
    print(f'   👥 Users in database: {user_count}')
    
    if user_count > 0:
        result = conn.execute(text("SELECT email, global_role, is_verified FROM users LIMIT 1"))
        user = result.fetchone()
        print(f'   🔑 Test user: {user[0]} (role: {user[1]}, verified: {user[2]})')
