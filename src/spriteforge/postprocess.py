"""Phase 4: normalize cutouts and write clean, metadata-free sprites.

Per asset: trim to content -> scale and anchor onto the class's fixed canvas ->
optional palette enforcement -> resize to each variant -> clean PNG write +
verify. Every asset of a class comes out mechanically identical in size and
registration. Runs on cached cutouts — no API calls.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from . import config, metadata
from .bg_remove import _hex_to_rgb, remove_background

# Downscale filter by name. Lanczos is best for smooth art; nearest preserves
# the hard edges of pixel art that Lanczos would smear.
_RESAMPLE = {"lanczos": Image.LANCZOS, "nearest": Image.NEAREST}


def resample_filter(name: str | None) -> int:
    """Map a resample name to a PIL filter, defaulting to Lanczos."""
    return _RESAMPLE.get((name or "lanczos").lower(), Image.LANCZOS)


def trim(img: Image.Image) -> Image.Image:
    """Crop to the alpha bounding box (tight content bounds)."""
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img


def normalize(
    img: Image.Image,
    *,
    canvas: int,
    anchor: str,
    margin: float = 0.08,
    resample: int = Image.LANCZOS,
) -> Image.Image:
    """Trim, scale to fit the canvas with margin, and place with consistent anchoring."""
    img = trim(img)
    avail = max(1, round(canvas * (1 - 2 * margin)))
    w, h = img.size
    scale = avail / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    sub = img.resize((nw, nh), resample)

    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    x = (canvas - nw) // 2
    if anchor == "bottom-center":
        y = canvas - nh - round(canvas * margin)   # sit on the base in world space
    else:
        y = (canvas - nh) // 2                      # center
    out.alpha_composite(sub, (x, max(0, y)))
    return out


def enforce_palette(img: Image.Image, palette_rgb: list[tuple[int, int, int]]) -> Image.Image:
    """Snap each pixel's RGB to the nearest locked palette color (opt-in safety net)."""
    rgba = np.asarray(img.convert("RGBA")).copy()
    rgb = rgba[..., :3].astype(np.int32)
    pal = np.array(palette_rgb, dtype=np.int32)
    dist = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(axis=3)
    rgba[..., :3] = pal[dist.argmin(axis=2)]
    return Image.fromarray(rgba, "RGBA")


def variant_sizes(canvas: int, variants: list[int]) -> list[int]:
    """The full set of emitted sizes: the canvas plus its downscale variants."""
    return sorted({canvas, *variants}, reverse=True)


def process_assets(*, only: str | None = None, enforce: bool = False) -> list[dict]:
    """Run the full normalize-and-clean pipeline over the manifest's cached raws."""
    from .generate import load_manifest
    from .style import load_style

    manifest = load_manifest()
    defaults = manifest.get("defaults", {})
    classes = manifest["classes"]
    palette_rgb = [_hex_to_rgb(v) for v in load_style()["palette"].values()]
    enforce = enforce or bool(defaults.get("enforce_palette"))

    entries = manifest["assets"]
    if only:
        entries = [e for e in entries if e["name"] == only]
        if not entries:
            raise ValueError(f"No asset named {only!r} in the manifest.")

    results: list[dict] = []
    for entry in entries:
        name, cls = entry["name"], entry["class"]
        raw = config.RAW_DIR / f"{name}.png"
        if not raw.exists():
            results.append({"name": name, "status": "missing-raw", "files": []})
            continue

        method = entry.get("background_method", defaults.get("background_method", "chroma"))
        key_hex = entry.get("key_color", defaults.get("key_color", config.DEFAULT_KEY_COLOR))
        resample = resample_filter(entry.get("resample", defaults.get("resample")))
        cspec = classes[cls]
        canvas, anchor = cspec["canvas"], cspec.get("anchor", "center")

        cut = remove_background(Image.open(raw), method=method, key_hex=key_hex)
        config.CUT_DIR.mkdir(parents=True, exist_ok=True)
        cut.save(config.CUT_DIR / f"{name}.png")

        norm = normalize(cut, canvas=canvas, anchor=anchor, resample=resample)
        if enforce:
            norm = enforce_palette(norm, palette_rgb)

        files: list[Path] = []
        for size in variant_sizes(canvas, cspec.get("variants", [])):
            out_img = norm if size == canvas else norm.resize((size, size), resample)
            dest = config.SPRITES_DIR / f"{name}_{size}.png"
            metadata.write_clean_png(out_img, dest)
            metadata.assert_clean(dest)  # belt-and-suspenders: verify every write
            files.append(dest)

        results.append({"name": name, "status": "ok", "class": cls, "canvas": canvas, "files": files})
    return results
