"""Offline tests for background-removal math (chroma key + despill). No cv2/rembg."""
import numpy as np
from PIL import Image

from spriteforge.bg_remove import chroma_key, despill


def _img(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr.astype(np.uint8), mode="RGB")


def test_chroma_key_keys_out_magenta_keeps_subject():
    arr = np.zeros((4, 4, 3), np.uint8)
    arr[:, :2] = (255, 0, 255)   # magenta background
    arr[:, 2:] = (220, 30, 30)   # red subject
    rgba = np.asarray(chroma_key(_img(arr), "#FF00FF"))
    assert rgba[:, :2, 3].max() == 0     # magenta -> transparent
    assert rgba[:, 2:, 3].min() == 255   # red subject -> opaque


def test_despill_removes_magenta_cast_from_edge():
    arr = np.full((2, 2, 3), (255, 100, 255), np.uint8)  # magenta-tinted fringe
    out = np.asarray(despill(_img(arr), "#FF00FF"))
    assert out[..., 0].max() <= 110   # R pulled down toward G
    assert out[..., 2].max() <= 110   # B pulled down toward G
    assert out[..., 1].min() == 100   # G untouched


def test_despill_leaves_true_cyan_alone():
    arr = np.full((2, 2, 3), (40, 200, 220), np.uint8)  # cyan: low R, not magenta
    out = np.asarray(despill(_img(arr), "#FF00FF"))
    assert abs(int(out[0, 0, 0]) - 40) <= 1
    assert abs(int(out[0, 0, 2]) - 220) <= 1
