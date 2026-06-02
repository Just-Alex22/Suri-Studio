# tools/scratchpad.py — Panel de notas persistente
#
# Reemplaza al Wasabi Media Player.
# Propósito: tener un espacio de scratch rápido sin salir del editor.
# Útil para: apuntes temporales, TODOs, snippets de prueba,
#             resultados de comandos que quieres guardar, etc.
#
# El contenido se guarda automáticamente en
#   ~/.local/share/sonia/scratchpad.txt
# No tiene pestañas, no tiene syntax highlighting, es intencional.
# La simplicidad es la feature.

from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLabel, QPushButton, QStyle,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QFont, QFontMetricsF

from core.theme     import VSCode
from core.translate import tr


def _scratch_path() -> Path:
    d = Path.home() / ".local" / "share" / "sonia"
    d.mkdir(parents=True, exist_ok=True)
    return d / "scratchpad.txt"


class ScratchPadWidget(QWidget):
    """
    Panel de notas rápidas persistente.
    Guarda automáticamente cada 2 segundos si hubo cambios.
    """

    AUTOSAVE_MS = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT};"
            f"border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 4, 8, 4)

        lbl = QLabel(tr("SCRATCH PAD"))
        lbl.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px;"
            f"font-weight:bold; letter-spacing:1px;"
        )

        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(
            f"color:{VSCode.FG_INACTIVE}; font-size:10px;"
        )

        btn_clear = QPushButton()
        btn_clear.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        )
        btn_clear.setToolTip(tr("scratch_clear_tip"))
        btn_clear.setFixedSize(22, 22)
        btn_clear.setStyleSheet("border:none; background:transparent;")
        btn_clear.clicked.connect(self._clear)

        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        hdr_lay.addWidget(self._lbl_status)
        hdr_lay.addWidget(btn_clear)
        lay.addWidget(hdr)

        # ── Editor de notas ───────────────────────────────────────────
        self._editor = QPlainTextEdit()
        self._editor.setObjectName("scratchpad_editor")
        self._editor.setPlaceholderText(tr("scratch_placeholder"))
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        # Fuente monoespaciada pero un poco más pequeña que el editor principal
        from core.theme import get_best_mono_font, FONT_FAMILY_EDITOR
        font = get_best_mono_font(12)
        self._editor.setFont(font)
        self._editor.setStyleSheet(
            f"QPlainTextEdit#scratchpad_editor {{ font-family: {FONT_FAMILY_EDITOR};"
            f" font-size: 12px; }}"
        )
        self._editor.setTabStopDistance(
            QFontMetricsF(font).horizontalAdvance(' ') * 4
        )

        lay.addWidget(self._editor)

        # ── Autosave ──────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(self.AUTOSAVE_MS)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._save)

        self._editor.textChanged.connect(self._on_changed)

        # Cargar contenido guardado
        self._load()

    # ── Carga / guardado ──────────────────────────────────────────────
    def _load(self) -> None:
        p = _scratch_path()
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
                self._editor.setPlainText(text)
                # Mover el cursor al final
                cursor = self._editor.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self._editor.setTextCursor(cursor)
            except Exception:
                pass
        self._dirty = False

    def _save(self) -> None:
        if not self._dirty:
            return
        try:
            _scratch_path().write_text(
                self._editor.toPlainText(),
                encoding="utf-8"
            )
            self._dirty = False
            self._lbl_status.setText(tr("scratch_saved"))
            # Limpiar el texto de status después de 2s
            QTimer.singleShot(2000, lambda: self._lbl_status.setText(""))
        except Exception:
            pass

    def _on_changed(self) -> None:
        self._dirty = True
        self._timer.start()

    def _clear(self) -> None:
        self._editor.clear()
        self._save()

    def save_now(self) -> None:
        """Guardar inmediatamente (llamar al cerrar la ventana)."""
        self._timer.stop()
        self._save()