-- PostgreSQL Schema & Initial Seed for SocialCoach AI
-- Multi-Tenant Autonomous Social Media & Lead-Gen Agent SaaS

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 1. Tenants ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    coaching_niche VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'PRO',
    brand_colors JSONB DEFAULT '{"primary": "#6C63FF", "secondary": "#F0EDFF", "accent": "#FF6B6B", "text": "#1A1A2E", "text_light": "#FFFFFF"}'::jsonb,
    brand_fonts JSONB DEFAULT '{"heading": "Plus Jakarta Sans", "body": "Plus Jakarta Sans"}'::jsonb,
    logo_url TEXT,
    active_platforms TEXT[] DEFAULT ARRAY['linkedin', 'instagram', 'twitter'],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. Users ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role VARCHAR(50) DEFAULT 'COACH',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. OAuth Token Vault ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[] DEFAULT ARRAY[]::text[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, platform)
);

-- ── 4. Audit Token Access Log ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS token_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    caller_service VARCHAR(100) DEFAULT 'api'
);

-- ── 5. Posts & Carousels ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR(100) PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    hook TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING_APPROVAL',
    critic_score NUMERIC(3, 1),
    critic_feedback TEXT,
    platforms TEXT[] DEFAULT ARRAY['linkedin', 'instagram', 'twitter'],
    linkedin_text TEXT,
    instagram_caption TEXT,
    twitter_thread JSONB,
    facebook_post TEXT,
    slides JSONB,
    carousel_pdf_url TEXT,
    carousel_png_urls JSONB,
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. Comment-to-DM Leads CRM ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    post_id VARCHAR(100),
    platform VARCHAR(50) NOT NULL,
    username VARCHAR(150) NOT NULL,
    keyword_triggered VARCHAR(50) NOT NULL,
    dm_status VARCHAR(50) DEFAULT 'SENT',
    lead_magnet_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    converted_at TIMESTAMPTZ
);

-- ── 7. Job Market Newsjack Signals ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS newsjack_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    headline TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    virality_score INTEGER DEFAULT 80,
    category VARCHAR(100) NOT NULL,
    urgency VARCHAR(20) DEFAULT 'HIGH',
    recommended_angle TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── SEED DATA ──────────────────────────────────────────────────────────────
INSERT INTO tenants (id, name, subdomain, coaching_niche, plan, brand_colors)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'Sarah Jenkins Coaching',
    'sarah-jenkins',
    'Tech Executive & VP Transitions',
    'ENTERPRISE',
    '{"primary": "#6C63FF", "secondary": "#F0EDFF", "accent": "#FF6B6B", "text": "#1A1A2E", "text_light": "#FFFFFF"}'::jsonb
) ON CONFLICT DO NOTHING;

INSERT INTO users (id, tenant_id, email, hashed_password, role)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'coach@sarahjenkins.io',
    '$2b$12$e80yq5q50dK5137xQv.lO.nLd5x9zP53iKkU99qF.Kx2K567L84aK',
    'COACH'
) ON CONFLICT DO NOTHING;

INSERT INTO newsjack_signals (headline, source, virality_score, category, urgency, recommended_angle)
VALUES 
(
    'Major Cloud Provider announces 8% restructuring to double down on Autonomous AI Agents',
    'TechCrunch / BLS Jobs Report',
    96,
    'LAYOFF',
    'HIGH',
    'Pivot story: How infrastructure engineers can re-position skills for the Agentic AI wave.'
),
(
    'Q4 Hiring Rebound: Cybersecurity and Platform Engineering salaries jump 14%',
    'Wall Street Journal Careers',
    88,
    'SALARY_TREND',
    'MEDIUM',
    'Salary negotiation breakdown for mid-to-senior security specialists.'
),
(
    'Return-to-Office Mandate backlash leads to 35% surge in remote contractor applications',
    'LinkedIn Workforce Insights',
    92,
    'REMOTE_WORK',
    'HIGH',
    'Tactical guide: How to negotiate permanent remote terms during interview rounds.'
) ON CONFLICT DO NOTHING;
