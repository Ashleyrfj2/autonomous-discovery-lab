"""Ordered, transactional schema migrations. Never edit an applied migration."""

MIGRATIONS = (
    """
            
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL DEFAULT 1,
              topic TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 0, owner TEXT, fence INTEGER NOT NULL DEFAULT 0,
              lease_until REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              failures INTEGER NOT NULL DEFAULT 0, last_error TEXT,
              policy_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS steps (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
              idempotency_key TEXT NOT NULL, input_hash TEXT NOT NULL,
              stage TEXT NOT NULL, target TEXT, output_json TEXT NOT NULL,
              result_json TEXT NOT NULL, UNIQUE(run_id,idempotency_key));
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
              run_id TEXT NOT NULL REFERENCES runs(id), kind TEXT NOT NULL,
              payload_json TEXT NOT NULL, timestamp TEXT NOT NULL,
              previous_hash TEXT NOT NULL, hash TEXT NOT NULL UNIQUE);
            CREATE INDEX IF NOT EXISTS events_run ON events(run_id,seq);
            
            
            """,
    """
CREATE TABLE daily_limits(day TEXT PRIMARY KEY,ceiling_nano INTEGER NOT NULL);
CREATE TABLE reservations(
 id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),request_key TEXT NOT NULL,
 fingerprint TEXT NOT NULL,day TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,
 reserved_nano INTEGER NOT NULL,charged_nano INTEGER NOT NULL,status TEXT NOT NULL,
 usage_json TEXT,result_json TEXT,UNIQUE(run_id,request_key));
CREATE INDEX reservation_day ON reservations(day);
CREATE TABLE circuits(provider TEXT NOT NULL,model TEXT NOT NULL,
 failures INTEGER NOT NULL DEFAULT 0,
 open_until REAL NOT NULL DEFAULT 0,last_error TEXT,PRIMARY KEY(provider,model));
""",
)
