from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import QSplashScreen
from PySide6.QtGui     import QPixmap, QColor, QFont, QPainter
from PySide6.QtCore    import Qt


def _assets() -> Path:
    return Path(__file__).parent.parent / "assets"


def make_splash() -> QSplashScreen:
    banner = _assets() / "startup_banner.jpg"
    if banner.exists():
        pix = QPixmap(str(banner))
        if pix.isNull():
            pix = _fallback()
    else:
        pix = _fallback()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    return splash


def _fallback() -> QPixmap:
    pix = QPixmap(480, 280)
    pix.fill(QColor("#1e1e2e"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    f = QFont()
    f.setPointSize(32)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#cdd6f4"))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "Suri Studio")

    f2 = QFont()
    f2.setPointSize(11)
    p.setFont(f2)
    p.setPen(QColor("#6c7086"))
    r = pix.rect().adjusted(0, 60, 0, 0)
    p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Cargando…")

    p.end()
    return pix
