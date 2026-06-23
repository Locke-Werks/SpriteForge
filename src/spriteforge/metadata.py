"""Phase 4: clean PNG writer + chunk verifier.

The output sprites cross into an open-source game repo, so they must carry no
EXIF, no PNG text (tEXt/iTXt/zTXt), no ICC profile, and no content-credential or
provenance data. The safest way is to rebuild the image from raw pixels into a
fresh buffer — dropping the info dict entirely — and then verify the written
file's chunks rather than trusting the save call.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

# Standard rendering chunks. Anything else — tEXt/iTXt/zTXt/eXIf/iCCP, C2PA
# custom chunks, etc. — is metadata/provenance and must not appear in output.
_SAFE = {"IHDR", "PLTE", "IDAT", "IEND", "tRNS", "sRGB", "gAMA", "pHYs", "cHRM", "bKGD", "sBIT"}


def write_clean_png(img: Image.Image, path: str | Path) -> Path:
    """Write a PNG rebuilt from pixel data only — no info, icc, exif, or text."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = img.convert("RGBA")
    # Fresh image from raw bytes carries an empty info dict, so the PNG encoder
    # has no text/exif/icc/provenance to write out.
    clean = Image.frombytes("RGBA", img.size, img.tobytes())
    clean.save(path, format="PNG", optimize=True)
    return path


def png_chunks(path: str | Path) -> list[str]:
    """Return the ordered list of PNG chunk types in a file."""
    out: list[str] = []
    with open(path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"{path} is not a PNG")
        while True:
            length_bytes = f.read(4)
            if len(length_bytes) < 4:
                break
            length = int.from_bytes(length_bytes, "big")
            ctype = f.read(4).decode("ascii", "replace")
            f.seek(length + 4, 1)  # skip data + CRC
            out.append(ctype)
            if ctype == "IEND":
                break
    return out


def metadata_chunks(path: str | Path) -> list[str]:
    """Chunks present that are NOT pure rendering data (i.e. metadata/provenance)."""
    return [c for c in png_chunks(path) if c not in _SAFE]


def assert_clean(path: str | Path) -> None:
    """Raise if the written file carries any non-rendering (metadata) chunk."""
    bad = metadata_chunks(path)
    if bad:
        raise AssertionError(f"{path} carries non-rendering chunks: {bad}")
