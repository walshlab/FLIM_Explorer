# flimexplorer/app_utils.py
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd


def df_to_store(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df2 = df.copy()
    df2["_rowid"] = df2.index.astype(int)
    return df2.to_dict("records")


def store_to_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    if "_rowid" in df.columns:
        df = df.set_index("_rowid", drop=True)
    return df
