-- ============================================
-- Complete Supabase Database Setup
-- Run this entire script in Supabase SQL Editor
-- ============================================

-- ============================================
-- PART 1: CREATE TABLES
-- ============================================

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256),
    google_id VARCHAR(100) UNIQUE,
    name VARCHAR(100),
    api_key VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create ad_accounts table
CREATE TABLE IF NOT EXISTS ad_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(200),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, account_id)
);

-- Create mcp_sessions table
CREATE TABLE IF NOT EXISTS mcp_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(200) UNIQUE NOT NULL,
    client_info TEXT,
    last_activity TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PART 2: CREATE INDEXES
-- ============================================

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_ad_accounts_user_id ON ad_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_user_id ON mcp_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_sessions_token ON mcp_sessions(session_token);

-- ============================================
-- PART 3: CREATE UPDATE TRIGGER
-- ============================================

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ad_accounts_updated_at ON ad_accounts;
CREATE TRIGGER update_ad_accounts_updated_at BEFORE UPDATE ON ad_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_mcp_sessions_updated_at ON mcp_sessions;
CREATE TRIGGER update_mcp_sessions_updated_at BEFORE UPDATE ON mcp_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- PART 4: ROW LEVEL SECURITY (OPTIONAL)
-- Uncomment this section if you want to enable RLS
-- ============================================

-- -- Enable RLS on all tables
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ad_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE mcp_sessions ENABLE ROW LEVEL SECURITY;

-- -- USERS TABLE POLICIES
-- -- Allow service role full access (since we're not using Supabase Auth)
-- CREATE POLICY "Service role full access to users" ON users
--     FOR ALL
--     USING (auth.role = 'service_role')
--     WITH CHECK (auth.role = 'service_role');

-- -- AD_ACCOUNTS TABLE POLICIES
-- CREATE POLICY "Service role full access to ad_accounts" ON ad_accounts
--     FOR ALL
--     USING (auth.role = 'service_role')
--     WITH CHECK (auth.role = 'service_role');

-- -- MCP_SESSIONS TABLE POLICIES
-- CREATE POLICY "Service role full access to mcp_sessions" ON mcp_sessions
--     FOR ALL
--     USING (auth.role = 'service_role')
--     WITH CHECK (auth.role = 'service_role');

-- ============================================
-- VERIFICATION QUERIES
-- Run these to verify setup
-- ============================================

-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'ad_accounts', 'mcp_sessions');

-- Check RLS status (should show FALSE unless you enabled it)
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'ad_accounts', 'mcp_sessions');