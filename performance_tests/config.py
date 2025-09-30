"""
Performance Testing Configuration
"""
import os

# Base API URL
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Test Configuration
TEST_CONFIG = {
    "concurrent_users": [1, 5, 10, 20, 50],
    "test_duration": 30,  # seconds
    "ramp_up_time": 5,    # seconds
    "iterations_per_user": 10,
    "timeout": 30,        # request timeout in seconds
    "delay_between_requests": 0.1,  # seconds
}

# Database Configuration - Production Neon PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_FRS5ptsg3QcE@ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# Authentication Test Data
AUTH_TEST_DATA = {
    "valid_user": {
        "email": "test@example.com",
        "password": "TestPass123",
        "username": "testuser",
        "full_name": "Test User"
    },
    "invalid_user": {
        "email": "invalid@example.com",
        "password": "wrongpass123"
    },
    "weak_password": {
        "email": "weak@example.com", 
        "password": "123"
    },
    "malformed_email": {
        "email": "notanemail",
        "password": "TestPass123"
    }
}

# Performance Thresholds (in milliseconds) - Adjusted for Production Database
PERFORMANCE_THRESHOLDS = {
    "auth": {
        "register": 5000,     # 5 seconds (includes bcrypt + network latency)
        "login": 3000,        # 3 seconds (includes bcrypt + network latency)
        "refresh": 1000,      # 1 second (JWT processing + network)
        "logout": 500,        # 0.5 seconds (minimal processing)
        "join": 3000,         # 3 seconds (DB queries + network)
        "change_password": 4000  # 4 seconds (bcrypt + DB update + network)
    }
}

# Report Configuration
REPORT_CONFIG = {
    "output_dir": "reports",
    "formats": ["html", "json", "csv"],
    "include_graphs": True,
    "detailed_logs": True
}
