import pandas as pd

from transform import normalize_calls, select_canonical_calls


def test_normalize_standardizes_headers_values_and_timestamps():
    raw = pd.DataFrame(
        {
            " Call_ID ": [" c-1 "],
            "AGENT_ID": [" a001 "],
            "Channel": [" voice "],
            "Call_Outcome": [" handled "],
            "Queue_Name": [" queue a "],
            "Created_At": ["2026-01-01 10:00:00"],
            "Updated_At": ["2026-01-01 10:05:00"],
            "Talk_Seconds": ["120"],
        }
    )
    result = normalize_calls(raw)

    assert "call_id" in result.columns
    assert result.loc[0, "call_id"] == "c-1"
    assert result.loc[0, "agent_id"] == "A001"
    assert result.loc[0, "channel"] == "VOICE"
    assert result.loc[0, "call_outcome"] == "HANDLED"
    assert pd.notna(result.loc[0, "created_at"])
    assert result.loc[0, "talk_seconds"] == 120


def test_canonical_selection_keeps_latest_update_and_counts_removed_versions():
    calls = pd.DataFrame(
        {
            "call_id": ["C1", "C1", "C2"],
            "updated_at": pd.to_datetime(
                ["2026-01-01 10:00:00", "2026-01-01 11:00:00", "2026-01-01 09:00:00"]
            ),
            "_source_row_number": [2, 3, 4],
        }
    )
    canonical, removed = select_canonical_calls(calls)

    assert removed == 1
    assert len(canonical) == 2
    assert canonical.loc[canonical["call_id"] == "C1", "updated_at"].iloc[0] == pd.Timestamp("2026-01-01 11:00:00")


def test_canonical_selection_retains_rows_with_missing_call_id():
    calls = pd.DataFrame(
        {
            "call_id": ["C1", pd.NA],
            "updated_at": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-01 10:01:00"]),
            "_source_row_number": [2, 3],
        }
    )
    canonical, removed = select_canonical_calls(calls)

    assert len(canonical) == 2
    assert removed == 0
    assert canonical["call_id"].isna().sum() == 1
