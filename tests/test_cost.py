"""Offline tests for cost summarization."""
import json

from spriteforge import config, cost


def test_spend_usd_math(monkeypatch):
    monkeypatch.setattr(config, "PRICE_TEXT_INPUT_PER_M", 5.0)
    monkeypatch.setattr(config, "PRICE_IMAGE_INPUT_PER_M", 8.0)
    monkeypatch.setattr(config, "PRICE_IMAGE_OUTPUT_PER_M", 30.0)
    s = cost.Spend(text_input=1_000_000, image_input=1_000_000, image_output=1_000_000)
    assert round(s.usd, 6) == 43.0
    assert s.total_tokens == 3_000_000


def test_summarize_reads_sidecars(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    rec = {
        "name": "item_coin",
        "usage": {
            "input_tokens_details": {"text_tokens": 100, "image_tokens": 200},
            "output_tokens": 1000,
            "output_tokens_details": {"image_tokens": 1000},
        },
    }
    (tmp_path / "k1.json").write_text(json.dumps(rec), encoding="utf-8")
    s = cost.summarize()
    assert s["records"] == 1
    tot = s["total"]
    assert (tot.text_input, tot.image_input, tot.image_output) == (100, 200, 1000)
    assert "item_coin" in s["per_asset"]
