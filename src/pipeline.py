"""Run the contact center synthetic-data ETL pipeline."""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from extract import read_input_csv
from load import load_tables
from transform import normalize_calls, select_canonical_calls
from validate import validate_calls

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CALL_COLUMNS = [
    "call_id", "created_at", "updated_at", "agent_id", "channel",
    "call_outcome", "queue_name", "offered_flag", "handled_flag",
    "ivr_contained_flag", "abandoned_flag", "wait_seconds", "talk_seconds",
    "hold_seconds", "after_call_work_seconds", "sla_threshold_seconds",
]
AGENT_COLUMNS = ["agent_id", "agent_name", "team_name", "site_name"]


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )


def run_pipeline(
    calls_path: str | Path | None = None,
    agents_path: str | Path | None = None,
    db_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict:
    calls_path = Path(calls_path or PROJECT_ROOT / "data/raw/calls_raw.csv")
    agents_path = Path(agents_path or PROJECT_ROOT / "data/raw/agents_raw.csv")
    db_path = Path(db_path or PROJECT_ROOT / "data/contact_center.sqlite")
    output_dir = Path(output_dir or PROJECT_ROOT / "data")
    processed_dir = output_dir / "processed"
    quarantine_dir = output_dir / "quarantine"
    reports_dir = PROJECT_ROOT / "reports"
    log_path = Path(log_path or PROJECT_ROOT / "logs/pipeline.log")
    for directory in [processed_dir, quarantine_dir, reports_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    configure_logging(log_path)
    logger = logging.getLogger("contact_center_pipeline")

    logger.info("Pipeline started")
    raw_calls = read_input_csv(calls_path, CALL_COLUMNS, "Calls")
    raw_agents = read_input_csv(agents_path, AGENT_COLUMNS, "Agents")
    source_count = len(raw_calls)
    logger.info("Extracted %s call rows and %s agent rows", source_count, len(raw_agents))

    agents = raw_agents.copy()
    for col in ["agent_id", "agent_name", "team_name", "site_name"]:
        agents[col] = agents[col].astype("string").str.strip()
    agents["agent_id"] = agents["agent_id"].str.upper()
    if agents["agent_id"].isna().any() or agents["agent_id"].duplicated().any():
        raise ValueError("Agent reference data contains missing or duplicate agent_id values")

    normalized = normalize_calls(raw_calls)
    canonical, duplicate_versions_removed = select_canonical_calls(normalized)
    logger.info(
        "Canonical selection complete: source=%s, duplicate_versions_removed=%s, canonical=%s",
        source_count, duplicate_versions_removed, len(canonical)
    )

    valid, quarantine = validate_calls(canonical, agents)
    logger.info("Validation complete: accepted=%s rejected=%s", len(valid), len(quarantine))

    # Keep the original source row reference in quarantine for auditability.
    valid.drop(columns=["validation_reasons"], errors="ignore").to_csv(
        processed_dir / "calls_validated.csv", index=False
    )
    quarantine.to_csv(quarantine_dir / "calls_quarantine.csv", index=False)

    loaded_count = load_tables(valid, agents, db_path)
    reason_counts = Counter()
    for reason_string in quarantine["validation_reasons"].fillna(""):
        for reason in filter(None, reason_string.split("|")):
            reason_counts[reason] += 1

    # These counts are intentionally distinct; duplicate versions are not counted as
    # accepted/rejected canonical records.
    report = {
        "source_rows": int(source_count),
        "duplicate_version_rows_removed": int(duplicate_versions_removed),
        "canonical_rows_evaluated": int(len(canonical)),
        "accepted_canonical_rows": int(len(valid)),
        "rejected_canonical_rows": int(len(quarantine)),
        "loaded_rows": int(loaded_count),
        "rejection_reason_counts": dict(sorted(reason_counts.items())),
        "reconciliation": {
            "canonical_rows_equal_accepted_plus_rejected": bool(
                len(canonical) == len(valid) + len(quarantine)
            ),
            "accepted_rows_equal_loaded_rows": bool(len(valid) == loaded_count),
        },
    }
    report_path = reports_dir / "data_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if len(canonical) != len(valid) + len(quarantine):
        raise RuntimeError("Canonical reconciliation failed: accepted + rejected != canonical")
    if len(valid) != loaded_count:
        raise RuntimeError("Load reconciliation failed: accepted != loaded")

    logger.info("Pipeline completed successfully. Report: %s", report_path)
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", help="Path to calls CSV")
    parser.add_argument("--agents", help="Path to agents CSV")
    parser.add_argument("--db", help="SQLite database path")
    parser.add_argument("--output-dir", help="Directory containing processed/ and quarantine/")
    parser.add_argument("--log", help="Log file path")
    args = parser.parse_args()
    run_pipeline(args.calls, args.agents, args.db, args.output_dir, args.log)


if __name__ == "__main__":
    main()
