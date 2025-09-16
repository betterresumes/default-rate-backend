#!/usr/bin/env python3
"""
Database reset script for the new single table schema
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the current directory to Python path
sys.path.append('/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

from src.database import engine, Base

def reset_database():
    print('Dropping all existing tables...')
    Base.metadata.drop_all(bind=engine)
    
    print('Creating new tables with updated schema...')
    Base.metadata.create_all(bind=engine)
    
    print('Database reset complete!')
    print('New schema includes a single "companies" table with all company info, financial ratios, and predictions.')

if __name__ == "__main__":
    reset_database()
