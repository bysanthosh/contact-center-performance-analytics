import pandas as pd

from transform import normalize_calls
from validate import validate_calls


def _call_row(**overrides):
    row = {
        "call_id": "C100",
        "created_at": "2026-01-01 10:00:00",
        "updated_at": "2026-01-01 10:05:00",
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
    }
    row.update(overrides)
    return row


def test_valid_handled_call_is_accepted():
    calls = normalize_calls(pd.DataFrame([_call_row()]))
    agents = pd.DataFrame({"agent_id": ["A001"]})

    accepted, rejected = validate_calls(calls, agents)

    assert len(accepted) == 1
    assert len(rejected) == 0
    assert accepted.iloc[0]["validation_reasons"] == ""


def test_invalid_handled_agent_is_quarantined():
    calls = normalize_calls(pd.DataFrame([_call_row(agent_id="A999")]))
    agents = pd.DataFrame({"agent_id": ["A001"]})

    accepted, rejected = validate_calls(calls, agents)

    assert len(accepted) == 0
    assert len(rejected) == 1
    assert "INVALID_AGENT_REFERENCE" in rejected.iloc[0]["validation_reasons"]


def test_negative_talk_duration_is_quarantined():
    calls = normalize_calls(pd.DataFrame([_call_row(talk_seconds=-1)]))
    agents = pd.DataFrame({"agent_id": ["A001"]})

    accepted, rejected = validate_calls(calls, agents)

    assert len(accepted) == 0
    assert len(rejected) == 1
    assert "NEGATIVE_TALK_SECONDS" in rejected.iloc[0]["validation_reasons"]
