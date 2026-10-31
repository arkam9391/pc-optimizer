"""Generuje icon.ico (PNG w środku, 16-256 px) i icon.png z tego samego rysunku, którego używa aplikacja (ui.logo_pixmap)."""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

from ui import logo_pixmap

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(px):
    buf = QBuffer(); buf.open(QIODevice.WriteOnly)
    logo_pixmap(px).save(buf, "PNG")
    return bytes(buf.data())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    out = Path(__file__).parent
    blobs = [png_bytes(s) for s in SIZES]
    head = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = 6 + 16 * len(SIZES)
    entries = b""
    for s, b in zip(SIZES, blobs):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(b), offset)
        offset += len(b)
    (out / "icon.ico").write_bytes(head + entries + b"".join(blobs))
    (out / "icon.png").write_bytes(png_bytes(256))
    print("icon.ico", (out / "icon.ico").stat().st_size, "B")
