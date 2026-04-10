from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def load_parquet(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_parquet(path, **kwargs)


def load_excel(path: Path, sheet_name: str | int = 0, **kwargs: Any) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, **kwargs)
