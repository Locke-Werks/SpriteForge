"""Phase 1: build, iterate, and lock the master style reference.

The master is the single image every other asset is generated against. We
iterate at low quality until the look is right, then lock one high-quality
master, stored next to config/style.yaml and committed to the repo.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from . import config
from .client import ImageClient, ImageResult

STYLE_YAML = config.PROJECT_ROOT / "config" / "style.yaml"
MASTER_PATH = config.PROJECT_ROOT / "config" / "style_master.png"
DRAFT_PATH = config.RAW_DIR / "style_draft.png"


def load_style() -> dict:
    with open(STYLE_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_palette(palette: dict) -> str:
    """Render an arbitrary palette dict as 'name #hex' pairs for a spec prompt.

    Game-agnostic: whatever color roles a project defines in style.yaml are
    emitted in order, so the palette schema is never fixed to one game's set.
    Underscored keys read naturally ('metal_shadow' -> 'metal shadow').
    """
    return ", ".join(f"{name.replace('_', ' ')} {value}" for name, value in palette.items())


def build_master_prompt(spec: dict) -> str:
    """Assemble the master spec-prompt from style.yaml, following the plan's template."""
    s, p, m = spec["style"], spec["palette"], spec["master"]
    key_color = spec["params"].get("key_color", config.DEFAULT_KEY_COLOR)
    size = spec["params"]["gen_size"]
    return (
        f"Subject: {m['subject'].strip()}\n"
        f"Style: flat 2D game sprite, {s['summary'].strip()} "
        f"Line: {s['line_weight']}. Shading: {s['shading']}.\n"
        f"Palette, use only these: {render_palette(p)}.\n"
        "Composition: single centered subject, flat front orthographic view, full subject in "
        "frame with about twelve percent margin, no ground shadow, no cast shadow on the background.\n"
        f"Lighting: {s['lighting']}.\n"
        f"Background: solid flat {key_color} magenta, completely uniform, no gradient, "
        "no texture, filling the entire canvas.\n"
        f"Output: {size}.\n"
        "Exclude: text, watermark, border, extra objects, gradient background, photorealism, 3D render."
    )


def generate_master(*, lock: bool = False) -> tuple[ImageResult, Path]:
    """Generate a low-quality draft (default) or lock a high-quality master."""
    spec = load_style()
    prompt = build_master_prompt(spec)
    params = spec["params"]
    quality = params["final_quality"] if lock else params["iterate_quality"]
    client = ImageClient(model=params.get("model"))
    result = client.generate(prompt, size=params["gen_size"], quality=quality)
    dest = MASTER_PATH if lock else DRAFT_PATH
    result.save(dest)
    return result, dest


def candidate_path(i: int) -> Path:
    return config.RAW_DIR / f"style_candidate_{i}.png"


def generate_candidates(n: int, *, quality: str | None = None) -> list[tuple[ImageResult, Path]]:
    """Roll N high-quality master candidates into out/raw/ to choose from.

    gpt-image-2 has no seed, so each roll is a fresh image in the same locked
    style. Pick the best and promote it with accept_candidate().
    """
    spec = load_style()
    prompt = build_master_prompt(spec)
    params = spec["params"]
    q = quality or params["final_quality"]
    client = ImageClient(model=params.get("model"))

    out: list[tuple[ImageResult, Path]] = []
    for i in range(1, n + 1):
        result = client.generate(prompt, size=params["gen_size"], quality=q)
        out.append((result, result.save(candidate_path(i))))
    return out


def accept_candidate(i: int) -> Path:
    """Promote candidate i to the locked master at config/style_master.png."""
    src = candidate_path(i)
    if not src.exists():
        raise FileNotFoundError(
            f"No candidate at {src}. Run `sprite style --candidates N` first."
        )
    MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MASTER_PATH.write_bytes(src.read_bytes())
    return MASTER_PATH
