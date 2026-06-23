"""Thin OpenAI Image API wrapper: generate, edit, retry/backoff, base64 decode.

Never logs the API key or raw responses. Returns decoded PNG bytes plus token
usage so callers can save the image and account for spend.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from . import config

# Transient failures worth retrying. Auth and invalid-request errors are NOT
# here on purpose: a bad key or bad params should fail fast, not retry.
_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)


@dataclass
class ImageResult:
    """A decoded PNG plus the token usage that produced it."""

    png_bytes: bytes
    usage: dict | None

    def save(self, path: str | Path) -> Path:
        """Write the raw PNG bytes to disk, creating parent dirs as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.png_bytes)
        return path


def _decode(response) -> ImageResult:
    """Extract base64 PNG bytes from an images response. No URL is ever used."""
    b64 = response.data[0].b64_json
    if not b64:
        raise RuntimeError("API response carried no b64_json image data.")
    png = base64.b64decode(b64)

    usage = None
    raw_usage = getattr(response, "usage", None)
    if raw_usage is not None:
        usage = raw_usage.model_dump() if hasattr(raw_usage, "model_dump") else dict(raw_usage)
    return ImageResult(png_bytes=png, usage=usage)


class ImageClient:
    """Wraps the OpenAI image endpoints with retry, backoff, and b64 decoding."""

    def __init__(self, model: str | None = None) -> None:
        # Key is read from the environment only (see config.load_api_key).
        self._client = OpenAI(api_key=config.load_api_key())
        self.model = model or config.MODEL

    @_retry
    def generate(
        self,
        prompt: str,
        *,
        size: str = config.DEFAULT_SIZE,
        quality: str = "low",
        background: str = "opaque",
    ) -> ImageResult:
        """Generate one image from a text prompt.

        Used for the master style reference and any asset that should not be
        anchored to a reference image. `background="opaque"` forces a solid fill
        (gpt-image-2 rejects transparent backgrounds); the flat key color is
        described in the prompt and removed in post.
        """
        response = self._client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=quality,
            background=background,
            n=1,
        )
        return _decode(response)

    @_retry
    def edit(
        self,
        prompt: str,
        images: Sequence[str | Path],
        *,
        size: str = config.DEFAULT_SIZE,
        quality: str = "low",
    ) -> ImageResult:
        """Generate one image anchored to one or more reference images.

        This is the primary path for every asset after the master reference is
        locked (Phase 2). Anchoring to the master holds the style far better than
        prompt text alone.
        """
        handles = [open(Path(p), "rb") for p in images]
        try:
            response = self._client.images.edit(
                model=self.model,
                image=handles if len(handles) > 1 else handles[0],
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
        finally:
            for h in handles:
                h.close()
        return _decode(response)
