"""SQLite loading helpers with transactional replace semantics."""
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text


def sqlite_engine(db_path: str | Path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path.as_posix()}", future=True)


def load_tables(
    calls: pd.DataFrame,
    agents: pd.DataFrame,
    db_path: str | Path,
) -> int:
    """Load valid calls and agent reference data in one transaction.

    Tables are replaced as a consistent snapshot on each run. This makes the
    pipeline rerunnable and avoids duplicate inserts when the same input is rerun.
    """
    engine = sqlite_engine(db_path)
    call_output = calls.drop(
        columns=["_source_row_number", "validation_reasons"], errors="ignore"
    ).copy()
    agent_output = agents.drop(columns=["_source_row_number"], errors="ignore").copy()

    # SQLite stores timestamps as ISO-formatted strings for portability.
    for col in ["created_at", "updated_at"]:
        if col in call_output.columns:
            call_output[col] = call_output[col].apply(
                lambda value: value.isoformat(sep=" ") if pd.notna(value) else None
            )

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS fact_calls"))
        connection.execute(text("DROP TABLE IF EXISTS dim_agents"))
        agent_output.to_sql("dim_agents", connection, if_exists="replace", index=False)
        call_output.to_sql("fact_calls", connection, if_exists="replace", index=False)
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_fact_calls_created_at ON fact_calls(created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_fact_calls_agent_id ON fact_calls(agent_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_calls_call_id ON fact_calls(call_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_agents_agent_id ON dim_agents(agent_id)"))
        loaded_count = connection.execute(text("SELECT COUNT(*) FROM fact_calls")).scalar_one()
    engine.dispose()
    return int(loaded_count)
