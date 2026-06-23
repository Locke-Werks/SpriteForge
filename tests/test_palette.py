"""Offline tests for the game-agnostic palette renderer."""
from spriteforge.style import render_palette


def test_render_palette_emits_all_pairs():
    out = render_palette({"primary": "#112233", "accent": "#445566"})
    assert "primary #112233" in out
    assert "accent #445566" in out


def test_render_palette_humanizes_underscored_keys():
    out = render_palette({"metal_shadow": "#8C90B0"})
    assert "metal shadow #8C90B0" in out


def test_render_palette_handles_arbitrary_schema():
    # No fixed key set is required — any color roles a game defines are rendered,
    # which is what makes the prompt layer game-agnostic.
    pal = {"goo": "#00FF00", "ooze_dark": "#001100", "rim_light": "#AAFFAA"}
    out = render_palette(pal)
    for name, value in pal.items():
        assert f"{name.replace('_', ' ')} {value}" in out
