-- guard_setup.sql: Database Protections for AskData Query Guard
-- Run this script in your Supabase SQL Editor as admin (postgres user).

-- 1. Create Views Excluding Sensitive Columns (PII)
-- Drops existing views if recreating
DROP VIEW IF EXISTS v_users CASCADE;
DROP VIEW IF EXISTS v_subscriptions CASCADE;
DROP VIEW IF EXISTS v_payments CASCADE;
DROP VIEW IF EXISTS v_events CASCADE;

-- View 1: v_users (EXCLUDES email and full_name)
CREATE VIEW v_users AS
SELECT 
    id,
    country,
    signup_date,
    plan,
    is_test_account
FROM users;

-- View 2: v_subscriptions
CREATE VIEW v_subscriptions AS
SELECT 
    id,
    user_id,
    plan,
    status,
    start_date,
    end_date,
    trial_end_date
FROM subscriptions;

-- View 3: v_payments
CREATE VIEW v_payments AS
SELECT 
    id,
    user_id,
    amount,
    currency,
    status,
    paid_at,
    refunded_amount
FROM payments;

-- View 4: v_events
CREATE VIEW v_events AS
SELECT 
    id,
    user_id,
    event_name,
    occurred_at,
    properties
FROM events;

-- 2. Create the Dedicated Read-Only Role
-- Check if role already exists; if not, create it
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'askdata_readonly') THEN
        CREATE ROLE askdata_readonly WITH LOGIN PASSWORD 'AskDataReadonly2026!';
    ELSE
        ALTER ROLE askdata_readonly WITH LOGIN PASSWORD 'AskDataReadonly2026!';
    END IF;
END $$;

-- 3. Strict Statement Timeout (5 seconds max for any analytical query)
ALTER ROLE askdata_readonly SET statement_timeout = '5000ms';

-- 4. Permissions: Allow access ONLY to safe views
GRANT USAGE ON SCHEMA public TO askdata_readonly;

-- Revoke all direct permissions from the raw underlying tables
REVOKE ALL ON users, subscriptions, payments, events FROM askdata_readonly;

-- Grant SELECT only on the safe analytical views
GRANT SELECT ON v_users, v_subscriptions, v_payments, v_events TO askdata_readonly;

-- 5. Audit Log Table (tracked by the Java Guard Service)
CREATE TABLE IF NOT EXISTS query_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255),
    question TEXT,
    sql_query TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    rejection_reason TEXT,
    execution_time_ms BIGINT,
    row_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON query_audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_allowed ON query_audit_logs(allowed);

-- Allow backend service to insert audit logs
GRANT SELECT, INSERT ON query_audit_logs TO postgres;
