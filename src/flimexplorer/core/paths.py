# core/paths.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import re


@dataclass
class PathPatterns:
    """
    Used for overlay images (NOT the SPC ASC extraction).
    For Explorer overlays we build intensity/color paths from:
      - nadh_folder + nadh_stem
      - fad_folder  + fad_stem
    then apply these patterns (patterns may include "{stem}").
   
    """
    # intensity panels (often .asc)
    nadh_photons: str = "{stem}_photons.asc"
    fad_photons:  str = "{stem}_photons.asc"

    # color panels (often .bmp)
    color_nadh:   str = "{stem}_color_Imag.bmp"
    color_fad:    str = "{stem}_color_Imag.bmp"

    # mask (usually full path already; pattern is fallback mode)
    mask:         str = "{stem}_cp_masks.png"


DEFAULT_DROP_TOKENS = [
    "FLIM1", "FLIM2", "FLIM3",
     # optional; only if you see duplicates
]

import re

def clean_stem_for_images(stem_base: str) -> str:
    """
    Cleans the stem by removing common tokens that often appear in the stem but not in the image filenames.
    """
    s = str(stem_base).strip()

    # 1) Remove 'FLIM<number>' tokens regardless of separator
    #    Examples removed:
    #      " ... NADH FLIM1"  -> " ... NADH"
    #      " ..._FLIM2"       -> " ... "
    s = re.sub(r"(?i)(?:[\s_-]+)FLIM\d+\b", "", s)

    # 2) Collapse whitespace/underscores to single underscores
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)

    return s.strip("_")


def _strip_ext(name: str) -> str:
    s = str(name).strip()
    p = Path(s)
 
    return p.stem if p.suffix else s


def _as_path(x) -> Path | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    return Path(s).expanduser() if s else None

def _strip_photons_suffix(stem: str) -> str:
    s = stem.strip()
    if s.lower().endswith("_photons"):
        return s[:-len("_photons")]
    return s


def resolve_paths_for_row(row: pd.Series, pat: PathPatterns) -> dict:

    nadh_folder = _as_path(row.get("nadh_folder", None))
    fad_folder  = _as_path(row.get("fad_folder", None))
    nadh_stem   = row.get("nadh_stem", None)
    fad_stem    = row.get("fad_stem", None)
    mask_path   = _as_path(row.get("mask_path", None))

    out = {
        "nadh": None, "fad": None, "cnadh": None, "cfad": None, "msk": None,
        "_attempted": {},
        "_exists": {},
    }

    def _record(key: str, p: Path | None):
        if p is None:
            out["_attempted"][key] = None
            out["_exists"][key] = False
            return None
        out["_attempted"][key] = str(p)
        ok = p.exists()
        out["_exists"][key] = bool(ok)
        return str(p) if ok else None

    # --- NADH intensity + color ---
    if nadh_folder and nadh_stem:
        stem_base = _strip_ext(str(nadh_stem))

        candidates = [
            stem_base,                       # raw
            _strip_photons_suffix(stem_base), # remove '_photons' if present
            clean_stem_for_images(stem_base),  # cleaned version 
        ]
        # de-duplicate preserving order
        seen = set()
        candidates = [s for s in candidates if not (s in seen or seen.add(s))]
        # intensity: try candidates too (handles cases where FLIM1/2 is absent in image filename)
        out["nadh"] = None
        attempted_paths = []
        for s in candidates:
            p_int = nadh_folder / pat.nadh_photons.format(stem=s)
            attempted_paths.append(str(p_int))
            got = _record("nadh", p_int)
            if got is not None:
                out["nadh"] = got
                break
        out["_attempted"]["nadh_attempts"] = attempted_paths

        # color: try candidates until one exists
        attempted_paths = []
        for s in candidates:
            p_col = nadh_folder / pat.color_nadh.format(stem=s)
            attempted_paths.append(str(p_col))
            got = _record("cnadh", p_col)
            if got is not None:
                out["cnadh"] = got
                break
        out["_attempted"]["cnadh_attempts"] = attempted_paths

    else:
        # still record "none" so UI can show missing columns
        out["_attempted"]["nadh"] = None
        out["_attempted"]["cnadh"] = None
        out["_exists"]["nadh"] = False
        out["_exists"]["cnadh"] = False

    # --- FAD intensity + color ---
    if fad_folder and fad_stem:
        stem_base = _strip_ext(str(fad_stem))

        candidates = [
            stem_base,
            _strip_photons_suffix(stem_base),
            clean_stem_for_images(stem_base),
        ]
        seen = set()
        candidates = [s for s in candidates if not (s in seen or seen.add(s))]

        out["fad"] = None
        attempted_paths = []
        for s in candidates:
            p_int = fad_folder / pat.fad_photons.format(stem=s)
            attempted_paths.append(str(p_int))
            got = _record("fad", p_int)
            if got is not None:
                out["fad"] = got
                break
        out["_attempted"]["fad_attempts"] = attempted_paths


        attempted_paths = []
        for s in candidates:
            p_col = fad_folder / pat.color_fad.format(stem=s)
            attempted_paths.append(str(p_col))
            got = _record("cfad", p_col)
            if got is not None:
                out["cfad"] = got
                break

        out["_attempted"]["cfad_attempts"] = attempted_paths


    else:
        out["_attempted"]["fad"] = None
        out["_attempted"]["cfad"] = None
        out["_exists"]["fad"] = False
        out["_exists"]["cfad"] = False

    # --- mask (prefer explicit absolute path) ---
    if mask_path:
        out["msk"] = _record("msk", mask_path)
    else:
        out["_attempted"]["msk"] = None
        out["_exists"]["msk"] = False

    return out
