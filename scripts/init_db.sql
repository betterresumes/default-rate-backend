-- Initialize AccuNode Development Database
-- This script runs when PostgreSQL container starts for the first time

-- Create additional databases if needed
-- CREATE DATABASE accunode_test;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create initial roles if needed
-- CREATE ROLE readonly_user LOGIN PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE accunode_development TO readonly_user;
-- GRANT USAGE ON SCHEMA public TO readonly_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- Log successful initialization
SELECT 'AccuNode development database initialized successfully!' as initialization_status;
