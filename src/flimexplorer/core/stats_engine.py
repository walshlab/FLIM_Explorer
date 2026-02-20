# core/stats_engine.py
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy import stats
from statsmodels.stats.multitest import multipletests


# ------------------------- Config -------------------------

@dataclass(frozen=True)
class StatsConfig:
    mode: str = "auto"              # "auto" | "welch" | "mwu" | "perm"
    alpha: float = 0.05
    mcomp: str = "holm"             # "holm" | "bonferroni" | "fdr_bh" | "sidak"
    perm_n: int = 5000
    perm_seed: int = 0
    exclude_flagged_outliers: bool = True

    # display/selection behavior handled in Dash, but kept here for summary
    show_only_significant_table: bool = False
    annotate_only_significant: bool = True

    # optional CI
    add_effect_ci: bool = False
    ci_level: float = 0.95
    ci_boot_n: int = 1000
    ci_seed: int = 123


# ------------------------- Helpers -------------------------

def stars(p: float) -> str:
    if p is None or (isinstance(p, float) and not np.isfinite(p)):
        return "—"
    return "****" if p < 1e-4 else ("***" if p < 1e-3 else ("**" if p < 1e-2 else ("*" if p < 0.05 else "ns")))

def _finite(x):
    x = np.asarray(x, float)
    return x[np.isfinite(x)]

def shapiro_ok(x) -> bool:
    x = _finite(x)
    if len(x) < 3:
        return False
    try:
        _, p = stats.shapiro(x)
        return bool(p >= 0.05)
    except Exception:
        return False

def levene_equal(a, b) -> bool:
    a = _finite(a); b = _finite(b)
    if len(a) < 2 or len(b) < 2:
        return False
    try:
        _, p = stats.levene(a, b, center="median")
        return bool(p >= 0.05)
    except Exception:
        return False

def cohens_d(a, b) -> float:
    a = _finite(a); b = _finite(b)
    if len(a) < 2 or len(b) < 2:
        return np.nan
    ma, mb = np.mean(a), np.mean(b)
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    sp = math.sqrt(((len(a)-1)*va + (len(b)-1)*vb) / max(1, (len(a)+len(b)-2)))
    return (ma - mb) / sp if sp > 0 else np.nan

def hedges_g(a, b) -> float:
    # small-sample correction of Cohen's d
    d = cohens_d(a, b)
    a = _finite(a); b = _finite(b)
    n1, n2 = len(a), len(b)
    if not np.isfinite(d) or (n1+n2) < 3:
        return d
    J = 1 - (3 / (4*(n1+n2) - 9))
    return float(J * d)

def rank_biserial_u(u_stat: float, n1: int, n2: int) -> float:
    return 1 - (2*u_stat)/(n1*n2) if n1 > 0 and n2 > 0 else np.nan

def perm_two_sample(a, b, n_perm: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    a = _finite(a); b = _finite(b)
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return np.nan, np.nan

    obs = abs(np.mean(a) - np.mean(b))
    pooled = np.concatenate([a, b])
    count = 0
    for _ in range(int(n_perm)):
        rng.shuffle(pooled)
        a_s = pooled[:na]
        b_s = pooled[na:]
        stat = abs(np.mean(a_s) - np.mean(b_s))
        if stat >= obs - 1e-12:
            count += 1
    p = (count + 1) / (n_perm + 1)
    return float(obs), float(p)

def apply_mcomp(pvals: np.ndarray, method: str, alpha: float) -> np.ndarray:
    if len(pvals) == 0:
        return np.array([])
    res = multipletests(pvals, alpha=alpha, method=method)
    return res[1]

def bootstrap_ci(effect_fn, a, b, boot_n: int, level: float, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    a = _finite(a); b = _finite(b)
    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan)
    vals = []
    for _ in range(int(boot_n)):
        a_s = rng.choice(a, size=len(a), replace=True)
        b_s = rng.choice(b, size=len(b), replace=True)
        vals.append(effect_fn(a_s, b_s))
    vals = np.asarray(vals, float)
    if not np.isfinite(vals).any():
        return (np.nan, np.nan)
    lo_q = (1 - level) / 2
    hi_q = 1 - lo_q
    return (float(np.nanquantile(vals, lo_q)), float(np.nanquantile(vals, hi_q)))


# ------------------------- Pair building -------------------------

def build_labels_and_pairs(df: pd.DataFrame, group_col: str, hue_col: str | None, scope: str) -> tuple[list[str], list[tuple[str,str]]]:
    """
    scope:
      - 'none'
      - 'all'                : all pairwise across labels
      - 'within_x'           : within each primary group across hue
      - 'within_hue'         : within each hue across primary group
      - 'across_x_same_hue'  : same as within_hue
      - 'same_x_across_hue'  : same as within_x
      - 'all_combos'         : all A×B combos then all-pairs
    """
    use_hue = bool(hue_col and hue_col in df.columns and hue_col != group_col)
    A = sorted(df[group_col].dropna().astype(str).unique())

    if not use_hue:
        labels = A
        pairs = list(__import__("itertools").combinations(labels, 2)) if scope != "none" else []
        return labels, pairs
    
    B = sorted(df[hue_col].dropna().astype(str).unique())
    def lab(a,b): return f"{a} | {b}"
    labels_all = [lab(a,b) for a in A for b in B]

    if scope == "none":
        return [], []
    if scope in ("all", "all_combos"):
        labels = labels_all
        pairs = list(__import__("itertools").combinations(labels, 2))
        return labels, pairs

    pairs = []
    if scope in ("within_x", "same_x_across_hue"):
        labels = labels_all
        for a in A:
            labs = [lab(a,b) for b in B]
            pairs += list(__import__("itertools").combinations(labs, 2))
        return labels, pairs

    if scope in ("within_hue", "across_x_same_hue"):
        labels = labels_all
        for b in B:
            labs = [lab(a,b) for a in A]
            pairs += list(__import__("itertools").combinations(labs, 2))
        return labels, pairs

    # safe default
    labels = labels_all
    pairs = list(__import__("itertools").combinations(labels, 2))
    return labels, pairs


def make_combo_series(df: pd.DataFrame, group_col: str, hue_col: str | None) -> pd.Series:
    if hue_col and hue_col in df.columns and hue_col != group_col:
        return df[group_col].astype(str) + " | " + df[hue_col].astype(str)
    return df[group_col].astype(str)


# ------------------------- Main compute -------------------------

def compute_pairwise_stats(
    df: pd.DataFrame,
    metric_col: str,
    group_col: str,
    hue_col: str | None,
    scope: str,
    cfg: StatsConfig,
) -> tuple[pd.DataFrame, str]:
    """
    Returns:
      stats_df: columns include group1, group2, n1,n2, test, p, p_adj, effect, effect_label, ci_low, ci_high, warnings
      summary: methods-like text block
    """
    d = df.copy()

    # outlier exclusion for stats
    if cfg.exclude_flagged_outliers and "outliers" in d.columns:
        d = d[d["outliers"] == False]

    # build combo labels
    d = d.copy()
    d["_combo"] = make_combo_series(d, group_col, hue_col)
    y = pd.to_numeric(d[metric_col], errors="coerce")
    d["_y"] = y

    labels, pairs = build_labels_and_pairs(d, group_col, hue_col, scope)
    if not labels or not pairs:
        summary = _methods_summary(metric_col, group_col, hue_col, scope, cfg, d)
        return pd.DataFrame(columns=[
            "group1","group2","n1","n2","test","p","p_adj","effect","effect_label","ci_low","ci_high","warnings"
        ]), summary

    # group arrays
    by = {}
    for lab in labels:
        arr = d.loc[d["_combo"] == lab, "_y"].astype(float).replace([np.inf, -np.inf], np.nan).dropna().values
        by[lab] = arr

    rows = []
    for (g1, g2) in pairs:
        a = by.get(g1, np.array([]))
        b = by.get(g2, np.array([]))
        n1, n2 = len(a), len(b)

        warn = []
        if n1 < 3 or n2 < 3:
            warn.append("normality-check-skipped(n<3)")
        if n1 == 0 or n2 == 0:
            rows.append(dict(
                group1=g1, group2=g2, n1=n1, n2=n2, test="NA",
                p=np.nan, effect=np.nan, effect_label="—",
                ci_low=np.nan, ci_high=np.nan,
                warnings=";".join(warn + ["empty-group"])
            ))
            continue

        chosen = cfg.mode
        normalish = False
        equal_var = False

        if cfg.mode == "auto":
            min_n = min(n1, n2)
            if min_n < 5:
                chosen = "perm"
                warn.append("auto->perm(min(n)<5)")
            else:
                normalish = shapiro_ok(a) and shapiro_ok(b)
                equal_var = levene_equal(a, b)
                if normalish and equal_var and (n1 >= 10 and n2 >= 10):
                    chosen = "welch"
                    warn.append("auto->welch")
                else:
                    chosen = "mwu"
                    warn.append("auto->mwu")
        else:
            # still compute checks for transparency
            normalish = shapiro_ok(a) and shapiro_ok(b)
            equal_var = levene_equal(a, b)

        if not normalish:
            warn.append("non-normal-ish" if (n1 >= 3 and n2 >= 3) else "normality-unknown")
        if not equal_var:
            warn.append("unequal-variance-ish" if (n1 >= 2 and n2 >= 2) else "variance-unknown")

        # run test + effect
        if chosen == "welch":
            _, p = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
            eff = hedges_g(a, b)
            eff_label = "Hedges g"
            testname = "Welch t-test"
            effect_fn = hedges_g

        elif chosen == "mwu":
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            eff = rank_biserial_u(float(u), n1, n2)
            eff_label = "Rank-biserial r"
            testname = "Mann–Whitney U"
            def effect_fn(x,y):
                u2, _ = stats.mannwhitneyu(x, y, alternative="two-sided")
                return rank_biserial_u(float(u2), len(x), len(y))

        elif chosen == "perm":
            _, p = perm_two_sample(a, b, n_perm=cfg.perm_n, seed=cfg.perm_seed)
            eff = float(np.mean(a) - np.mean(b))
            eff_label = "Mean diff"
            testname = f"Permutation (N={cfg.perm_n}, seed={cfg.perm_seed})"
            effect_fn = lambda x,y: float(np.mean(_finite(x)) - np.mean(_finite(y)))

        else:
            _, p = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
            eff = hedges_g(a, b)
            eff_label = "Hedges g"
            testname = "Welch t-test"
            effect_fn = hedges_g

        ci_low = ci_high = np.nan
        if cfg.add_effect_ci:
            ci_low, ci_high = bootstrap_ci(effect_fn, a, b, cfg.ci_boot_n, cfg.ci_level, cfg.ci_seed)

        rows.append(dict(
            group1=g1, group2=g2,
            n1=n1, n2=n2,
            test=testname,
            p=float(p) if np.isfinite(p) else np.nan,
            effect=float(eff) if np.isfinite(eff) else np.nan,
            effect_label=eff_label,
            ci_low=ci_low, ci_high=ci_high,
            warnings=";".join(warn) if warn else ""
        ))

    sdf = pd.DataFrame(rows)

    # multiple comparisons
    mask = sdf["p"].notna()
    pvals = sdf.loc[mask, "p"].values
    padj = apply_mcomp(pvals, method=cfg.mcomp, alpha=cfg.alpha)
    sdf.loc[mask, "p_adj"] = padj
    sdf["p_adj"] = sdf["p_adj"].astype(float)

    # add stars
    sdf["stars"] = sdf["p_adj"].apply(stars)

    # sort helpful for reading
    sdf = sdf.sort_values(["p_adj","p"], na_position="last").reset_index(drop=True)

    summary = _methods_summary(metric_col, group_col, hue_col, scope, cfg, d)
    return sdf, summary


def _methods_summary(metric_col, group_col, hue_col, scope, cfg: StatsConfig, d: pd.DataFrame) -> str:
    hue_txt = hue_col if hue_col else "None"
    out_txt = "Excluded flagged outliers" if cfg.exclude_flagged_outliers else "Included flagged outliers"
    ci_txt = f"Bootstrap CI: {int(cfg.ci_level*100)}% (N={cfg.ci_boot_n}, seed={cfg.ci_seed})" if cfg.add_effect_ci else "Effect CI: off"

    # count
    n_total = len(d)
    n_used = int(pd.to_numeric(d["_y"], errors="coerce").notna().sum()) if "_y" in d.columns else n_total

    return (
        f"Metric: {metric_col}\n"
        f"Grouping: X={group_col} | Hue={hue_txt} | Scope={scope}\n"
        f"Outliers for stats: {out_txt}\n"
        f"Auto-rule: Shapiro–Wilk (α=0.05) + Levene (median); Welch if normal-ish & equal-var & n>=10 per group; "
        f"MWU otherwise; Permutation if min(n)<5\n"
        f"Selected test mode: {cfg.mode}\n"
        f"Multiple comparisons: {cfg.mcomp} (α={cfg.alpha})\n"
        f"Permutation: N={cfg.perm_n}, seed={cfg.perm_seed}\n"
        f"{ci_txt}\n"
        f"Data: {n_total} rows loaded; {n_used} finite values used for {metric_col}"
    )
