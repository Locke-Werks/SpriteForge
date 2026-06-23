"""Offline tests for manifest emit and the handoff boundary."""
import json

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from spriteforge import config, metadata, pack


def _clean_png(p):
    metadata.write_clean_png(Image.new("RGBA", (8, 8), (1, 2, 3, 255)), p)


def test_emit_manifest_indexes_existing_sprites(tmp_path, monkeypatch):
    sprites = tmp_path / "sprites"
    sprites.mkdir()
    monkeypatch.setattr(config, "SPRITES_DIR", sprites)
    monkeypatch.setattr(pack, "MANIFEST", sprites / "manifest.json")
    for s in (256, 128, 64):
        _clean_png(sprites / f"item_coin_{s}.png")

    doc = json.loads(pack.emit_manifest().read_text())
    item = [s for s in doc["sprites"] if s["name"] == "item_coin"]
    assert item and sorted(item[0]["sizes"]) == [64, 128, 256]
    assert item[0]["class"] == "item"


def test_handoff_copies_only_sprites_and_manifest(tmp_path, monkeypatch):
    sprites = tmp_path / "sprites"
    sprites.mkdir()
    monkeypatch.setattr(config, "SPRITES_DIR", sprites)
    monkeypatch.setattr(pack, "MANIFEST", sprites / "manifest.json")
    _clean_png(sprites / "item_coin_256.png")
    _clean_png(sprites / "item_coin_128.png")
    (sprites / "manifest.json").write_text("{}", encoding="utf-8")
    (sprites / "notes.txt").write_text("must not cross", encoding="utf-8")

    target = tmp_path / "game" / "Art"
    result = pack.handoff(target)
    crossed = sorted(p.name for p in target.iterdir())
    assert crossed == ["item_coin_128.png", "item_coin_256.png", "manifest.json"]
    assert "notes.txt" not in crossed


def test_handoff_refuses_dirty_png(tmp_path, monkeypatch):
    sprites = tmp_path / "sprites"
    sprites.mkdir()
    monkeypatch.setattr(config, "SPRITES_DIR", sprites)
    monkeypatch.setattr(pack, "MANIFEST", sprites / "manifest.json")
    (sprites / "manifest.json").write_text("{}", encoding="utf-8")
    info = PngInfo()
    info.add_text("leak", "tool fingerprint")
    Image.new("RGBA", (8, 8), (0, 0, 0, 255)).save(sprites / "dirty_256.png", pnginfo=info)

    with pytest.raises(AssertionError):
        pack.handoff(tmp_path / "out")
