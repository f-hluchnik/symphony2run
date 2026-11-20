CREATE TABLE works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            composer TEXT NOT NULL,
            work TEXT NOT NULL,
            duration_ms INTEGER NOT NULL, verified BOOLEAN NOT NULL DEFAULT 0, excluded BOOLEAN NOT NULL DEFAULT 0,
            UNIQUE(composer, work)
        );
CREATE INDEX idx_duration ON works(duration_ms);
CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));
INSERT INTO alembic_version VALUES ('d432ee45a620');
INSERT INTO works (composer, work, duration_ms, verified) VALUES ('Composer Z', 'Legacy work', 1500000, 1);
