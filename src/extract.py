"""Input extraction helpers for the contact center pipeline."""
from pathlib import Path
import pandas as pd


def read_input_csv(path: str | Path, required_columns: list[str], label: str) -> pd.DataFrame:
    """Read a CSV and fail clearly if the file or required columns are missing."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"{label} CSV not found: {csv_path}")
    frame = pd.read_csv(csv_path, dtype="string", keep_default_na=False)
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} CSV is missing required columns: {missing}")
    frame["_source_row_number"] = range(2, len(frame) + 2)  # header is row 1
    return frame
