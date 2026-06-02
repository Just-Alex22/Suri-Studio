# core/user_snippets.py — Snippets personalizados del usuario
#
# Se guardan en ~/.config/sonia/snippets.json con este formato:
# {
#   "python": {
#     "mysnip": "def my_function():\n    ",
#     "header": "# -*- coding: utf-8 -*-\n# Author: \n"
#   },
#   "javascript": { ... }
# }
#
# El SnippetEditorDialog permite añadir/editar/borrar snippets desde la UI.

from __future__ import annotations
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QPlainTextEdit, QLabel, QComboBox,
    QDialogButtonBox, QSplitter, QMessageBox, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont

from core.theme     import VSCode
from core.settings  import snippets_path
from core.translate import tr

_ALL_LANGS = [
    'python', 'javascript', 'typescript', 'cpp', 'java', 'rust', 'go',
    'bash', 'html', 'css', 'scss', 'sql', 'ruby', 'php', 'kotlin',
    'swift', 'lua', 'markdown',
]


# ─────────────────────────────────────────────────────────────────────────────
#  I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_user_snippets() -> dict[str, dict[str, str]]:
    """Carga el archivo de snippets del usuario. Devuelve {} si no existe."""
    p = snippets_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_user_snippets(data: dict[str, dict[str, str]]) -> None:
    """Guarda el dict de snippets en disco."""
    try:
        snippets_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception:
        pass


def get_snippets_for_lang(lang: str) -> dict[str, str]:
    """Devuelve los snippets de usuario para un lenguaje específico."""
    return load_user_snippets().get(lang, {})


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo de gestión de snippets
# ─────────────────────────────────────────────────────────────────────────────
class SnippetEditorDialog(QDialog):
    """
    Diálogo para gestionar snippets personalizados.
    Selector de lenguaje → lista de snippets → editor de prefijo/cuerpo.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Custom snippets title"))
        self.resize(720, 480)
        self.setStyleSheet(f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG};")

        self._data = load_user_snippets()
        self._current_lang = 'python'

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{VSCode.BG}; border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 8, 12, 8)

        lbl = QLabel(tr("Custom snippets title"))
        lbl.setStyleSheet(f"font-size:14px; font-weight:bold; color:{VSCode.FG};")

        lang_lbl = QLabel(tr("Language"))
        lang_lbl.setStyleSheet(f"color:{VSCode.FG_DIM}; font-size:12px;")

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(_ALL_LANGS)
        self._lang_combo.setCurrentText('python')
        self._lang_combo.setFixedWidth(140)
        self._lang_combo.currentTextChanged.connect(self._on_lang_changed)

        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        hdr_lay.addWidget(lang_lbl)
        hdr_lay.addWidget(self._lang_combo)
        lay.addWidget(hdr)

        # ── Área principal ────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background:{VSCode.BORDER}; width:1px; }}"
        )

        # Panel izquierdo: lista de snippets
        left = QWidget()
        left.setMinimumWidth(200)
        left.setMaximumWidth(280)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        list_hdr = QLabel(f"  {tr('Snippets')}")
        list_hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG_DIM};"
            f"font-size:11px; font-weight:bold; letter-spacing:1px;"
            f"padding:6px 8px; border-bottom:1px solid {VSCode.BORDER};"
        )
        left_lay.addWidget(list_hdr)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background:{VSCode.BG};
                border:none; outline:none; font-size:12px;
            }}
            QListWidget::item {{ padding:6px 10px; }}
            QListWidget::item:selected {{ background:#094771; color:{VSCode.WHITE}; }}
            QListWidget::item:hover {{ background:{VSCode.BG_LIGHTER}; }}
        """)
        self._list.currentRowChanged.connect(self._on_snippet_selected)
        left_lay.addWidget(self._list, 1)

        # Botones lista
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"background:{VSCode.BG_LIGHT}; border-top:1px solid {VSCode.BORDER};")
        btn_bar_lay = QHBoxLayout(btn_bar)
        btn_bar_lay.setContentsMargins(6, 4, 6, 4)
        btn_bar_lay.setSpacing(4)

        self._btn_add = QPushButton(tr("Add snippet"))
        self._btn_add.setFixedHeight(26)
        self._btn_add.clicked.connect(self._add_snippet)

        self._btn_del = QPushButton(tr("Delete snippet"))
        self._btn_del.setFixedHeight(26)
        self._btn_del.setEnabled(False)
        self._btn_del.clicked.connect(self._delete_snippet)

        btn_bar_lay.addWidget(self._btn_add)
        btn_bar_lay.addWidget(self._btn_del)
        left_lay.addWidget(btn_bar)
        splitter.addWidget(left)

        # Panel derecho: editor del snippet
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 8)
        right_lay.setSpacing(8)

        prefix_row = QHBoxLayout()
        prefix_lbl = QLabel(tr("snippet_prefix"))
        prefix_lbl.setStyleSheet(f"color:{VSCode.FG_DIM}; font-size:12px;")
        prefix_lbl.setFixedWidth(160)
        self._prefix_input = QLineEdit()
        self._prefix_input.setPlaceholderText(tr("snippet_prefix_ph"))
        prefix_row.addWidget(prefix_lbl)
        prefix_row.addWidget(self._prefix_input)
        right_lay.addLayout(prefix_row)

        body_lbl = QLabel(tr("snippet_body"))
        body_lbl.setStyleSheet(f"color:{VSCode.FG_DIM}; font-size:12px;")
        right_lay.addWidget(body_lbl)

        self._body_editor = QPlainTextEdit()
        self._body_editor.setPlaceholderText(
            "Escribe el contenido del snippet aquí.\n"
            "Usa \\n para saltos de línea."
        )
        font = QFont("JetBrains Mono", 12)
        font.setFixedPitch(True)
        self._body_editor.setFont(font)
        self._body_editor.setStyleSheet(
            f"background:{VSCode.BG}; color:{VSCode.FG}; border:1px solid {VSCode.BORDER};"
        )
        right_lay.addWidget(self._body_editor, 1)

        hint = QLabel(tr("snippet_tip"))
        hint.setStyleSheet(f"color:{VSCode.FG_INACTIVE}; font-size:11px;")
        right_lay.addWidget(hint)

        self._btn_save_snippet = QPushButton(tr("Save snippet"))
        self._btn_save_snippet.setEnabled(False)
        self._btn_save_snippet.clicked.connect(self._save_current_snippet)
        right_lay.addWidget(self._btn_save_snippet, 0, Qt.AlignmentFlag.AlignRight)

        splitter.addWidget(right)
        splitter.setSizes([220, 480])
        lay.addWidget(splitter, 1)

        # Botones del diálogo
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.setContentsMargins(12, 0, 12, 0)
        lay.addWidget(bb, 0, Qt.AlignmentFlag.AlignRight)

        # Conectar cambios del editor de snippet
        self._prefix_input.textChanged.connect(self._on_editor_changed)
        self._body_editor.textChanged.connect(self._on_editor_changed)

        self._refresh_list()

    # ── Lógica interna ────────────────────────────────────────────────────
    def _on_lang_changed(self, lang: str) -> None:
        self._current_lang = lang
        self._refresh_list()
        self._clear_editor()

    def _refresh_list(self) -> None:
        self._list.clear()
        snippets = self._data.get(self._current_lang, {})
        for prefix in sorted(snippets):
            it = QListWidgetItem(prefix)
            it.setData(Qt.ItemDataRole.UserRole, prefix)
            self._list.addItem(it)
        self._btn_del.setEnabled(False)

    def _on_snippet_selected(self, row: int) -> None:
        if row < 0:
            self._clear_editor()
            return
        it     = self._list.item(row)
        prefix = it.data(Qt.ItemDataRole.UserRole)
        body   = self._data.get(self._current_lang, {}).get(prefix, "")
        self._prefix_input.setText(prefix)
        self._body_editor.setPlainText(body)
        self._btn_del.setEnabled(True)
        self._btn_save_snippet.setEnabled(False)

    def _on_editor_changed(self) -> None:
        self._btn_save_snippet.setEnabled(
            bool(self._prefix_input.text().strip())
        )

    def _clear_editor(self) -> None:
        self._prefix_input.clear()
        self._body_editor.clear()
        self._btn_save_snippet.setEnabled(False)
        self._btn_del.setEnabled(False)

    def _add_snippet(self) -> None:
        self._list.clearSelection()
        self._clear_editor()
        self._prefix_input.setFocus()
        self._btn_save_snippet.setEnabled(False)

    def _save_current_snippet(self) -> None:
        prefix = self._prefix_input.text().strip()
        body   = self._body_editor.toPlainText()
        if not prefix:
            return
        if self._current_lang not in self._data:
            self._data[self._current_lang] = {}
        self._data[self._current_lang][prefix] = body
        save_user_snippets(self._data)
        self._refresh_list()
        # Seleccionar el snippet recién guardado
        for i in range(self._list.count()):
            if self._list.item(i).text() == prefix:
                self._list.setCurrentRow(i)
                break
        self._btn_save_snippet.setEnabled(False)

    def _delete_snippet(self) -> None:
        it = self._list.currentItem()
        if not it:
            return
        prefix = it.data(Qt.ItemDataRole.UserRole)
        r = QMessageBox.question(
            self, tr("Delete snippet"),
            tr("Delete snippet confirm").format(name=prefix),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            self._data.get(self._current_lang, {}).pop(prefix, None)
            save_user_snippets(self._data)
            self._refresh_list()
            self._clear_editor()
