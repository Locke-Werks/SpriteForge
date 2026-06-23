"""Offline tests for the client layer. These never hit the API or need a key."""
import base64

import pytest

from spriteforge.client import ImageResult, _decode


class _Datum:
    def __init__(self, b64: str) -> None:
        self.b64_json = b64


class _Resp:
    def __init__(self, b64: str, usage=None) -> None:
        self.data = [_Datum(b64)]
        self.usage = usage


def test_decode_returns_png_bytes():
    raw = b"\x89PNG\r\n\x1a\n fake png bytes"
    result = _decode(_Resp(base64.b64encode(raw).decode()))
    assert isinstance(result, ImageResult)
    assert result.png_bytes == raw
    assert result.usage is None


def test_decode_missing_data_raises():
    with pytest.raises(RuntimeError):
        _decode(_Resp(b64=""))


def test_save_writes_file(tmp_path):
    out = ImageResult(png_bytes=b"hello", usage=None).save(tmp_path / "sub" / "x.png")
    assert out.read_bytes() == b"hello"
