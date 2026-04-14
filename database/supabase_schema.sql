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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    server TEXT                          -- 접속 서버 구분
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
-- 세션 토큰 조회 최적화: settings_data->_session->token expression 인덱스 (적용 완료)
CREATE INDEX IF NOT EXISTS idx_user_settings_session_token
    ON user_settings ((settings_data -> '_session' ->> 'token'))
    WHERE settings_data ? '_session';

-- 7. 분석 큐 (서버 배분 / 순번 관리)
CREATE TABLE IF NOT EXISTS analysis_queue (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    project_id  INTEGER,
    status      TEXT,                        -- waiting | running | done | cancelled
    position    INTEGER,
    entered_at  TIMESTAMPTZ,
    started_at  TIMESTAMPTZ,
    team_id     INTEGER,
    server      CHARACTER VARYING
);
CREATE INDEX IF NOT EXISTS idx_analysis_queue_user ON analysis_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_queue_status ON analysis_queue(status);

-- 8. 프로젝트 (다중 프로젝트 지원)
CREATE TABLE IF NOT EXISTS projects (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL DEFAULT '새 프로젝트',
    description TEXT,
    location    TEXT,
    status      TEXT DEFAULT 'in_progress',  -- in_progress | completed | archived
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(user_id, updated_at DESC);

-- analysis_sessions 에 project_id 추가
ALTER TABLE analysis_sessions
    ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_sessions_project ON analysis_sessions(project_id);
-- UNIQUE constraint: (user_id, project_id) 당 1행 보장 (UPSERT 정상 동작에 필요)
-- 이미 중복 행이 없는 경우에만 실행 가능
ALTER TABLE analysis_sessions
    ADD CONSTRAINT uq_sessions_user_project UNIQUE (user_id, project_id);

-- project_files: 업로드 파일 메타데이터 (바이너리는 Supabase Storage)
CREATE TABLE IF NOT EXISTS project_files (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_type       TEXT,                   -- pdf, docx, xlsx, …
    storage_path    TEXT,                   -- Supabase Storage 경로
    char_count      INTEGER,
    file_size_bytes INTEGER,
    file_meta       JSONB DEFAULT '{}'::jsonb,  -- quality_score, method 등
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_project_files_project ON project_files(project_id);

-- 9. 분석 실행(run) / 단계(step) 저장 (단계별 재실행 지원)
CREATE TABLE IF NOT EXISTS analysis_runs (
    id             BIGSERIAL PRIMARY KEY,
    project_id     BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status         TEXT DEFAULT 'running',  -- running | completed | failed
    input_snapshot JSONB,                  -- 실행 당시 입력 스냅샷(JSON 문자열 저장 가능)
    created_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_project ON analysis_runs(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS analysis_steps (
    id         BIGSERIAL PRIMARY KEY,
    run_id     BIGINT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    block_id   TEXT NOT NULL,
    block_name TEXT,
    step_index INTEGER,
    status     TEXT DEFAULT 'pending',   -- pending | running | completed | failed | skipped
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    inputs     JSONB,                   -- 단계 입력(JSON 문자열 저장 가능)
    outputs    JSONB,                   -- 단계 출력(JSON 문자열 저장 가능)
    error      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analysis_steps_run ON analysis_steps(run_id, step_index);
CREATE INDEX IF NOT EXISTS idx_analysis_steps_project ON analysis_steps(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_steps_block ON analysis_steps(project_id, block_id);

-- 10. 필지 API 캐시 (PNU 기준, NED/WFS 12개 병렬 호출 결과 저장)
CREATE TABLE IF NOT EXISTS parcel_cache (
    pnu          TEXT PRIMARY KEY,
    parcel_data  JSONB NOT NULL,
    cached_at    TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 정책: service_role 키 사용 시 바이패스되므로 별도 정책 불필요
-- 필요 시 아래 정책 추가 가능:
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "service_role_all" ON users FOR ALL USING (true);
