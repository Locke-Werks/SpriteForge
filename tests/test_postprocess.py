"""Offline tests for normalization geometry."""
import numpy as np
from PIL import Image

from spriteforge.postprocess import normalize, trim, variant_sizes


def _box(cw: int, ch: int, bw: int, bh: int, ox: int, oy: int) -> Image.Image:
    a = np.zeros((ch, cw, 4), np.uint8)
    a[oy:oy + bh, ox:ox + bw] = (200, 100, 50, 255)
    return Image.fromarray(a, "RGBA")


def test_trim_crops_to_content():
    assert trim(_box(100, 100, 20, 30, 40, 50)).size == (20, 30)


def test_normalize_centers_on_square_canvas():
    out = normalize(_box(100, 100, 20, 20, 5, 5), canvas=256, anchor="center", margin=0.1)
    assert out.size == (256, 256)
    x0, y0, x1, y1 = out.getchannel("A").getbbox()
    assert abs((x0 + x1) / 2 - 128) <= 2
    assert abs((y0 + y1) / 2 - 128) <= 2


def test_normalize_bottom_anchor_sits_low():
    # A wide, short subject leaves vertical slack so the anchor is observable.
    out = normalize(_box(100, 100, 40, 10, 5, 5), canvas=256, anchor="bottom-center", margin=0.1)
    x0, y0, x1, y1 = out.getchannel("A").getbbox()
    assert y0 > 140                     # content sits in the lower half
    assert y1 >= 256 * (1 - 0.1) - 3    # bottom near canvas bottom minus margin


def test_variant_sizes_dedupes_and_sorts():
    assert variant_sizes(256, [128, 64]) == [256, 128, 64]
    assert variant_sizes(512, [512, 256]) == [512, 256]
