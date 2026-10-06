CREATE TABLE IF NOT EXISTS jobs (
 id text PRIMARY KEY,
 idempotency_key text NOT NULL UNIQUE,
 request_hash text NOT NULL,
 fixture text NOT NULL,
 algorithm text NOT NULL,
 state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','running','succeeded','failed')),
 attempt integer NOT NULL DEFAULT 0,
 lease_until timestamptz,
 report jsonb,
 revision text,
 created_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz
);
CREATE TABLE IF NOT EXISTS outbox (
 job_id text PRIMARY KEY REFERENCES jobs(id),
 published_at timestamptz
);
-- Additive local migration preserves job history from the initial quickstart.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS trace_parent text NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS report_object jsonb;
ALTER TABLE outbox ADD COLUMN IF NOT EXISTS lease_until timestamptz;
ALTER TABLE outbox ADD COLUMN IF NOT EXISTS token integer NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS local_queue (
 job_id text PRIMARY KEY REFERENCES jobs(id),
 available_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS attempts (
 job_id text NOT NULL REFERENCES jobs(id),
 token integer NOT NULL,
 revision text NOT NULL,
 started_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz,
 PRIMARY KEY(job_id, token)
);
