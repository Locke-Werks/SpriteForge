"""Offline tests for the cache, manifest, and prompt layers. No API calls."""
from spriteforge import cache
from spriteforge.generate import build_asset_prompt, load_manifest
from spriteforge.style import load_style


def test_request_hash_is_stable_and_sensitive():
    base = dict(model="m", prompt="p", size="1024x1024", quality="low")
    h1 = cache.request_hash(**base)
    assert h1 == cache.request_hash(**base)
    assert cache.request_hash(**{**base, "prompt": "other"}) != h1
    assert cache.request_hash(**{**base, "quality": "high"}) != h1
    assert cache.request_hash(**base, reference_bytes=b"abc") != h1


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.config, "CACHE_DIR", tmp_path)
    assert cache.get("missing") is None
    cache.put("k1", b"png-bytes", meta={"name": "x"})
    assert cache.get("k1") == b"png-bytes"
    assert (tmp_path / "k1.json").exists()


def test_manifest_is_well_formed():
    m = load_manifest()
    names = [a["name"] for a in m["assets"]]
    assert len(names) == len(set(names)), "asset names must be unique"
    for a in m["assets"]:
        assert a["class"] in m["classes"], f"{a['name']} -> unknown class {a['class']}"
        assert a.get("prompt"), f"{a['name']} has no prompt"


def test_build_asset_prompt_includes_subject_palette_and_key():
    spec = load_style()
    prompt = build_asset_prompt("a test widget", spec, size="1024x1024", key_color="#FF00FF")
    assert "a test widget" in prompt
    assert spec["palette"]["primary"] in prompt
    assert "#FF00FF" in prompt
    assert "reference image" in prompt
