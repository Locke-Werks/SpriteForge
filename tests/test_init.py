"""Offline tests for the init scaffolder (bundled templates + presets)."""
import pytest

from spriteforge import config, init


def test_list_presets_includes_bundled():
    assert {"flat-vector", "pixel-art", "hand-drawn"} <= set(init.list_presets())


def test_scaffold_generic_writes_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    result = init.scaffold()
    assert sorted(result["written"]) == ["assets.yaml", "style.yaml"]
    assert (tmp_path / "config" / "style.yaml").exists()
    assert (tmp_path / "config" / "assets.yaml").exists()
    # The generic template must keep a `primary` palette role — the prompt
    # builder/test rely on it being present.
    assert "primary" in (tmp_path / "config" / "style.yaml").read_text(encoding="utf-8")


def test_scaffold_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    init.scaffold()
    again = init.scaffold()
    assert again["written"] == []
    assert sorted(again["skipped"]) == ["assets.yaml", "style.yaml"]
    forced = init.scaffold(force=True)
    assert sorted(forced["written"]) == ["assets.yaml", "style.yaml"]


def test_scaffold_preset_applies_manifest_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    init.scaffold(style="pixel-art")
    style_text = (tmp_path / "config" / "style.yaml").read_text(encoding="utf-8")
    assets_text = (tmp_path / "config" / "assets.yaml").read_text(encoding="utf-8")
    assert "Pixel Art" in style_text              # the preset was copied
    assert 'resample: "nearest"' in assets_text   # the pixel-art tweak was applied


def test_scaffold_unknown_preset_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    with pytest.raises(ValueError):
        init.scaffold(style="does-not-exist")
