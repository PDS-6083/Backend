-- MySQL User Creation and Grant Commands for AeroSync Database
-- Run this script as a MySQL root user or a user with GRANT privileges

-- Replace 'your_database_name' with your actual database name
-- Replace 'your_app_user' and 'your_app_password' with your desired credentials
-- Replace 'your_readonly_user' and 'your_readonly_password' with your desired credentials

-- ============================================
-- 1. Create Application User (Full Access)
-- ============================================

-- Create the main application user
CREATE USER IF NOT EXISTS 'aerosync_app'@'%' IDENTIFIED BY 'change_this_password';

-- Grant all privileges on the database and all tables
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, REFERENCES, CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, CREATE VIEW, SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER 
ON aerosync.* TO 'aerosync_app'@'%';

-- Alternative: Grant all privileges (use with caution)
-- GRANT ALL PRIVILEGES ON aerosync.* TO 'aerosync_app'@'%';

-- ============================================
-- 2. Create Read-Only User (For Reporting/Backup)
-- ============================================

CREATE USER IF NOT EXISTS 'aerosync_readonly'@'%' IDENTIFIED BY 'change_this_readonly_password';

-- Grant SELECT privilege on all tables
GRANT SELECT ON aerosync.* TO 'aerosync_readonly'@'%';

-- ============================================
-- 3. Table-Specific Grants (Optional - More Granular Control)
-- ============================================

-- If you want to grant permissions on specific tables only, use these:

-- Core tables
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.airports TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.routes TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.aircraft TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.flights TO 'aerosync_app'@'%';

-- Crew and scheduling tables
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.crew TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.crew_schedules TO 'aerosync_app'@'%';

-- Engineer tables
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.engineers TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.maintenance_history TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.engineer_maintenances TO 'aerosync_app'@'%';

-- Admin and scheduler tables
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.schedulers TO 'aerosync_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.admins TO 'aerosync_app'@'%';

-- Parts table
GRANT SELECT, INSERT, UPDATE, DELETE ON aerosync.aircraft_parts TO 'aerosync_app'@'%';

-- ============================================
-- 4. Localhost-Only User (For Development)
-- ============================================

-- Create a user that can only connect from localhost (more secure for local development)
CREATE USER IF NOT EXISTS 'aerosync_local'@'localhost' IDENTIFIED BY 'change_this_local_password';
GRANT ALL PRIVILEGES ON aerosync.* TO 'aerosync_local'@'localhost';

-- ============================================
-- 5. Apply Changes
-- ============================================

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- ============================================
-- 6. Verify Users (Optional - Run to check)
-- ============================================

-- Uncomment to verify users were created:
-- SELECT User, Host FROM mysql.user WHERE User LIKE 'aerosync%';

-- Uncomment to verify grants:
-- SHOW GRANTS FOR 'aerosync_app'@'%';
-- SHOW GRANTS FOR 'aerosync_readonly'@'%';
-- SHOW GRANTS FOR 'aerosync_local'@'localhost';

-- ============================================
-- 7. Revoke/Delete Users (If Needed)
-- ============================================

-- To revoke privileges:
-- REVOKE ALL PRIVILEGES ON aerosync.* FROM 'aerosync_app'@'%';

-- To delete users:
-- DROP USER IF EXISTS 'aerosync_app'@'%';
-- DROP USER IF EXISTS 'aerosync_readonly'@'%';
-- DROP USER IF EXISTS 'aerosync_local'@'localhost';

