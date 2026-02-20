# core/spc_import.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import numpy as np
import pandas as pd
import imageio.v2 as imageio

RESOLUTION = 256


# -----------------------------
# Config for suffix patterns
# -----------------------------
@dataclass
class AscSuffixConfig:
    """
    Format strings that build filenames from a *base stem* (no extension).
    The format variable is: {stem}

    Examples:
      a1 = "{stem}_a1[%].asc"
      photons = "{stem}_photons.asc"
    """
    a1: str = "{stem}_a1[%].asc"
    t1: str = "{stem}_t1.asc"
    t2: str = "{stem}_t2.asc"
    photons: str = "{stem}_photons.asc"

    def build(self, stem_base: str, kind: str) -> str:
        pat = getattr(self, kind)
        fn = pat.format(stem=stem_base)
        if not fn.lower().endswith(".asc"):
            raise ValueError(f"{kind} pattern must end with .asc, got: {fn}")
        return fn


# -----------------------------
# Column normalization
# -----------------------------
def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in str(s) if ch.isalnum() or ch == "_")


def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Return the first matching column name in df for any candidate (case/space tolerant).
    """
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        key = _norm(cand)
        if key in norm_map:
            return norm_map[key]
    return None


def _require_cols(df: pd.DataFrame, required: Dict[str, List[str]]) -> Tuple[Dict[str, str], List[str]]:
    """
    required: canonical_name -> list of candidate input headers
    Returns (mapping canonical->actualcol, missing_canonical_names)
    """
    mapping: Dict[str, str] = {}
    missing: List[str] = []
    for canon, cands in required.items():
        found = _find_col(df, cands)
        if not found:
            missing.append(canon)
        else:
            mapping[canon] = found
    return mapping, missing


# -----------------------------
# Helpers
# -----------------------------
def load_ascii_image(path: str | Path) -> Optional[np.ndarray]:
    try:
        return np.loadtxt(str(path)).astype(float)
    except Exception:
        return None


def pad_to_res(arr: np.ndarray, res: int = RESOLUTION) -> np.ndarray:
    if arr is None:
        return np.zeros((res, res), dtype=float)

    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    r, c = arr.shape
    out = arr
    if c < res:
        out = np.pad(out, ((0, 0), (0, res - c)), mode="constant")
    if r < res:
        out = np.pad(out, ((0, res - r), (0, 0)), mode="constant")

    return out[:res, :res]


def nanmean_nonzero(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    sel = (x != 0) & np.isfinite(x)
    return float(np.nanmean(x[sel])) if np.any(sel) else np.nan


def strip_photons_suffix(stem_with_ext: str) -> str:
    """
    Turn 'test_..._photons.asc' into 'test_...'
    If it doesn't end with '_photons.asc', just strip '.asc' if present.
    """
    s = str(stem_with_ext)
    low = s.lower()
    if low.endswith("_photons.asc"):
        return s[: -len("_photons.asc")]
    if low.endswith(".asc"):
        return s[: -len(".asc")]
    return s


def safe_a1_fraction(a1_img: Optional[np.ndarray], res: int) -> np.ndarray:
    """
    Convert percent a1 image to fraction image (0..1).
    If missing, return all-NaN so downstream knows it's invalid.
    """
    if a1_img is None:
        return np.full((res, res), np.nan, dtype=float)
    a1 = pad_to_res(a1_img, res) / 100.0
    return a1


def _path_str(p: Path) -> str:
    try:
        return str(p.expanduser())
    except Exception:
        return str(p)

# -----------------------------
# Sanity / validation helpers
# -----------------------------
def _is_blank(x) -> bool:
    return x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() == ""

def _short_cols(df: pd.DataFrame, n: int = 40) -> str:
    cols = list(map(str, df.columns))
    return ", ".join(cols[:n]) + (f" … (+{len(cols)-n} more)" if len(cols) > n else "")

def validate_spc_input_table(df: pd.DataFrame, colmap: Dict[str, str], *, max_bad_rows: int = 5) -> None:
    """
    Validate that required columns are present and look usable.
    Raises RuntimeError with a user-friendly message.
    """
    if df is None or df.empty:
        raise RuntimeError("SPC input table is empty (0 rows).")

    # Quick check: required columns not all blank
    bad_rows = []
    for i, row in df.iterrows():
        missing_any = []
        for canon, actual in colmap.items():
            if _is_blank(row.get(actual, None)):
                missing_any.append(canon)
        if missing_any:
            bad_rows.append((i, missing_any))
            if len(bad_rows) >= max_bad_rows:
                break

    if bad_rows:
        lines = [f"Row {idx}: blank {miss}" for idx, miss in bad_rows]
        raise RuntimeError(
            "SPC input table has blank required fields in some rows.\n"
            + "\n".join(lines)
        )

def validate_suffix_config(cfg: AscSuffixConfig, name: str = "cfg") -> None:
    """
    Make sure suffix patterns are well-formed.
    """
    for kind in ("a1", "t1", "t2", "photons"):
        pat = getattr(cfg, kind, None)
        if not isinstance(pat, str) or "{stem}" not in pat:
            raise RuntimeError(f"{name}.{kind} must be a string containing '{{stem}}' (got: {pat})")
        if not pat.lower().endswith(".asc"):
            raise RuntimeError(f"{name}.{kind} must end with '.asc' (got: {pat})")

def validate_mask(mask: np.ndarray, mask_path: Path, *, res: int = RESOLUTION) -> Tuple[np.ndarray, List[str]]:
    """
    Returns (mask_int_resized, warnings)
    """
    warns: List[str] = []

    if mask is None:
        raise RuntimeError(f"Mask could not be read: {mask_path}")

    if mask.ndim != 2:
        # common with RGBA PNGs
        warns.append(f"mask had ndim={mask.ndim}; using channel 0")
        mask = mask[..., 0]

    mask = pad_to_res(mask, res).astype(int)

    if mask.shape != (res, res):
        # pad_to_res should enforce this, but keep it explicit
        raise RuntimeError(f"Mask was not resized to {res}×{res} (got {mask.shape})")

    max_id = int(np.nanmax(mask)) if mask.size else 0
    if max_id <= 0:
        raise RuntimeError(
            f"Mask contains no labeled cells (max label={max_id}) for: {mask_path}\n"
            "This usually means you loaded a binary/empty mask, the wrong file, or labels are not encoded as integers."
        )

    # warn if labels are extremely high (often indicates grayscale image mistaken for labels)
    if max_id > 5000:
        warns.append(f"mask max label is very large ({max_id}) — is this really a labeled mask?")

    return mask, warns

def validate_percell_output(df: pd.DataFrame) -> None:
    """
    Confirm extractor produced per-cell endpoints, not just a pass-through table.
    """
    if df is None or df.empty:
        raise RuntimeError("SPC extraction produced an empty per-cell table (0 rows).")

    expected_any = ["NADH Intensity", "NADH t1", "ORR", "mask_id", "Cell Number"]
    if not any(c in df.columns for c in expected_any):
        raise RuntimeError(
            "SPC extraction output does not look like a per-cell endpoints table.\n"
            f"Columns present: {_short_cols(df)}\n"
            "Expected columns like: " + ", ".join(expected_any)
        )

    # Strong check: these should exist
    must_have = ["mask_id", "Image Number", "Cell Number", "NADH Intensity"]
    missing = [c for c in must_have if c not in df.columns]
    if missing:
        raise RuntimeError(
            "SPC extraction output missing required per-cell columns: "
            + ", ".join(missing)
            + "\nColumns present: "
            + _short_cols(df)
        )

# -----------------------------
# Main extractor
# -----------------------------
def extract_spc_from_excel(
    df_input: pd.DataFrame,
    nadh_cfg: AscSuffixConfig,
    fad_cfg: AscSuffixConfig,
    a1_min: float = 0.3,
    a1_max: float = 1.0,
) -> pd.DataFrame:
    """
    Expected input columns (flexible headers, case/space tolerant):
      - nadh_folder
      - nadh_stem   (often includes _photons.asc)
      - fad_folder
      - fad_stem
      - mask_path
      - Timepoint (optional)

    Output columns (matches your desired schema):
      Common Name, nadh_folder, nadh_stem, fad_folder, fad_stem, mask_path, mask_id,
      Image Number, Cell Number, Timepoint,
      NADH Intensity, NADH t1, NADH t2, NADH a1, NADH tm,
      FAD Intensity, FAD t1, FAD t2, FAD a1, FAD tm,
      ORR, FLIRR, spc_warnings, outliers
    """
    df_input = df_input.copy()
    # 1. Validate configs
    validate_suffix_config(nadh_cfg, "nadh_cfg")
    validate_suffix_config(fad_cfg, "fad_cfg")

    required = {
        "nadh_folder": ["nadh_folder", "NADH folder", "nadh folder"],
        "nadh_stem":   ["nadh_stem", "NADH stem", "nadh stem", "nadh_filename", "nadh file", "nadh_file"],
        "fad_folder":  ["fad_folder", "FAD folder", "fad folder"],
        "fad_stem":    ["fad_stem", "FAD stem", "fad stem", "fad_filename", "fad file", "fad_file"],
        "mask_path":   ["mask_path", "Mask Path", "maskpath", "mask file", "mask"],

    }

    colmap, missing = _require_cols(df_input, {
        "nadh_folder": required["nadh_folder"],
        "nadh_stem": required["nadh_stem"],
        "fad_folder": required["fad_folder"],
        "fad_stem": required["fad_stem"],
        "mask_path": required["mask_path"],
    })
    validate_spc_input_table(df_input, colmap) # validate required columns and non-blank rows

    if missing:
        # Raise a *clear* error that Dash can show to user
        raise KeyError(
            "SPC input Excel is missing required columns: "
            + ", ".join(missing)
            + "\nFound columns: "
            + ", ".join(map(str, df_input.columns))
        )
    
    # -----------------------------
    # Metadata columns (copied to every cell)
    # -----------------------------
    core_input_cols = set(colmap.values())
    meta_cols = [c for c in df_input.columns if c not in core_input_cols]



    results: List[Dict] = []
    cell_number = 0  # global running cell index

    for img_idx, row in df_input.iterrows():
        nadh_folder = Path(str(row[colmap["nadh_folder"]])).expanduser()
        fad_folder  = Path(str(row[colmap["fad_folder"]])).expanduser()
        nadh_stem_raw = str(row[colmap["nadh_stem"]]).strip()
        fad_stem_raw  = str(row[colmap["fad_stem"]]).strip()
        mask_path = Path(str(row[colmap["mask_path"]])).expanduser()

        #timepoint = row[tp_col] if tp_col and tp_col in row.index else None

        # -----------------------------
        # Per-image metadata (copied to each cell)
        # -----------------------------
        meta = {str(c): row[c] for c in meta_cols}

        # "Common Name" = base stem without _photons.asc
        common_name = strip_photons_suffix(nadh_stem_raw)

        # base stem for building a1/t1/t2/photons (no extension, no "_photons")
        nadh_base = strip_photons_suffix(nadh_stem_raw)
        fad_base  = strip_photons_suffix(fad_stem_raw)

        warn_img: List[str] = []

        # --- Build filenames from user-defined patterns ---
        nadh_files = {
            "a1": nadh_folder / nadh_cfg.build(nadh_base, "a1"),
            "t1": nadh_folder / nadh_cfg.build(nadh_base, "t1"),
            "t2": nadh_folder / nadh_cfg.build(nadh_base, "t2"),
            "photons": nadh_folder / nadh_cfg.build(nadh_base, "photons"),
        }
        fad_files = {
            "a1": fad_folder / fad_cfg.build(fad_base, "a1"),
            "t1": fad_folder / fad_cfg.build(fad_base, "t1"),
            "t2": fad_folder / fad_cfg.build(fad_base, "t2"),
            "photons": fad_folder / fad_cfg.build(fad_base, "photons"),
        }
        # --- Validate folders exist ---
        if not nadh_folder.exists():
            raise FileNotFoundError(f"NADH_folder does not exist (row {img_idx}): {nadh_folder}")
        if not fad_folder.exists():
          
            raise FileNotFoundError(f"FAD_folder does not exist (row {img_idx}): {fad_folder}")

        if not nadh_stem_raw.lower().endswith(".asc"):
            warn_img.append("nadh_stem not .asc (continuing)")
        if not fad_stem_raw.lower().endswith(".asc"):
            warn_img.append("fad_stem not .asc (continuing)")

        # --- Load NADH (t1/t2/photons required; a1 optional) ---
        NADHt1 = load_ascii_image(nadh_files["t1"])
        NADHt2 = load_ascii_image(nadh_files["t2"])
        NADHI  = load_ascii_image(nadh_files["photons"])
        NADHa1_raw = load_ascii_image(nadh_files["a1"])  # may be None

        missing_nadh = [k for k in ("t1", "t2", "photons") if load_ascii_image(nadh_files[k]) is None]
        if missing_nadh:
            exp = "\n".join([f"  - {k}: {nadh_files[k]}" for k in missing_nadh])
            raise FileNotFoundError(
                f"Missing required NADH asc for input row {img_idx}:\n{exp}\n"
                "Check suffix patterns and that the folder/stem point to the right files."
            )

        # --- Load FAD (optional) ---
        FADt1 = load_ascii_image(fad_files["t1"])
        FADt2 = load_ascii_image(fad_files["t2"])
        FADI  = load_ascii_image(fad_files["photons"])
        FADa1_raw = load_ascii_image(fad_files["a1"])

        fad_available = not (FADt1 is None or FADt2 is None or FADI is None)

        if not fad_available:
            warn_img.append("missing FAD asc files")
            FADt1 = FADt2 = FADI = np.full((RESOLUTION, RESOLUTION), np.nan)
            FADa1_raw = None

        # --- Mask ---
        if not mask_path.exists():
            raise FileNotFoundError(f"Mask not found for input row {img_idx}: {mask_path}")

        mask_raw = imageio.imread(str(mask_path))
        mask, mask_warns = validate_mask(mask_raw, mask_path, res=RESOLUTION)
        warn_img.extend(mask_warns)


        mask = imageio.imread(str(mask_path))
        if mask.ndim != 2:
            mask = mask[..., 0]

        mask = pad_to_res(mask, RESOLUTION).astype(int)

        # --- Pad images ---
        NADHt1 = pad_to_res(NADHt1)
        NADHt2 = pad_to_res(NADHt2)
        NADHI  = pad_to_res(NADHI)

        FADt1 = pad_to_res(FADt1)
        FADt2 = pad_to_res(FADt2)
        FADI  = pad_to_res(FADI)

        # --- a1 as fraction (NaN array if missing) ---
        NADHa1 = safe_a1_fraction(NADHa1_raw, RESOLUTION)
        FADa1  = safe_a1_fraction(FADa1_raw, RESOLUTION)

        if NADHa1_raw is None:
            warn_img.append("missing NADH a1")
        if fad_available and FADa1_raw is None:
            warn_img.append("missing FAD a1")

        num_cells = int(np.nanmax(mask)) if mask.size else 0

        for mask_id in range(1, num_cells + 1):
            cell_mask = (mask == mask_id)

            # Masked intensity + lifetimes
            NADHt1_c = np.where(cell_mask, NADHt1, 0.0)
            NADHt2_c = np.where(cell_mask, NADHt2, 0.0)
            NADHI_c  = np.where(cell_mask, NADHI, 0.0)

            FADt1_c  = np.where(cell_mask, FADt1, 0.0)
            FADt2_c  = np.where(cell_mask, FADt2, 0.0)
            FADI_c   = np.where(cell_mask, FADI, 0.0)

            # Masked a1 (fraction); may be NaN if missing
            NADHa1_c = np.where(cell_mask, NADHa1, np.nan)
            FADa1_c  = np.where(cell_mask, FADa1, np.nan)

            # Clamp a1 into [a1_min, a1_max], else set to NaN
            NADHa1_c[(NADHa1_c < a1_min) | (NADHa1_c > a1_max)] = np.nan
            FADa1_c[(FADa1_c < a1_min) | (FADa1_c > a1_max)] = np.nan

            # tm only valid where a1 is valid
            NADH_tm = (NADHa1_c * NADHt1_c) + ((1.0 - NADHa1_c) * NADHt2_c)
            FAD_tm  = (FADa1_c * FADt1_c) + ((1.0 - FADa1_c) * FADt2_c)

            with np.errstate(divide="ignore", invalid="ignore"):
                ORR = FADI_c / (FADI_c + NADHI_c)
                FLIRR = (1.0 - NADHa1_c) / FADa1_c

            cell_number += 1

            out_row = {
                # --- identity / paths ---
                "Common Name": common_name,
                "nadh_folder": _path_str(nadh_folder),
                "nadh_stem": nadh_stem_raw,
                "fad_folder": _path_str(fad_folder),
                "fad_stem": fad_stem_raw,
                "mask_path": _path_str(mask_path),

                # --- experimental metadata ---
                **meta,
                # --- ids ---
                "mask_id": int(mask_id),
                "Image Number": int(img_idx) + 1,
                "Cell Number": int(cell_number),
                #"Timepoint": timepoint,

                # --- NADH ---
                "NADH Intensity": nanmean_nonzero(NADHI_c),
                "NADH t1": nanmean_nonzero(NADHt1_c),
                "NADH t2": nanmean_nonzero(NADHt2_c),
                "NADH a1": float(np.nanmean(NADHa1_c[cell_mask])) if np.any(cell_mask) else np.nan,
                "NADH tm": float(np.nanmean(NADH_tm[cell_mask])) if np.any(cell_mask) else np.nan,

                # --- FAD ---
                "FAD Intensity": nanmean_nonzero(FADI_c),
                "FAD t1": nanmean_nonzero(FADt1_c),
                "FAD t2": nanmean_nonzero(FADt2_c),
                "FAD a1": float(np.nanmean(FADa1_c[cell_mask])) if np.any(cell_mask) else np.nan,
                "FAD tm": float(np.nanmean(FAD_tm[cell_mask])) if np.any(cell_mask) else np.nan,

                # --- ratios ---
                "ORR": nanmean_nonzero(ORR),
                "FLIRR": nanmean_nonzero(FLIRR),

                # --- warnings/outliers ---
                "spc_warnings": "; ".join(warn_img),
                "outliers": False,
            }

            results.append(out_row)

    # Ensure stable column order like your example
    cols_order = [
        "Common Name",
        "nadh_folder", "nadh_stem",
        "fad_folder", "fad_stem",
        "mask_path",
        "mask_id",
        "Image Number", "Cell Number", 
        "NADH Intensity", "NADH t1", "NADH t2", "NADH a1", "NADH tm",
        "FAD Intensity", "FAD t1", "FAD t2", "FAD a1", "FAD tm",
        "ORR", "FLIRR",
        "spc_warnings",
        "outliers",
    ]
    out = pd.DataFrame(results)
    for c in cols_order:
        if c not in out.columns:
            out[c] = np.nan
    # Keep metadata columns (that weren't in cols_order) at the end
    ordered = cols_order + [c for c in out.columns if c not in cols_order]
    out = out[ordered]

    validate_percell_output(out)

    return out
