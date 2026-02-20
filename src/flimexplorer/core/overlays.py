# core/overlays.py
from __future__ import annotations
import base64, io
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend for server rendering
import matplotlib.pyplot as plt

from skimage import io as skio
from skimage.measure import find_contours

def normalize01(a):
    a = np.asarray(a, float)
    lo, hi = np.nanmin(a), np.nanmax(a)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return a
    return (a - lo) / (hi - lo)

def load_gray(path: str):
    try:
        if path.lower().endswith(".asc"):
            return normalize01(np.loadtxt(path, dtype=float))
        img = skio.imread(path)
        if img.ndim == 2:
            return normalize01(img)
        return normalize01(img[..., 0])
    except Exception:
        return None

def load_color(path: str):
    try:
        return skio.imread(path)
    except Exception:
        return None

def load_mask(path: str):
    try:
        m = skio.imread(path)
        if m.ndim > 2:
            m = m[..., 0]
        if m.dtype.kind == "f":
            m = (m > 0).astype(np.uint8)
        return m
    except Exception:
        return None

def outline(mask, cell_id=None):
    if mask is None:
        return []
    if cell_id is not None:
        m = (mask == int(cell_id)).astype(np.uint8)
        return find_contours(m, 0.5)
    m = (mask > 0).astype(np.uint8)
    return find_contours(m, 0.5)

def fig_to_data_uri(fig) -> str:
    bio = io.BytesIO()
    fig.savefig(bio, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    b64 = base64.b64encode(bio.getvalue()).decode("ascii")
    return "data:image/png;base64," + b64

def render_overlay_png(img, mask, cell_id=None, title=""):
    fig, ax = plt.subplots(1, 1, figsize=(5.3, 5.3))
    if img is None:
        ax.text(0.5, 0.5, "Missing image", ha="center", va="center")
        ax.set_axis_off()
        return fig_to_data_uri(fig)

    if img.ndim == 2:
        ax.imshow(img, cmap="gray", interpolation="nearest")
    else:
        ax.imshow(img, interpolation="nearest")

    for cnt in outline(mask, cell_id):
        ax.plot(cnt[:, 1], cnt[:, 0], "r-", linewidth=1.5)

    ax.set_title(title)
    ax.set_axis_off()
    return fig_to_data_uri(fig)
