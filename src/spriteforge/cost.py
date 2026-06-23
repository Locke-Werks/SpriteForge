"""Phase 6: cost reporting from the cache's usage sidecars.

Each generation records its token usage in cache/{key}.json. This reads those
sidecars and prices them at the configured gpt-image-2 rates. Confirm current
rates on the OpenAI pricing page; override via SPRITEFORGE_PRICE_* env vars.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import config


@dataclass
class Spend:
    text_input: int = 0
    image_input: int = 0
    image_output: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.text_input + self.image_input + self.image_output

    @property
    def usd(self) -> float:
        return (
            self.text_input / 1e6 * config.PRICE_TEXT_INPUT_PER_M
            + self.image_input / 1e6 * config.PRICE_IMAGE_INPUT_PER_M
            + self.image_output / 1e6 * config.PRICE_IMAGE_OUTPUT_PER_M
        )


def _accumulate(spend: Spend, usage: dict | None) -> None:
    if not usage:
        return
    spend.calls += 1
    ind = usage.get("input_tokens_details", {}) or {}
    outd = usage.get("output_tokens_details", {}) or {}
    spend.text_input += ind.get("text_tokens", 0)
    spend.image_input += ind.get("image_tokens", 0)
    spend.image_output += outd.get("image_tokens", usage.get("output_tokens", 0))


def spend_from_usages(usages) -> Spend:
    """Aggregate a Spend from an iterable of usage dicts (e.g. one gen run)."""
    s = Spend()
    for u in usages:
        _accumulate(s, u)
    return s


def load_records() -> list[dict]:
    if not config.CACHE_DIR.exists():
        return []
    records = []
    for j in sorted(config.CACHE_DIR.glob("*.json")):
        try:
            records.append(json.loads(j.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def summarize() -> dict:
    """Cumulative spend across every cached generation, plus a per-asset breakdown."""
    total = Spend()
    per_asset: dict[str, Spend] = {}
    records = load_records()
    for rec in records:
        usage = rec.get("usage")
        name = rec.get("name", "?")
        _accumulate(per_asset.setdefault(name, Spend()), usage)
        _accumulate(total, usage)
    return {"total": total, "per_asset": per_asset, "records": len(records)}
