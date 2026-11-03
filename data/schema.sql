-- schema.sql: AskData Analytics Schema
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. USERS
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    country VARCHAR(2), -- ISO 2-letter country code (can be NULL)
    signup_date TIMESTAMPTZ NOT NULL,
    plan VARCHAR(50) NOT NULL, -- 'free', 'starter', 'pro', 'enterprise'
    is_test_account BOOLEAN NOT NULL DEFAULT FALSE -- TRAP 1: Internal/test accounts
);

-- 2. SUBSCRIPTIONS
CREATE TABLE subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'trialing', 'active', 'canceled', 'past_due'
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ, -- NULL for currently active subscriptions
    trial_end_date TIMESTAMPTZ
);

-- 3. PAYMENTS
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL, -- TRAP 2: 'USD' vs 'EUR'
    status VARCHAR(50) NOT NULL, -- TRAP 3: 'succeeded', 'failed', 'refunded'
    paid_at TIMESTAMPTZ NOT NULL,
    refunded_amount NUMERIC(10, 2) DEFAULT 0.00 -- TRAP 4: Partial or full refunds
);

-- 4. EVENTS
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_name VARCHAR(100) NOT NULL, -- 'page_view', 'login', 'dashboard_view', 'export_data', etc.
    occurred_at TIMESTAMPTZ NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb
);

-- Indexes for query performance
CREATE INDEX idx_users_signup_date ON users(signup_date);
CREATE INDEX idx_users_is_test ON users(is_test_account);
CREATE INDEX idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX idx_payments_user_status ON payments(user_id, status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at);
CREATE INDEX idx_events_user_occurred ON events(user_id, occurred_at);
CREATE INDEX idx_events_name ON events(event_name);
CREATE INDEX idx_events_properties ON events USING GIN (properties);
