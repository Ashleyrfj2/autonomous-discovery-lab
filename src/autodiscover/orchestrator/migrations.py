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
    """
CREATE TABLE research_nodes(id TEXT PRIMARY KEY,kind TEXT NOT NULL,artifact_digest TEXT NOT NULL,
 valid INTEGER NOT NULL DEFAULT 1,summary TEXT NOT NULL);
CREATE TABLE run_sources(run_id TEXT NOT NULL REFERENCES runs(id),
 source_id TEXT NOT NULL REFERENCES research_nodes(id),PRIMARY KEY(run_id,source_id));
CREATE TABLE research_edges(parent TEXT NOT NULL REFERENCES research_nodes(id),
 child TEXT NOT NULL REFERENCES research_nodes(id),PRIMARY KEY(parent,child));
""",
    """
CREATE TABLE source_locations(url TEXT NOT NULL,
 source_id TEXT PRIMARY KEY REFERENCES research_nodes(id),
 raw_digest TEXT NOT NULL,retrieved_at TEXT NOT NULL);
CREATE INDEX source_location_url ON source_locations(url);
""",
    """
CREATE TABLE director_state(run_id TEXT PRIMARY KEY REFERENCES runs(id),
 policy_json TEXT NOT NULL,stopped_reason TEXT);
CREATE TABLE hypotheses(id TEXT NOT NULL,run_id TEXT NOT NULL REFERENCES runs(id),
 identity TEXT NOT NULL,parent_id TEXT,depth INTEGER NOT NULL,
 domain TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,revision_evidence TEXT,score REAL,
 PRIMARY KEY(run_id,id),UNIQUE(run_id,identity),
 FOREIGN KEY(run_id,parent_id) REFERENCES hypotheses(run_id,id));
CREATE TABLE branch_allocations(run_id TEXT NOT NULL REFERENCES runs(id),step_key TEXT NOT NULL,
 hypothesis_id TEXT NOT NULL,mode TEXT NOT NULL,ordinal INTEGER NOT NULL,
 PRIMARY KEY(run_id,step_key),UNIQUE(run_id,ordinal),
 FOREIGN KEY(run_id,hypothesis_id) REFERENCES hypotheses(run_id,id));
CREATE TABLE branch_results(run_id TEXT NOT NULL,hypothesis_id TEXT NOT NULL,
 report_digest TEXT NOT NULL,passed INTEGER NOT NULL,
 PRIMARY KEY(run_id,hypothesis_id,report_digest),
 FOREIGN KEY(run_id,hypothesis_id) REFERENCES hypotheses(run_id,id));
CREATE TABLE progress_guards(run_id TEXT NOT NULL REFERENCES runs(id),task_id TEXT NOT NULL,
 state_json TEXT NOT NULL,PRIMARY KEY(run_id,task_id));
""",
    """
CREATE TABLE market_opportunities(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),
 candidate_id TEXT NOT NULL,artifact_digest TEXT NOT NULL);
CREATE TABLE market_current(run_id TEXT NOT NULL REFERENCES runs(id),candidate_id TEXT NOT NULL,
 opportunity_id TEXT NOT NULL REFERENCES market_opportunities(id),PRIMARY KEY(run_id,candidate_id));
CREATE TABLE market_evidence(id TEXT PRIMARY KEY,
 opportunity_id TEXT NOT NULL REFERENCES market_opportunities(id),artifact_digest TEXT NOT NULL,
 origin TEXT NOT NULL);
CREATE TABLE market_reviews(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,
 evidence_id TEXT NOT NULL REFERENCES market_evidence(id),artifact_digest TEXT NOT NULL);
""",
    """
CREATE TABLE experiment_jobs(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(id),
 stage_version INTEGER NOT NULL,replication INTEGER NOT NULL,plan_digest TEXT NOT NULL,
 status TEXT NOT NULL,owner TEXT,fence INTEGER NOT NULL,lease_until REAL,
 attempts INTEGER NOT NULL,error_count INTEGER NOT NULL,worker_pid INTEGER,worker_created_at REAL,
 artifact_digest TEXT,last_error TEXT,UNIQUE(run_id,stage_version,replication));
""",
    """
CREATE TABLE work_queue(run_id TEXT PRIMARY KEY REFERENCES runs(id),status TEXT NOT NULL,
 owner TEXT,fence INTEGER NOT NULL,lease_until REAL,available_at REAL NOT NULL,
 attempts INTEGER NOT NULL,completed_steps INTEGER NOT NULL,
 last_error TEXT,updated_at TEXT NOT NULL);
""",
)
