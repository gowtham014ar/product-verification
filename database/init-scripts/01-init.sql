-- Product Verification System — PostgreSQL init script
-- Runs once when the postgres container first starts.

-- Database product_verification is automatically created and connected by POSTGRES_DB environment variable.


-- Users and products tables are created by SQLAlchemy on service startup.
-- This script seeds an admin user so the system is usable immediately.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table if not exists (in case postgres initializes before auth-service startup)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'customer',
    wallet_address VARCHAR(42),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed admin users (password: "admin123" bcrypt hash)
-- Change this immediately in production.
INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at)
VALUES 
(
    uuid_generate_v4()::text,
    'admin@productverify.local',
    '$2b$12$HvwmHkLoxiu9bQcuu0fm5O5v4IaQYKuPOWey5kbBcfHDTZeuKIlni',
    'System Admin',
    'admin',
    true,
    NOW()
),
(
    uuid_generate_v4()::text,
    'admin@productverify.com',
    '$2b$12$HvwmHkLoxiu9bQcuu0fm5O5v4IaQYKuPOWey5kbBcfHDTZeuKIlni',
    'System Admin',
    'admin',
    true,
    NOW()
) ON CONFLICT (email) DO NOTHING;
