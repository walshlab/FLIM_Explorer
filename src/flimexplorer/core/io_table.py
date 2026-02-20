# core/io_table.py
from __future__ import annotations

import io
import pandas as pd
import numpy as np

# Columns that should never appear as Group/Hue dropdown choices
EXCLUDE_GROUP_COLS = {
    "__rowid__", "_rowid",
    "nadh_folder", "nadh_stem",
    "fad_folder", "fad_stem",
    "mask_path",
    "Common Name",
    "Image Number", "Cell Number",  # optional
    "spc_warnings",
    "outliers",
}
EXCLUDE_METRIC_COLS = {"mask_id", "Image Number", "Cell Number","row"}

def read_table_from_upload(contents: bytes, filename: str) -> pd.DataFrame:
    fn = (filename or "").lower().strip()

    # Excel (modern)
    if fn.endswith(".xlsx") or fn.endswith(".xlsm") or fn.endswith(".xltx") or fn.endswith(".xltm"):
        return pd.read_excel(io.BytesIO(contents), engine="openpyxl")

    # Excel (legacy .xls) — requires xlrd<2.0, OR ask user to resave as .xlsx
    if fn.endswith(".xls"):
        
        try:
            return pd.read_excel(io.BytesIO(contents), engine="xlrd")
        except Exception as e:
            raise RuntimeError(
                "This looks like a legacy .xls file. Please re-save it as .xlsx (recommended), "
                "or install xlrd<2.0 (e.g., pip install 'xlrd<2')."
            ) from e

    # TSV
    if fn.endswith(".tsv"):
        return pd.read_csv(io.BytesIO(contents), sep="\t")

    # CSV (default)
    if fn.endswith(".csv") or fn.endswith(".txt") or fn == "":
        return pd.read_csv(io.BytesIO(contents))

    # Fallback: try CSV then XLSX
    try:
        return pd.read_csv(io.BytesIO(contents))
    except Exception:
        return pd.read_excel(io.BytesIO(contents), engine="openpyxl")


def infer_candidates(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    metrics = df.select_dtypes(include=[np.number]).columns.tolist()
    metrics = [c for c in metrics if c not in EXCLUDE_METRIC_COLS] # filter out non-metrics

    groups  = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # Drop internal columns that shouldn't be used for grouping/hue
    groups = [c for c in groups if c not in EXCLUDE_GROUP_COLS]

    prefer = ['Group','TimePoint','Condition','Treatment','Label',
              'group','timepoint','condition','treatment','label']
    groups = sorted(groups, key=lambda c: (c not in prefer, groups.index(c)))
    return metrics, groups


def ensure_outlier_col(df: pd.DataFrame) -> pd.DataFrame:
    if "outliers" not in df.columns:
        df = df.copy()
        df["outliers"] = False
        return df

    df = df.copy()
    s = df["outliers"]

    if pd.api.types.is_bool_dtype(s):
        return df

    def _to_bool(x):
        if pd.isna(x):
            return False
        if isinstance(x, (bool, np.bool_)):
            return bool(x)
        if isinstance(x, (int, float, np.integer, np.floating)):
            return bool(int(x))
        t = str(x).strip().lower()
        if t in ("true", "t", "yes", "y", "1"):
            return True
        if t in ("false", "f", "no", "n", "0", ""):
            return False
        return False

    df["outliers"] = s.map(_to_bool).astype(bool)
    return df

import base64

def read_df_from_dash_upload(contents, filename: str) -> pd.DataFrame:
    """
    Decode Dash dcc.Upload contents and read into a DataFrame.
    Handles list payloads, base64 decoding, and XLSX sanity check.
    """
    if not contents:
        raise ValueError("No upload contents.")

    if isinstance(contents, list):
        contents = contents[0] if contents else None

    if not contents or not isinstance(contents, str) or "," not in contents:
        raise ValueError("Malformed upload payload (expected base64 data URI).")

    header, b64data = contents.split(",", 1)
    if "base64" not in header.lower():
        raise ValueError("Upload header not base64.")

    raw = base64.b64decode(b64data)

    fn = (filename or "").lower().strip()
    if fn.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")) and not raw.startswith(b"PK"):
        raise ValueError(f"{filename} does not look like a valid XLSX (expected PK zip header).")

    return read_table_from_upload(raw, filename or "upload")
