-- Supabase 테이블 생성 SQL
-- Supabase Dashboard → SQL Editor에서 실행

-- 1. 팀 테이블
CREATE TABLE IF NOT EXISTS teams (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    personal_number TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user',
    team_id BIGINT REFERENCES teams(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'active',
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_personal_number ON users(personal_number);

-- 3. API 키 저장 (암호화)
CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    encryption_iv TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key_name)
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- 4. 사용자 블록
CREATE TABLE IF NOT EXISTS blocks (
    id BIGSERIAL PRIMARY KEY,
    block_id TEXT NOT NULL,
    owner_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    block_data JSONB NOT NULL,
    visibility TEXT DEFAULT 'personal',
    shared_with_teams JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blocks_owner ON blocks(owner_id);
CREATE INDEX IF NOT EXISTS idx_blocks_visibility ON blocks(visibility);

-- 5. 분석 세션
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    session_name TEXT,
    project_name TEXT,
    session_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user ON analysis_sessions(user_id);

-- 6. 사용자 설정
CREATE TABLE IF NOT EXISTS user_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    settings_data JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. 분석 진행 상태 (실시간 저장용)
CREATE TABLE IF NOT EXISTS analysis_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    progress_data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analysis_progress_user ON analysis_progress(user_id);

-- RLS 정책: service_role 키 사용 시 바이패스되므로 별도 정책 불필요
-- 필요 시 아래 정책 추가 가능:
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "service_role_all" ON users FOR ALL USING (true);
