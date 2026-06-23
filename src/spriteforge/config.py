"""Central configuration: model snapshot, defaults, paths, and key handling.

The API key is read from the environment only. It is never returned in logs,
never written to disk by this tool, and never committed.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Pinned snapshot for reproducibility. The moving alias is "gpt-image-2".
# Override per-run with SPRITEFORGE_IMAGE_MODEL if a newer snapshot is needed.
MODEL = os.environ.get("SPRITEFORGE_IMAGE_MODEL", "gpt-image-2-2026-04-21")

# Safe square default: both edges divisible by 16, well inside gpt-image-2's
# pixel range (655,360 - 8,294,400). Downscaling to game sizes happens in post.
DEFAULT_SIZE = "1024x1024"

# Flat key color generated behind every sprite, keyed out in post (Phase 3).
# Magenta rarely appears in art, so it makes a clean chroma key.
DEFAULT_KEY_COLOR = "#FF00FF"

# Project paths. parents[2] resolves to the repo root for an editable install
# (src/spriteforge/config.py -> src -> repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "out"
RAW_DIR = OUT_DIR / "raw"
CUT_DIR = OUT_DIR / "cut"        # transparent intermediates from background removal (Phase 3)
SPRITES_DIR = OUT_DIR / "sprites"
CACHE_DIR = PROJECT_ROOT / "cache"

# gpt-image-2 token pricing, USD per 1M tokens. CONFIRM on the OpenAI pricing
# page before a large batch; override via SPRITEFORGE_PRICE_* env vars.
PRICE_TEXT_INPUT_PER_M = float(os.environ.get("SPRITEFORGE_PRICE_TEXT_INPUT", "5.0"))
PRICE_IMAGE_INPUT_PER_M = float(os.environ.get("SPRITEFORGE_PRICE_IMAGE_INPUT", "8.0"))
PRICE_IMAGE_OUTPUT_PER_M = float(os.environ.get("SPRITEFORGE_PRICE_IMAGE_OUTPUT", "30.0"))


def load_api_key() -> str:
    """Return OPENAI_API_KEY, loading it from the project .env if present.

    Raises a clear error if the key is missing. The value is never logged.
    """
    # Deterministic regardless of current working directory.
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or export OPENAI_API_KEY in your shell."
        )
    return key
