"""`sprite init` — scaffold a project's config from bundled templates or a preset.

Game-agnostic: SpriteForge ships generic templates and a small library of style
presets *inside the package*. `init` copies them into ./config so a fresh project
(or a re-style of an existing one) starts from a sane, documented baseline that
Claude Code then edits. Reading via importlib.resources means it works the same
from an editable install or an installed wheel.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config

# Bundled templates/presets live on disk next to this module. SpriteForge is
# always used as an editable, dropped-in repo, so a filesystem path is the
# simplest, most robust way to read them (no zip-import edge cases).
_PKG_DIR = Path(__file__).resolve().parent

# Per-preset tweaks applied to assets.yaml at init time. This keeps presets as
# pure style.yaml while still letting a look adjust a mechanical default (e.g.
# pixel art wants nearest-neighbour downscales, not Lanczos).
PRESET_MANIFEST_DEFAULTS: dict[str, dict[str, str]] = {
    "pixel-art": {"resample": "nearest"},
}


def list_presets() -> list[str]:
    """Names of bundled style presets (without the .yaml suffix), sorted."""
    return sorted(p.stem for p in (_PKG_DIR / "presets").glob("*.yaml"))


def _read(relpath: str) -> str:
    """Read a bundled template/preset file as text."""
    return (_PKG_DIR / relpath).read_text(encoding="utf-8")


def _apply_manifest_defaults(assets_text: str, tweaks: dict[str, str]) -> str:
    """Swap default values in the assets.yaml text, preserving its comments."""
    for key, value in tweaks.items():
        assets_text = re.sub(
            rf'(?m)^(\s*{re.escape(key)}:\s*)"[^"]*"',
            rf'\g<1>"{value}"',
            assets_text,
        )
    return assets_text


def scaffold(*, style: str | None = None, force: bool = False) -> dict:
    """Write config/style.yaml + config/assets.yaml from templates (or a preset).

    Refuses to overwrite an existing file unless `force` is set, so an established
    project is never clobbered by accident. Returns a summary of what changed.
    """
    cfg_dir = config.PROJECT_ROOT / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    if style is not None:
        presets = list_presets()
        if style not in presets:
            raise ValueError(
                f"Unknown style preset {style!r}. Available: {', '.join(presets) or '(none)'}."
            )
        style_text = _read(f"presets/{style}.yaml")
    else:
        style_text = _read("templates/style.yaml")

    assets_text = _read("templates/assets.yaml")
    if style is not None and style in PRESET_MANIFEST_DEFAULTS:
        assets_text = _apply_manifest_defaults(assets_text, PRESET_MANIFEST_DEFAULTS[style])

    targets = {
        cfg_dir / "style.yaml": style_text,
        cfg_dir / "assets.yaml": assets_text,
    }

    written: list[str] = []
    skipped: list[str] = []
    for path, text in targets.items():
        if path.exists() and not force:
            skipped.append(path.name)
            continue
        path.write_text(text, encoding="utf-8")
        written.append(path.name)

    # Make setup obvious: ensure a .env.example sits next to the config.
    env_example = config.PROJECT_ROOT / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# Copy to .env and set your key. .env is gitignored; never commit it.\n"
            "OPENAI_API_KEY=\n",
            encoding="utf-8",
        )

    return {
        "style": style or "generic-template",
        "config_dir": str(cfg_dir),
        "written": written,
        "skipped": skipped,
    }
