"""Offline tests for the clean PNG writer and chunk verifier."""
import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from spriteforge import metadata


def test_clean_writer_strips_metadata(tmp_path):
    img = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    dirty = tmp_path / "dirty.png"
    info = PngInfo()
    info.add_text("Comment", "made by some-tool")
    info.add_itxt("provenance", "c2pa-style blob")
    img.save(dirty, pnginfo=info)
    # sanity: the dirty file really does carry text chunks
    assert set(metadata.png_chunks(dirty)) & {"tEXt", "iTXt", "zTXt"}

    clean = tmp_path / "clean.png"
    metadata.write_clean_png(Image.open(dirty), clean)
    assert metadata.metadata_chunks(clean) == []
    metadata.assert_clean(clean)  # must not raise


def test_assert_clean_flags_metadata(tmp_path):
    p = tmp_path / "x.png"
    info = PngInfo()
    info.add_text("k", "v")
    Image.new("RGBA", (4, 4), (0, 255, 0, 255)).save(p, pnginfo=info)
    with pytest.raises(AssertionError):
        metadata.assert_clean(p)
