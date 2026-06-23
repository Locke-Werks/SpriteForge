"""Phase 3: background removal.

Every asset is generated on a flat magenta key. The primary path chroma-keys
that color to alpha and despills the edge halo; rembg is the per-asset fallback
for shapes where chroma-key struggles. Both feed a final edge-cleanup pass.

Runs entirely on cached raws — no API calls. cv2 and rembg are imported lazily
so the math path (numpy + PIL) works without the heavy [bg] stack loaded.
Orchestration over the manifest lives in postprocess.process_assets.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import config


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def chroma_key(
    img: Image.Image, key_hex: str, *, inner: float = 60.0, outer: float = 130.0
) -> Image.Image:
    """Key a flat background color to alpha by color distance, with a feathered edge.

    Pixels within `inner` of the key are fully transparent, beyond `outer` fully
    opaque, linearly feathered between (which mattes anti-aliased edges). Returns
    an RGBA image whose colors are not yet despilled.
    """
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    key = np.array(_hex_to_rgb(key_hex), dtype=np.float32)
    dist = np.sqrt(((rgb - key) ** 2).sum(axis=2))
    alpha = np.clip((dist - inner) / (outer - inner), 0.0, 1.0) * 255.0
    out = np.dstack([rgb, alpha]).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def despill(img: Image.Image, key_hex: str) -> Image.Image:
    """Neutralize the key color bleeding onto edge pixels.

    Generalized: the key's near-255 channels are its "high" channels and its
    near-0 channels are "low". The spill is how far the high channels jointly
    exceed the low channels; subtract it from the high channels. For magenta
    (R,B high, G low) this removes pink fringes while leaving true reds, blues,
    and cyans untouched.
    """
    rgba = np.asarray(img.convert("RGBA"), dtype=np.float32)
    key = _hex_to_rgb(key_hex)
    highs = [i for i, v in enumerate(key) if v >= 128]
    lows = [i for i, v in enumerate(key) if v < 128]
    if not highs or not lows:
        return img  # not a cleanly keyable color; skip despill

    high_min = np.minimum.reduce([rgba[..., i] for i in highs])
    low_max = np.maximum.reduce([rgba[..., i] for i in lows])
    spill = np.clip(high_min - low_max, 0.0, None)
    for i in highs:
        rgba[..., i] = rgba[..., i] - spill
    return Image.fromarray(rgba.clip(0, 255).astype(np.uint8), mode="RGBA")


def rembg_cutout(img: Image.Image) -> Image.Image:
    """Model-based cutout fallback. Lazy import; downloads a model on first use."""
    from rembg import remove  # heavy, optional dependency

    return remove(img.convert("RGBA"))


def edge_cleanup(
    img: Image.Image,
    *,
    erode: int = 1,
    feather: float = 0.8,
    low_thresh: int = 25,
    high_thresh: int = 248,
) -> Image.Image:
    """Soften fringes and remove semi-transparent border garbage.

    Erodes the matte a touch to eat the last halo ring, feathers to soften hard
    fringes, then thresholds so near-transparent specks drop to 0 and
    near-opaque pixels solidify to 255.
    """
    import cv2  # lazy: part of the [bg] stack

    rgba = np.asarray(img.convert("RGBA")).copy()
    alpha = rgba[..., 3].astype(np.float32)

    if erode:
        alpha = cv2.erode(alpha, np.ones((3, 3), np.uint8), iterations=erode)
    if feather:
        k = max(1, int(round(feather)) * 2 + 1)
        alpha = cv2.GaussianBlur(alpha, (k, k), feather)

    alpha = np.where(alpha < low_thresh, 0, alpha)
    alpha = np.where(alpha > high_thresh, 255, alpha)
    rgba[..., 3] = alpha.clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def remove_background(
    img: Image.Image, *, method: str = "chroma", key_hex: str = config.DEFAULT_KEY_COLOR
) -> Image.Image:
    """Dispatch to chroma-key (default) or rembg, then run the edge-cleanup pass."""
    if method == "rembg":
        cut = rembg_cutout(img)
    else:
        cut = despill(chroma_key(img, key_hex), key_hex)
    return edge_cleanup(cut)
