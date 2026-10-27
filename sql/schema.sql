-- SQLite schema contract for the Contact Center Analytics project.
-- The Python loader currently creates fact_calls and dim_agents from validated data.
-- This script documents the intended schema and can be used to initialize a fresh database.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    site_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_calls (
    call_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    agent_id TEXT,
    channel TEXT NOT NULL,
    call_outcome TEXT NOT NULL,
    queue_name TEXT NOT NULL,
    offered_flag INTEGER NOT NULL CHECK (offered_flag IN (0, 1)),
    handled_flag INTEGER NOT NULL CHECK (handled_flag IN (0, 1)),
    ivr_contained_flag INTEGER NOT NULL CHECK (ivr_contained_flag IN (0, 1)),
    abandoned_flag INTEGER NOT NULL CHECK (abandoned_flag IN (0, 1)),
    wait_seconds INTEGER NOT NULL CHECK (wait_seconds >= 0),
    talk_seconds INTEGER,
    hold_seconds INTEGER,
    after_call_work_seconds INTEGER,
    sla_threshold_seconds INTEGER NOT NULL CHECK (sla_threshold_seconds >= 0),
    FOREIGN KEY (agent_id) REFERENCES dim_agents(agent_id)
);

CREATE INDEX IF NOT EXISTS ix_fact_calls_created_at ON fact_calls(created_at);
CREATE INDEX IF NOT EXISTS ix_fact_calls_agent_id ON fact_calls(agent_id);
CREATE INDEX IF NOT EXISTS ix_fact_calls_outcome ON fact_calls(call_outcome);
