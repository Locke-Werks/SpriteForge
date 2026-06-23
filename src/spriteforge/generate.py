"""Phase 2: read the manifest, check the cache, and generate each asset via the
edit endpoint anchored to the master reference.

The master reference carries the overall look; each asset's spec-prompt pins
palette, framing, and the flat key background. The content-addressed cache makes
unchanged re-runs free and regenerates only what changed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from . import cache, config
from .client import ImageClient
from .style import MASTER_PATH, load_style, render_palette

ASSETS_YAML = config.PROJECT_ROOT / "config" / "assets.yaml"


def load_manifest() -> dict:
    with open(ASSETS_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_asset_prompt(subject: str, style_spec: dict, *, size: str, key_color: str) -> str:
    """Wrap an asset subject in the shared palette/composition/background spec.

    The reference image (passed to the edit endpoint) holds the look; this pins
    palette, framing, and background per the plan's three-layer strategy.
    """
    p = style_spec["palette"]
    s = style_spec["style"]
    return (
        f"Subject: {subject.strip()}.\n"
        "Style: flat 2D game sprite, consistent with the provided reference image, "
        f"{s['line_weight']}, {s['shading']}.\n"
        f"Palette, use only these: {render_palette(p)}.\n"
        "Composition: single centered subject, flat front orthographic view, full subject "
        "in frame with about ten percent margin, no ground shadow, no cast shadow on the background.\n"
        f"Background: solid flat {key_color} magenta, completely uniform, no gradient, no "
        "texture, filling the entire canvas.\n"
        f"Output: {size}.\n"
        "Exclude: text, watermark, border, extra objects, gradient background."
    )


@dataclass
class GenOutcome:
    name: str
    status: str  # "cached" or "generated"
    path: Path
    tokens: int | None
    usage: dict | None = None


def _resolve(entry: dict, defaults: dict, key: str, fallback):
    """Per-asset value, falling back to manifest defaults, then a hard default."""
    return entry.get(key, defaults.get(key, fallback))


def generate_all(
    *, only: str | None = None, quality: str | None = None, force: bool = False
) -> list[GenOutcome]:
    """Generate manifest assets, serving cache hits and calling the API only on misses."""
    if not MASTER_PATH.exists():
        raise FileNotFoundError(
            "No master reference at config/style_master.png. Run `sprite style --lock` first."
        )

    manifest = load_manifest()
    style_spec = load_style()
    defaults = manifest.get("defaults", {})
    master_bytes = MASTER_PATH.read_bytes()
    model = style_spec["params"].get("model") or config.MODEL

    entries = manifest["assets"]
    if only:
        entries = [e for e in entries if e["name"] == only]
        if not entries:
            raise ValueError(f"No asset named {only!r} in the manifest.")

    # Constructed lazily so a fully-cached run needs no API key.
    _client: list[ImageClient] = []

    def client() -> ImageClient:
        if not _client:
            _client.append(ImageClient(model=model))
        return _client[0]

    outcomes: list[GenOutcome] = []
    for entry in entries:
        name = entry["name"]
        size = _resolve(entry, defaults, "size", config.DEFAULT_SIZE)
        q = quality or _resolve(entry, defaults, "quality", "low")
        key_color = _resolve(entry, defaults, "key_color", config.DEFAULT_KEY_COLOR)

        prompt = build_asset_prompt(entry["prompt"], style_spec, size=size, key_color=key_color)
        key = cache.request_hash(
            model=model, prompt=prompt, size=size, quality=q, reference_bytes=master_bytes
        )
        raw_path = config.RAW_DIR / f"{name}.png"

        cached = None if force else cache.get(key)
        if cached is not None:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(cached)
            outcomes.append(GenOutcome(name, "cached", raw_path, None))
            continue

        result = client().edit(prompt, [MASTER_PATH], size=size, quality=q)
        cache.put(
            key,
            result.png_bytes,
            meta={"name": name, "model": model, "size": size, "quality": q, "usage": result.usage},
        )
        result.save(raw_path)
        tokens = (result.usage or {}).get("total_tokens")
        outcomes.append(GenOutcome(name, "generated", raw_path, tokens, result.usage))

    return outcomes
