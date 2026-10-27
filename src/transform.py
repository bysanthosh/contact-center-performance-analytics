"""Deterministic normalization and canonical-record selection."""
import pandas as pd

DURATION_COLUMNS = [
    "wait_seconds", "talk_seconds", "hold_seconds", "after_call_work_seconds"
]
INTEGER_COLUMNS = [
    "offered_flag", "handled_flag", "ivr_contained_flag", "abandoned_flag",
    "wait_seconds", "talk_seconds", "hold_seconds", "after_call_work_seconds",
    "sla_threshold_seconds",
]
CATEGORICAL_COLUMNS = ["channel", "call_outcome", "queue_name", "agent_id"]


def normalize_calls(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers, whitespace, categories, timestamps, and numeric types."""
    df = raw.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    for col in ["call_id", "agent_id", "channel", "call_outcome", "queue_name"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
            df[col] = df[col].replace("", pd.NA)
    for col in ["channel", "call_outcome", "queue_name", "agent_id"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.upper()
    for col in ["created_at", "updated_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in INTEGER_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace("", pd.NA), errors="coerce")
    return df


def select_canonical_calls(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep one version per non-empty call_id, preferring latest valid updated_at.

    If updated_at ties, the last source row wins. If all versions for an ID have
    invalid update timestamps, the last source row wins so it can be quarantined.
    Rows with missing call_id cannot be grouped and are retained individually for
    record-level validation.
    """
    work = df.copy()
    if "_source_row_number" not in work.columns:
        work["_source_row_number"] = range(2, len(work) + 2)

    has_id = work["call_id"].notna() & work["call_id"].astype("string").str.strip().ne("")
    identified = work.loc[has_id].copy()
    unidentified = work.loc[~has_id].copy()

    if identified.empty:
        canonical = work.sort_values("_source_row_number", kind="stable")
        return canonical.reset_index(drop=True), 0

    identified["_has_valid_update"] = identified["updated_at"].notna()
    identified = identified.sort_values(
        ["call_id", "_has_valid_update", "updated_at", "_source_row_number"],
        ascending=[True, True, True, True],
        na_position="first",
        kind="stable",
    )
    chosen = identified.groupby("call_id", sort=False, dropna=False).tail(1)
    canonical = pd.concat([chosen, unidentified], ignore_index=False)
    canonical = canonical.sort_values("_source_row_number", kind="stable").drop(
        columns=["_has_valid_update"], errors="ignore"
    )
    removed_versions = len(df) - len(canonical)
    return canonical.reset_index(drop=True), removed_versions
