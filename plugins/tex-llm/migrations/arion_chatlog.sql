-- arion_chatlog — durable store for the T-Ex LLM realtime chat-brain
-- (hooks/chat-capture.mjs, fired on the Stop event).
--
-- Applying this migration is OPTIONAL per project: the hook always writes the local
-- JSONL log (.claude/chat-log.jsonl) and degrades to JSONL-only when this table is
-- absent or no DB credentials are configured — the DB post is best-effort and can
-- never block or fail a turn. Apply it to a project's own Postgres/Supabase database
-- to get the durable, queryable store. Idempotent — safe to run more than once.

CREATE TABLE IF NOT EXISTS arion_chatlog (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  branch text,
  session_id text,
  ts timestamptz,
  user_text text,
  assistant_text text,
  tools jsonb,
  files jsonb,
  harnesses jsonb,
  blocks jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS arion_chatlog_branch_created_at_idx
  ON arion_chatlog (branch, created_at DESC);

CREATE INDEX IF NOT EXISTS arion_chatlog_session_id_idx
  ON arion_chatlog (session_id);

-- RLS enabled with NO policies: anon/authenticated roles are locked out entirely;
-- only the service role (which bypasses RLS) can read or write. Idempotent.
ALTER TABLE arion_chatlog ENABLE ROW LEVEL SECURITY;
