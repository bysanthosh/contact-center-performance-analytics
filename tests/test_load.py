import sqlite3

import pandas as pd

from load import load_tables


def _calls():
    return pd.DataFrame(
        [
            {
                "call_id": "C1",
                "created_at": pd.Timestamp("2026-01-01 10:00:00"),
                "updated_at": pd.Timestamp("2026-01-01 10:05:00"),
                "agent_id": "A001",
                "channel": "VOICE",
                "call_outcome": "HANDLED",
                "queue_name": "QUEUE_A",
                "offered_flag": 1,
                "handled_flag": 1,
                "ivr_contained_flag": 0,
                "abandoned_flag": 0,
                "wait_seconds": 30,
                "talk_seconds": 300,
                "hold_seconds": 20,
                "after_call_work_seconds": 40,
                "sla_threshold_seconds": 60,
                "validation_reasons": "",
                "_source_row_number": 2,
            }
        ]
    )


def _agents():
    return pd.DataFrame(
        [{"agent_id": "A001", "agent_name": "Agent 001", "team_name": "Team 1", "site_name": "Site A"}]
    )


def test_load_creates_fact_and_dimension_tables(tmp_path):
    db_path = tmp_path / "test.sqlite"
    loaded = load_tables(_calls(), _agents(), db_path)

    with sqlite3.connect(db_path) as connection:
        assert loaded == 1
        assert connection.execute("SELECT COUNT(*) FROM fact_calls").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM dim_agents").fetchone()[0] == 1
        assert connection.execute("SELECT call_id FROM fact_calls").fetchone()[0] == "C1"


def test_load_replaces_snapshot_instead_of_appending(tmp_path):
    db_path = tmp_path / "test.sqlite"
    load_tables(_calls(), _agents(), db_path)
    load_tables(_calls(), _agents(), db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM fact_calls").fetchone()[0] == 1
