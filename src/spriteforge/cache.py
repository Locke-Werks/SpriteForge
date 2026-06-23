"""Content-addressed cache for raw generations.

The key is a SHA-256 of everything that determines the pixels we ask for: model,
prompt, reference-image bytes, size, and quality. A request whose key already
exists is served from disk and never hits the API, so re-runs are free and the
output is reproducible. (gpt-image-2 has no seed, so we cache the accepted
output rather than trying to reproduce it from parameters.)
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from . import config


def request_hash(
    *,
    model: str,
    prompt: str,
    size: str,
    quality: str,
    reference_bytes: bytes | None = None,
    extra: dict | None = None,
) -> str:
    """Hash a request into a stable cache key."""
    h = hashlib.sha256()
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "extra": extra or {},
    }
    h.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    if reference_bytes:
        # Fold in the reference image so a changed master invalidates everything
        # generated against it.
        h.update(b"\x00ref\x00")
        h.update(hashlib.sha256(reference_bytes).digest())
    return h.hexdigest()


def cache_path(key: str) -> Path:
    return config.CACHE_DIR / f"{key}.png"


def meta_path(key: str) -> Path:
    return config.CACHE_DIR / f"{key}.json"


def get(key: str) -> bytes | None:
    """Return cached PNG bytes for a key, or None on a miss."""
    p = cache_path(key)
    return p.read_bytes() if p.exists() else None


def put(key: str, png_bytes: bytes, meta: dict | None = None) -> Path:
    """Store PNG bytes plus a metadata sidecar (prompt, usage) for cost reporting."""
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = cache_path(key)
    p.write_bytes(png_bytes)
    record = {"key": key, "bytes": len(png_bytes), "cached_at": time.time(), **(meta or {})}
    meta_path(key).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return p
