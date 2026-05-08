import struct
import zlib
from pathlib import Path

import pytest

from image_converter import png_to_svg


def _make_png(path: Path, width: int = 32, height: int = 32) -> Path:
    """Gera um PNG mínimo válido (quadrado preto)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\x00\x00\x00" * width
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")

    path.write_bytes(signature + ihdr + idat + iend)
    return path


def test_png_to_svg_creates_file(tmp_path: Path):
    png = _make_png(tmp_path / "test.png")
    svg = tmp_path / "test.svg"
    result = png_to_svg(png, svg)
    assert result.exists()
    assert result.stat().st_size > 0


def test_png_to_svg_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        png_to_svg(tmp_path / "nao_existe.png", tmp_path / "out.svg")
