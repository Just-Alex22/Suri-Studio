# ui/palette.py — Command Palette (Ctrl+P)
#
# Fix principal: el filtrado fuzzy se mueve a un QThread dedicado
# para que nunca bloquee el event loop, incluso con miles de archivos.
#
# Flujo:
#   1. Usuario escribe → timer 80ms → lanza FilterWorker
#   2. FilterWorker hace el scoring en background
#   3. Al terminar emite resultados → se pintan en la lista
#   Si llega otra tecla mientras filtra, cancela el worker anterior.

from __future__ import annotations
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui  import QColor

from core.theme import VSCode
from core.translate import tr


# ─────────────────────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────────────────────
_SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
              '.tox', 'dist', 'build', '.mypy_cache', '.ruff_cache',
              '.pytest_cache', 'target', 'out', '.idea', '.vscode'}
_TEXT_EXTS = {
    '.py','.pyw','.js','.mjs','.ts','.tsx','.jsx','.html','.htm',
    '.css','.scss','.sass','.c','.cpp','.cc','.h','.hpp','.rs','.go',
    '.java','.kt','.swift','.rb','.php','.lua','.sh','.bash','.zsh',
    '.sql','.json','.toml','.yaml','.yml','.md','.markdown','.txt',
    '.xml','.svg','.ini','.cfg','.conf','.env','.gitignore','.dockerfile',
    '.makefile','.cmake','.gradle','.properties',
}

MAX_RESULTS   = 40
_KIND_FILE    = "file"
_KIND_CMD     = "cmd"


# ─────────────────────────────────────────────────────────────────────────────
#  Indexador de archivos (corre una sola vez por carpeta)
# ─────────────────────────────────────────────────────────────────────────────
class FileIndexWorker(QThread):
    done = Signal(list)   # lista de rutas absolutas

    def __init__(self, folder: str):
        super().__init__()
        self._folder   = folder
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self) -> None:
        results = []
        try:
            for root, dirs, files in os.walk(self._folder):
                if self._cancelled:
                    return
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                for f in files:
                    if self._cancelled:
                        return
                    if Path(f).suffix.lower() in _TEXT_EXTS:
                        results.append(os.path.join(root, f))
        except Exception:
            pass
        if not self._cancelled:
            self.done.emit(results)


# ─────────────────────────────────────────────────────────────────────────────
#  Worker de filtrado fuzzy (corre en cada keystroke)
# ─────────────────────────────────────────────────────────────────────────────
def _score(query: str, text: str) -> int:
    """Scoring fuzzy simple. Devuelve 0 si no hay coincidencia."""
    q = query.lower()
    t = text.lower()
    if not q:
        return 1
    # Substring exacto: mayor score cuanto más al principio
    if q in t:
        return 200 - t.index(q)
    # Coincidencia por letras en orden
    idx = 0
    bonus = 0
    prev  = -1
    for ch in q:
        pos = t.find(ch, idx)
        if pos == -1:
            return 0
        if pos == prev + 1:
            bonus += 2   # letras consecutivas
        idx  = pos + 1
        prev = pos
    return 10 + bonus


class FilterWorker(QThread):
    done = Signal(list)   # [(score, filepath), ...]

    def __init__(self, query: str, files: list[str],
                 folder: str, max_results: int = MAX_RESULTS):
        super().__init__()
        self._query      = query
        self._files      = files
        self._folder     = folder
        self._max        = max_results
        self._cancelled  = False

    def cancel(self):
        self._cancelled = True

    def run(self) -> None:
        q = self._query
        if not q:
            # Sin query: mostrar los últimos archivos indexados
            result = [(0, f) for f in self._files[-(self._max):][::-1]]
            if not self._cancelled:
                self.done.emit(result)
            return

        scored = []
        for fpath in self._files:
            if self._cancelled:
                return
            name  = Path(fpath).name
            s     = _score(q, name)
            if s == 0:
                # Intentar contra la ruta relativa
                rel = fpath[len(self._folder):].lstrip("/\\") if self._folder else fpath
                s   = _score(q, rel)
            if s > 0:
                scored.append((s, fpath))

        scored.sort(key=lambda x: -x[0])
        if not self._cancelled:
            self.done.emit(scored[:self._max])


# ─────────────────────────────────────────────────────────────────────────────
#  QSS del popup
# ─────────────────────────────────────────────────────────────────────────────
_QSS = f"""
QDialog {{
    background: {VSCode.BG_LIGHT};
    border: 1px solid {VSCode.BLUE_ACCENT};
    border-radius: 0px;
}}
QLineEdit {{
    background: {VSCode.BG};
    color: {VSCode.FG};
    border: none;
    border-bottom: 1px solid {VSCode.BORDER};
    padding: 10px 14px;
    font-size: 14px;
    border-radius: 0;
}}
QListWidget {{
    background: {VSCode.BG_LIGHT};
    color: {VSCode.FG};
    border: none;
    outline: none;
    font-size: 13px;
}}
QListWidget::item {{
    padding: 6px 14px;
    border-bottom: .5px solid {VSCode.BORDER};
}}
QListWidget::item:selected {{
    background: #094771;
    color: #ffffff;
}}
QListWidget::item:hover:!selected {{
    background: {VSCode.BG_LIGHTER};
}}
QLabel#hint {{
    color: {VSCode.FG_INACTIVE};
    font-size: 11px;
    padding: 4px 14px;
    background: {VSCode.BG_LIGHT};
    border-top: .5px solid {VSCode.BORDER};
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  CommandPalette
# ─────────────────────────────────────────────────────────────────────────────
class CommandPalette(QDialog):
    open_file   = Signal(str)
    run_command = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        )
        # NO usar WA_TranslucentBackground: en compositors Wayland sin
        # soporte de alpha channel (LabWC, sway, river…) el fondo queda
        # negro sólido en vez de transparente. Usamos colores opacos y
        # borde visible para el mismo efecto visual.
        self.setStyleSheet(_QSS)
        self.setFixedWidth(640)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._input = QLineEdit()
        self._input.setPlaceholderText(tr("Open file or run command…"))
        lay.addWidget(self._input)

        self._list = QListWidget()
        self._list.setMaximumHeight(400)
        lay.addWidget(self._list)

        hint = QLabel(tr("↑↓ navigate  Enter open  Esc close  > for commands"))
        hint.setObjectName("hint")
        lay.addWidget(hint)

        # Estado interno
        self._all_files:      list[str] = []
        self._commands:       list[tuple[str, str, object]] = []
        self._folder:         str = ""
        self._index_worker:   FileIndexWorker | None = None
        self._filter_worker:  FilterWorker    | None = None

        # Timer para debounce — espera 80ms de silencio antes de filtrar
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(80)
        self._debounce.timeout.connect(self._start_filter)

        self._input.textChanged.connect(lambda _: self._debounce.start())
        self._input.returnPressed.connect(self._accept_selected)
        self._list.itemActivated.connect(self._accept_item)

    # ── API pública ───────────────────────────────────────────────────────
    def register_command(self, cmd_id: str, label: str, callback) -> None:
        self._commands.append((cmd_id, label, callback))

    def set_folder(self, folder: str) -> None:
        if folder == self._folder:
            return
        self._folder    = folder
        self._all_files = []

        # Cancelar indexación anterior si sigue corriendo
        if self._index_worker and self._index_worker.isRunning():
            self._index_worker.cancel()
            self._index_worker.wait(200)

        if folder:
            self._index_worker = FileIndexWorker(folder)
            self._index_worker.done.connect(self._on_indexed)
            self._index_worker.start()

    def open(self) -> None:
        if self.parent():
            pw = self.parent()
            self.move(
                pw.geometry().center().x() - self.width() // 2,
                pw.geometry().top() + 60,
            )
        self._input.clear()
        self._render_results([])   # lista vacía mientras filtra
        self._start_filter()
        self.show()
        self._input.setFocus()

    # ── Indexación ────────────────────────────────────────────────────────
    def _on_indexed(self, files: list[str]) -> None:
        self._all_files = files
        if self.isVisible():
            self._start_filter()

    # ── Filtrado asíncrono ────────────────────────────────────────────────
    def _start_filter(self) -> None:
        query = self._input.text().strip()

        # Modo comando
        if query.startswith(">"):
            self._filter_commands(query[1:].strip())
            return

        # Cancelar worker anterior
        if self._filter_worker and self._filter_worker.isRunning():
            self._filter_worker.cancel()
            self._filter_worker.wait(100)

        self._filter_worker = FilterWorker(
            query, self._all_files, self._folder
        )
        self._filter_worker.done.connect(self._on_filter_done)
        self._filter_worker.start()

    def _on_filter_done(self, scored: list) -> None:
        self._render_results(scored)

    def _filter_commands(self, query: str) -> None:
        self._list.clear()
        q = query.lower()
        found = False
        for cmd_id, label, _ in self._commands:
            if not q or q in label.lower():
                it = QListWidgetItem(f"  >  {label}")
                it.setForeground(QColor(VSCode.CYAN))
                it.setData(Qt.ItemDataRole.UserRole, (_KIND_CMD, cmd_id))
                self._list.addItem(it)
                found = True
        if not found:
            it = QListWidgetItem(f"  {tr('No matching commands')}")
            it.setForeground(QColor(VSCode.FG_DIM))
            self._list.addItem(it)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # ── Renderizado ───────────────────────────────────────────────────────
    def _render_results(self, scored: list) -> None:
        self._list.clear()
        if not scored and not self._input.text().strip():
            # Sin query y sin archivos todavía
            if not self._all_files:
                it = QListWidgetItem(f"  {tr('Indexing files…')}")
                it.setForeground(QColor(VSCode.FG_DIM))
                self._list.addItem(it)
            return

        if not scored and self._input.text().strip():
            it = QListWidgetItem(f"  {tr('No results')}")
            it.setForeground(QColor(VSCode.FG_DIM))
            self._list.addItem(it)
            return

        for _score_val, fpath in scored:
            try:
                rel = fpath[len(self._folder):].lstrip("/\\") \
                      if self._folder and fpath.startswith(self._folder) \
                      else fpath
            except Exception:
                rel = fpath
            name = Path(fpath).name
            # Nombre en blanco, ruta relativa más tenue
            it = QListWidgetItem(f"  {name}   {rel}")
            it.setData(Qt.ItemDataRole.UserRole, (_KIND_FILE, fpath))
            it.setToolTip(fpath)
            self._list.addItem(it)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # ── Aceptar ───────────────────────────────────────────────────────────
    def _accept_selected(self) -> None:
        item = self._list.currentItem()
        if item:
            self._accept_item(item)

    def _accept_item(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, value = data[0], data[1]
        self.hide()
        if kind == _KIND_FILE:
            self.open_file.emit(value)
        elif kind == _KIND_CMD:
            for cmd_id, _, cb in self._commands:
                if cmd_id == value:
                    cb()
                    break

    # ── Teclado ───────────────────────────────────────────────────────────
    def keyPressEvent(self, event) -> None:
        key = event.key()
        n   = self._list.count()
        if key == Qt.Key.Key_Escape:
            self.hide()
        elif key == Qt.Key.Key_Down:
            if n:
                self._list.setCurrentRow(
                    min(self._list.currentRow() + 1, n - 1)
                )
        elif key == Qt.Key.Key_Up:
            if n:
                self._list.setCurrentRow(
                    max(self._list.currentRow() - 1, 0)
                )
        else:
            super().keyPressEvent(event)

    def hideEvent(self, event) -> None:
        # Cancelar workers al cerrar
        if self._filter_worker and self._filter_worker.isRunning():
            self._filter_worker.cancel()
        super().hideEvent(event)
