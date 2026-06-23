"""Phase 5: emit the asset manifest, optionally pack atlases, and hand off.

The manifest indexes the finished sprite set for Unity import. Handoff copies
ONLY the clean sprites and the manifest into the game repo's art folder — it
re-verifies every PNG is metadata-free before letting it cross the boundary, so
nothing else (raws, cache, keys, source) can leak.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from PIL import Image

from . import config, metadata

MANIFEST = config.SPRITES_DIR / "manifest.json"


def emit_manifest() -> Path:
    """Index every built sprite into out/sprites/manifest.json."""
    from .generate import load_manifest
    from .postprocess import variant_sizes
    from .style import load_style

    src = load_manifest()
    classes = src["classes"]
    style = load_style()

    sprites = []
    for entry in src["assets"]:
        name, cls = entry["name"], entry["class"]
        cspec = classes[cls]
        files = {
            str(s): f"{name}_{s}.png"
            for s in variant_sizes(cspec["canvas"], cspec.get("variants", []))
            if (config.SPRITES_DIR / f"{name}_{s}.png").exists()
        }
        if not files:
            continue
        sprites.append(
            {
                "name": name,
                "class": cls,
                "anchor": cspec.get("anchor", "center"),
                "sizes": [int(s) for s in files],
                "files": files,
            }
        )

    doc = {
        "generated_by": "spriteforge",
        "style": style["style"]["name"],
        "classes": {
            k: {"canvas": v["canvas"], "anchor": v.get("anchor", "center"),
                "variants": v.get("variants", [])}
            for k, v in classes.items()
        },
        "sprites": sprites,
    }
    config.SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return MANIFEST


def pack_atlases() -> list[Path]:
    """Optional: grid-pack each class's canvas-size sprites into a clean atlas."""
    from .generate import load_manifest

    src = load_manifest()
    classes = src["classes"]
    by_class: dict[str, list[str]] = {}
    for e in src["assets"]:
        by_class.setdefault(e["class"], []).append(e["name"])

    out: list[Path] = []
    for cls, names in by_class.items():
        canvas = classes[cls]["canvas"]
        imgs = [(n, config.SPRITES_DIR / f"{n}_{canvas}.png") for n in names]
        imgs = [(n, p) for n, p in imgs if p.exists()]
        if not imgs:
            continue
        cols = math.ceil(math.sqrt(len(imgs)))
        rows = math.ceil(len(imgs) / cols)
        sheet = Image.new("RGBA", (cols * canvas, rows * canvas), (0, 0, 0, 0))
        frames = {}
        for i, (n, p) in enumerate(imgs):
            x, y = (i % cols) * canvas, (i // cols) * canvas
            sheet.alpha_composite(Image.open(p).convert("RGBA"), (x, y))
            frames[n] = {"x": x, "y": y, "w": canvas, "h": canvas}
        atlas_png = config.SPRITES_DIR / f"atlas_{cls}.png"
        metadata.write_clean_png(sheet, atlas_png)
        (config.SPRITES_DIR / f"atlas_{cls}.json").write_text(
            json.dumps({"image": atlas_png.name, "frames": frames}, indent=2), encoding="utf-8"
        )
        out.append(atlas_png)
    return out


def handoff(target: str | Path, *, include_atlas: bool = False) -> dict:
    """Copy ONLY clean sprites + manifest into the game repo art folder.

    Every PNG is metadata-verified before it crosses; nothing outside
    out/sprites is ever read, so raws, cache, and the key cannot leak.
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        emit_manifest()

    copied: list[str] = []
    for p in sorted(config.SPRITES_DIR.glob("*.png")):
        if p.name.startswith("atlas_") and not include_atlas:
            continue
        metadata.assert_clean(p)  # refuse to hand off anything carrying metadata
        shutil.copy2(p, target / p.name)
        copied.append(p.name)

    shutil.copy2(MANIFEST, target / MANIFEST.name)
    copied.append(MANIFEST.name)

    if include_atlas:
        for j in sorted(config.SPRITES_DIR.glob("atlas_*.json")):
            shutil.copy2(j, target / j.name)
            copied.append(j.name)

    return {"target": str(target), "copied": copied}
