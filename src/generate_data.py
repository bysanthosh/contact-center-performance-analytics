"""Generate reproducible, entirely synthetic contact center CSV data.

Default portfolio dataset: 5,000 offered calls per month from Jan 2024 through
Dec 2026 (180,000 base calls), with a small amount of intentional duplicate
versioning and data-quality defects for ETL demonstration.

Run from the repository root:
    python src/generate_data.py
    python src/generate_data.py --calls-per-month 5000 --start-year 2024 --months 36
"""
from __future__ import annotations

import argparse
import calendar
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CALL_COLUMNS = [
    "call_id", "created_at", "updated_at", "agent_id", "channel",
    "call_outcome", "queue_name", "offered_flag", "handled_flag",
    "ivr_contained_flag", "abandoned_flag", "wait_seconds", "talk_seconds",
    "hold_seconds", "after_call_work_seconds", "sla_threshold_seconds",
]


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1)


def generate_data(
    calls_per_month: int = 5_000,
    start_year: int = 2024,
    months: int = 36,
    seed: int = 20261027,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return raw call rows (including injected defects) and agent reference rows."""
    if calls_per_month < 100:
        raise ValueError("calls_per_month must be at least 100 so defect injection remains meaningful")
    if not 1 <= months <= 120:
        raise ValueError("months must be between 1 and 120")

    rng = random.Random(seed)
    agents = []
    for i in range(1, 101):
        agents.append({
            "agent_id": f"AG{i:03d}",
            "agent_name": f"Agent {i:03d}",
            "team_name": f"Team {((i - 1) // 10) + 1}",
            "site_name": ["Chennai", "Coimbatore", "Bengaluru"][((i - 1) // 34) % 3],
        })
    agent_ids = [a["agent_id"] for a in agents]
    queues = ["GENERAL", "PAYMENTS", "SERVICING", "ESCALATIONS"]
    outcomes = ["HANDLED", "ABANDONED", "IVR_CONTAINED"]

    records: list[dict] = []
    call_number = 1
    for month_offset in range(months):
        year = start_year + (month_offset // 12)
        month = (month_offset % 12) + 1
        days_in_month = calendar.monthrange(year, month)[1]
        month_start = _month_start(year, month)
        for _ in range(calls_per_month):
            created = month_start + timedelta(
                days=rng.randint(0, days_in_month - 1),
                seconds=rng.randint(0, 86399),
            )
            updated = created + timedelta(seconds=rng.randint(0, 7200))
            outcome = rng.choices(outcomes, weights=[0.72, 0.16, 0.12], k=1)[0]
            offered = 1
            handled = int(outcome == "HANDLED")
            contained = int(outcome == "IVR_CONTAINED")
            abandoned = int(outcome == "ABANDONED")
            channel = "IVR" if contained else "VOICE"
            agent_id = rng.choice(agent_ids) if handled else ""

            # Handled-call queue waits average about 77 seconds, with realistic
            # variation around the requested 60–90 second ASA target. Other
            # outcomes have different wait profiles and are not included in ASA.
            if handled:
                wait = int(round(rng.triangular(15, 150, 65)))
            elif abandoned:
                wait = rng.randint(25, 420)
            else:
                wait = rng.randint(0, 20)

            talk = rng.randint(180, 720) if handled else ""
            hold = rng.randint(0, 150) if handled else ""
            acw = rng.randint(30, 180) if handled else ""
            records.append({
                "call_id": f"CALL{call_number:08d}",
                "created_at": _timestamp(created),
                "updated_at": _timestamp(updated),
                "agent_id": agent_id,
                "channel": channel,
                "call_outcome": outcome,
                "queue_name": rng.choice(queues),
                "offered_flag": offered,
                "handled_flag": handled,
                "ivr_contained_flag": contained,
                "abandoned_flag": abandoned,
                "wait_seconds": wait,
                "talk_seconds": talk,
                "hold_seconds": hold,
                "after_call_work_seconds": acw,
                "sla_threshold_seconds": 60,
            })
            call_number += 1

    base_rows = len(records)
    # Inject about 1% duplicate versions, with later update timestamps.
    duplicate_count = max(1, base_rows // 100)
    duplicate_indices = rng.sample(range(base_rows), duplicate_count)
    for idx in duplicate_indices:
        duplicate = records[idx].copy()
        original_updated = datetime.strptime(duplicate["updated_at"], "%Y-%m-%d %H:%M:%S")
        duplicate["updated_at"] = _timestamp(original_updated + timedelta(minutes=5))
        duplicate["queue_name"] = rng.choice(queues)
        records.append(duplicate)

    # Inject defects into about 0.5% of base records for realistic ETL quarantine.
    defect_count = max(10, base_rows // 200)
    defect_indices = rng.sample(range(base_rows), defect_count)
    for position, idx in enumerate(defect_indices):
        row = records[idx]
        if position % 5 == 0:
            row["agent_id"] = "AG999"
            row["handled_flag"] = 1
            row["call_outcome"] = "HANDLED"
            row["ivr_contained_flag"] = 0
            row["abandoned_flag"] = 0
            row["channel"] = "VOICE"
            row["talk_seconds"] = row["talk_seconds"] if row["talk_seconds"] != "" else 300
            row["hold_seconds"] = row["hold_seconds"] if row["hold_seconds"] != "" else 30
            row["after_call_work_seconds"] = row["after_call_work_seconds"] if row["after_call_work_seconds"] != "" else 60
        elif position % 5 == 1:
            row["created_at"] = "not-a-timestamp"
        elif position % 5 == 2:
            row["talk_seconds"] = -5
            row["handled_flag"] = 1
            row["call_outcome"] = "HANDLED"
            row["ivr_contained_flag"] = 0
            row["abandoned_flag"] = 0
            row["channel"] = "VOICE"
            row["agent_id"] = rng.choice(agent_ids)
            row["hold_seconds"] = 10
            row["after_call_work_seconds"] = 20
        elif position % 5 == 3:
            row["call_id"] = ""
        else:
            row["call_outcome"] = "UNKNOWN_OUTCOME"

    calls_df = pd.DataFrame(records, columns=CALL_COLUMNS)
    agents_df = pd.DataFrame(agents, columns=["agent_id", "agent_name", "team_name", "site_name"])
    return calls_df, agents_df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls-per-month", type=int, default=5_000)
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--months", type=int, default=36)
    parser.add_argument("--seed", type=int, default=20261027)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    calls_df, agents_df = generate_data(
        calls_per_month=args.calls_per_month,
        start_year=args.start_year,
        months=args.months,
        seed=args.seed,
    )
    calls_path = RAW_DIR / "calls_raw.csv"
    agents_path = RAW_DIR / "agents_raw.csv"
    calls_df.to_csv(calls_path, index=False)
    agents_df.to_csv(agents_path, index=False)

    print(f"Generated raw call rows (including duplicate versions): {len(calls_df):,} -> {calls_path.relative_to(PROJECT_ROOT)}")
    print(f"Base calls: {args.calls_per_month * args.months:,} across {args.months} months")
    print(f"Generated agents: {len(agents_df):,} -> {agents_path.relative_to(PROJECT_ROOT)}")
    print("Synthetic data only. Duplicate versions and validation defects are intentional.")


if __name__ == "__main__":
    main()
