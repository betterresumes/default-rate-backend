-- Check current data
SELECT 'CURRENT DATA:' as status;
SELECT COUNT(*) FROM users; 
SELECT COUNT(*) FROM tenants; 
SELECT COUNT(*) FROM organizations;

-- Reset everything (CORRECTED - no IF EXISTS)
SET session_replication_role = replica;

TRUNCATE TABLE bulk_upload_jobs RESTART IDENTITY CASCADE;
TRUNCATE TABLE quarterly_predictions RESTART IDENTITY CASCADE;  
TRUNCATE TABLE annual_predictions RESTART IDENTITY CASCADE;
TRUNCATE TABLE companies RESTART IDENTITY CASCADE;
TRUNCATE TABLE organization_member_whitelists RESTART IDENTITY CASCADE;
TRUNCATE TABLE users RESTART IDENTITY CASCADE;
TRUNCATE TABLE organizations RESTART IDENTITY CASCADE;
TRUNCATE TABLE tenants RESTART IDENTITY CASCADE;

-- Reset sequences
DO $$
DECLARE seq_name TEXT;
BEGIN
    FOR seq_name IN SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
    LOOP
        EXECUTE 'ALTER SEQUENCE ' || seq_name || ' RESTART WITH 1';
    END LOOP;
END $$;

SET session_replication_role = DEFAULT;

-- Verify
SELECT 'AFTER RESET:' as status;
SELECT COUNT(*) FROM users; 
SELECT COUNT(*) FROM tenants; 
SELECT COUNT(*) FROM organizations;