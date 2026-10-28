CREATE TABLE IF NOT EXISTS sources (
    slug        TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'enabled'
                CHECK (status IN ('enabled','disabled','quarantined')),
    cursor      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS records (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL REFERENCES sources(slug),
    source_ref   TEXT NOT NULL,
    title        TEXT,
    caption      TEXT,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    year         INT,
    license      TEXT NOT NULL,
    nsfw_score   REAL NOT NULL DEFAULT 0,
    visual_vec   REAL[],
    visual_ver   INT,
    text_vec     REAL[],
    text_ver     INT,
    phash        TEXT,
    thumb        BYTEA,
    taken_down   BOOLEAN NOT NULL DEFAULT false,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_ref)
);

-- text vectors alag table mein, taaki naya version purane ke saath mix na ho
CREATE TABLE IF NOT EXISTS text_embeddings (
    record_id          BIGINT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    embedding_version  INT NOT NULL,
    vec                REAL[] NOT NULL,
    PRIMARY KEY (record_id, embedding_version)
);

-- ek hi row: kaunsa version live hai
CREATE TABLE IF NOT EXISTS index_state (
    id              INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    active_version  INT NOT NULL DEFAULT 1,
    index_version   BIGINT NOT NULL DEFAULT 1
);
INSERT INTO index_state (id) VALUES (1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS jobs (
    id           BIGSERIAL PRIMARY KEY,
    type         TEXT NOT NULL CHECK (type IN ('ingest','reembed')),
    source       TEXT,
    status       TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued','running','done','failed')),
    processed    INT NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ
);

-- append-only: sirf INSERT, kabhi UPDATE/DELETE nahi
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    record_id   BIGINT NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);