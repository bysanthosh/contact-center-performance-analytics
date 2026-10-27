"""Record-level validation and quarantine reason generation."""
import pandas as pd

ALLOWED_CHANNELS = {"VOICE", "IVR"}
ALLOWED_OUTCOMES = {"HANDLED", "ABANDONED", "IVR_CONTAINED"}


def validate_calls(calls: pd.DataFrame, agents: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (valid_calls, quarantined_calls), each with a validation_reasons field."""
    df = calls.copy()
    valid_agent_ids = set(
        agents["agent_id"].dropna().astype("string").str.strip().str.upper().tolist()
    )
    reasons_by_row: list[list[str]] = []

    for _, row in df.iterrows():
        reasons: list[str] = []

        if pd.isna(row.get("call_id")) or not str(row.get("call_id", "")).strip():
            reasons.append("MISSING_CALL_ID")

        created = row.get("created_at")
        updated = row.get("updated_at")
        if pd.isna(created):
            reasons.append("INVALID_CREATED_AT")
        if pd.isna(updated):
            reasons.append("INVALID_UPDATED_AT")
        if pd.notna(created) and pd.notna(updated) and updated < created:
            reasons.append("UPDATED_BEFORE_CREATED")

        channel = row.get("channel")
        outcome = row.get("call_outcome")
        if pd.isna(channel) or channel not in ALLOWED_CHANNELS:
            reasons.append("INVALID_CHANNEL")
        if pd.isna(outcome) or outcome not in ALLOWED_OUTCOMES:
            reasons.append("INVALID_CALL_OUTCOME")

        # Validate flags are 0/1 and outcome flags agree with the outcome.
        flag_cols = ["offered_flag", "handled_flag", "ivr_contained_flag", "abandoned_flag"]
        flags_ok = True
        for col in flag_cols:
            value = row.get(col)
            if pd.isna(value) or value not in (0, 1):
                reasons.append(f"INVALID_{col.upper()}")
                flags_ok = False

        if flags_ok:
            if row["offered_flag"] != 1:
                reasons.append("NOT_OFFERED_RECORD")
            expected = {
                "HANDLED": (1, 0, 0),
                "ABANDONED": (0, 0, 1),
                "IVR_CONTAINED": (0, 1, 0),
            }.get(outcome)
            if expected is not None:
                actual = (row["handled_flag"], row["ivr_contained_flag"], row["abandoned_flag"])
                if actual != expected:
                    reasons.append("OUTCOME_FLAG_MISMATCH")
            if outcome == "IVR_CONTAINED" and channel != "IVR":
                reasons.append("IVR_OUTCOME_CHANNEL_MISMATCH")
            if outcome in {"HANDLED", "ABANDONED"} and channel != "VOICE":
                reasons.append("VOICE_OUTCOME_CHANNEL_MISMATCH")

        # Threshold and wait are needed to assess service level for all offered calls.
        for col in ["wait_seconds", "sla_threshold_seconds"]:
            value = row.get(col)
            if pd.isna(value) or value < 0:
                reasons.append(f"INVALID_{col.upper()}")

        for col in ["talk_seconds", "hold_seconds", "after_call_work_seconds"]:
            value = row.get(col)
            if row.get("handled_flag") == 1:
                if pd.isna(value):
                    reasons.append(f"MISSING_{col.upper()}_FOR_HANDLED_CALL")
                elif value < 0:
                    reasons.append(f"NEGATIVE_{col.upper()}")
            elif pd.notna(value) and value < 0:
                reasons.append(f"NEGATIVE_{col.upper()}")

        if row.get("handled_flag") == 1:
            agent_id = row.get("agent_id")
            if pd.isna(agent_id) or str(agent_id).strip().upper() not in valid_agent_ids:
                reasons.append("INVALID_AGENT_REFERENCE")
        elif pd.notna(row.get("agent_id")) and str(row.get("agent_id")).strip().upper() not in valid_agent_ids:
            # A supplied but invalid reference is still a data quality defect.
            reasons.append("INVALID_AGENT_REFERENCE")

        reasons_by_row.append(sorted(set(reasons)))

    df["validation_reasons"] = ["|".join(reasons) for reasons in reasons_by_row]
    valid = df.loc[df["validation_reasons"].eq("")].copy()
    quarantine = df.loc[~df["validation_reasons"].eq("")].copy()
    return valid, quarantine
