
from __future__ import annotations
import os
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QStyle, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui  import QColor

from core.theme     import VSCode
from core.translate import tr

class ProblemsPanel(QWidget):

    goto_line      = Signal(str, int)
    refresh_needed = Signal()

    POLL_MS = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 4, 8, 4)

        self._lbl_count = QLabel(tr("PROBLEMS"))
        self._lbl_count.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )

        btn_refresh = QPushButton()
        btn_refresh.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        btn_refresh.setToolTip(tr("Refresh"))
        btn_refresh.setFixedSize(22, 22)
        btn_refresh.setStyleSheet("border:none; background:transparent;")
        btn_refresh.clicked.connect(self.refresh_needed)

        hdr_lay.addWidget(self._lbl_count)
        hdr_lay.addStretch()
        hdr_lay.addWidget(btn_refresh)
        lay.addWidget(hdr)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background:{VSCode.BG};
                border:none;
                outline:none;
                font-size:12px;
            }}
            QListWidget::item {{
                padding:4px 10px;
                border-bottom:.5px solid {VSCode.BORDER};
            }}
            QListWidget::item:selected {{
                background:#094771;
                color:{VSCode.WHITE};
            }}
            QListWidget::item:hover {{
                background:{VSCode.BG_LIGHTER};
            }}
        """)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        lay.addWidget(self._list)

        self._filepath = ""

        self._poll = QTimer(self)
        self._poll.setInterval(self.POLL_MS)
        self._poll.timeout.connect(self.refresh_needed)

    def showEvent(self, event):
        super().showEvent(event)
        self._poll.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._poll.stop()

    def update_problems(self, filepath: str, errors: list) -> None:
        self._filepath = filepath
        self._list.clear()

        n_err  = sum(1 for *_, s in errors if s == 'error')
        n_warn = sum(1 for *_, s in errors if s == 'warning')

        if errors:
            tmpl  = tr("problems_count")
            label = f"{tr('PROBLEMS')} — " + tmpl.format(e=n_err, w=n_warn)
        else:
            label = f"{tr('PROBLEMS')} — {tr('problems_none')}"
        self._lbl_count.setText(label)

        for ln, col, msg, sev in errors:
            it     = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, ln)
            prefix = "✕" if sev == 'error' else "△"
            color  = "#f44747" if sev == 'error' else "#e5c07b"
            it.setText(f"  {prefix}  {tr('Ln')} {ln+1}   {msg}")
            it.setForeground(QColor(color))
            self._list.addItem(it)

    def clear(self) -> None:
        self._list.clear()
        self._lbl_count.setText(tr("PROBLEMS"))
        self._filepath = ""

    def _on_double_click(self, item: QListWidgetItem) -> None:
        ln = item.data(Qt.ItemDataRole.UserRole)
        if self._filepath and ln is not None:
            self.goto_line.emit(self._filepath, ln)

_TEXT_EXTS = {
    '.py','.pyw','.js','.mjs','.ts','.tsx','.jsx','.html','.htm','.css',
    '.scss','.sass','.c','.cpp','.cc','.h','.hpp','.rs','.go','.java',
    '.kt','.swift','.rb','.php','.lua','.sh','.bash','.sql','.json',
    '.toml','.yaml','.yml','.md','.markdown','.txt','.xml','.svg',
    '.ini','.cfg','.conf','.env','.gitignore','.dockerfile',
}
_SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
              '.tox', 'dist', 'build', '.mypy_cache', '.ruff_cache'}

class SearchWorker(QThread):
    result_found = Signal(str, int, str, str)
    finished     = Signal(int)

    def __init__(self, folder: str, query: str,
                 use_regex: bool, case_sensitive: bool):
        super().__init__()
        self._folder = folder
        self._query  = query
        self._regex  = use_regex
        self._case   = case_sensitive
        self._stop   = False
        self._count  = 0

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        flags = 0 if self._case else re.IGNORECASE
        try:
            pattern = (re.compile(self._query, flags)
                       if self._regex
                       else re.compile(re.escape(self._query), flags))
        except re.error:
            self.finished.emit(0)
            return

        for root, dirs, files in os.walk(self._folder):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            if self._stop:
                break
            for fname in files:
                if self._stop:
                    break
                if Path(fname).suffix.lower() not in _TEXT_EXTS:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if self._stop:
                                break
                            if pattern.search(line):
                                self._count += 1
                                self.result_found.emit(
                                    fpath, i, line.rstrip(), self._query
                                )
                except (PermissionError, IsADirectoryError):
                    pass

        self.finished.emit(self._count)

class SearchInFilesPanel(QWidget):
    open_result = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 4, 8, 4)
        lbl = QLabel(tr("SEARCH IN FILES"))
        lbl.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        lay.addWidget(hdr)

        ctrl = QWidget()
        ctrl.setStyleSheet(f"background:{VSCode.BG_LIGHT}; padding:4px;")
        ctrl_lay = QVBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(8, 6, 8, 6)
        ctrl_lay.setSpacing(6)

        search_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText(tr("Search in all files…"))
        self._input.setStyleSheet(
            f"background:#3c3c3c; color:{VSCode.FG};"
            f"border:1px solid {VSCode.BORDER}; border-radius:2px; padding:4px 7px;"
        )
        self._input.returnPressed.connect(self._start_search)

        self._btn_search = QPushButton(tr("Search"))
        self._btn_search.setFixedWidth(70)
        self._btn_search.clicked.connect(self._start_search)

        self._btn_stop = QPushButton(tr("Stop"))
        self._btn_stop.setFixedWidth(70)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_search)

        search_row.addWidget(self._input)
        search_row.addWidget(self._btn_search)
        search_row.addWidget(self._btn_stop)
        ctrl_lay.addLayout(search_row)

        opts_row = QHBoxLayout()
        self._chk_case  = QCheckBox(tr("Case sensitive"))
        self._chk_regex = QCheckBox(tr("Regex"))
        for c in [self._chk_case, self._chk_regex]:
            c.setStyleSheet(f"color:{VSCode.FG_DIM}; font-size:11px;")
            opts_row.addWidget(c)
        opts_row.addStretch()
        ctrl_lay.addLayout(opts_row)
        lay.addWidget(ctrl)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background:{VSCode.BG};
                border:none;
                outline:none;
                font-size:12px;
            }}
            QTreeWidget::item {{
                padding:3px 4px;
            }}
            QTreeWidget::item:selected {{
                background:#094771;
                color:{VSCode.WHITE};
            }}
            QTreeWidget::item:hover {{
                background:{VSCode.BG_LIGHTER};
            }}
        """)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        lay.addWidget(self._tree, 1)

        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px; padding:3px 10px;"
        )
        lay.addWidget(self._lbl_status)

        self._worker:     SearchWorker | None = None
        self._folder:     str = str(Path.home())
        self._file_items: dict[str, QTreeWidgetItem] = {}

    def set_folder(self, folder: str) -> None:
        self._folder = folder

    def _start_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            return
        self._stop_search()
        self._tree.clear()
        self._file_items.clear()
        self._lbl_status.setText(tr("Searching…"))
        self._btn_search.setEnabled(False)
        self._btn_stop.setEnabled(True)

        self._worker = SearchWorker(
            self._folder, query,
            self._chk_regex.isChecked(),
            self._chk_case.isChecked(),
        )
        self._worker.result_found.connect(self._on_result)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop_search(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(500)
        self._btn_search.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_result(self, filepath: str, lineno: int,
                   line_text: str, query: str) -> None:
        if filepath not in self._file_items:
            try:
                rel = str(Path(filepath).relative_to(self._folder))
            except ValueError:
                rel = Path(filepath).name
            fi = QTreeWidgetItem([rel])
            fi.setForeground(0, QColor(VSCode.BLUE_LIGHT))
            fi.setData(0, Qt.ItemDataRole.UserRole, ("file", filepath, 0))
            self._tree.addTopLevelItem(fi)
            self._file_items[filepath] = fi

        parent = self._file_items[filepath]
        mi = QTreeWidgetItem([f"  {lineno}:  {line_text.strip()[:120]}"])
        mi.setForeground(0, QColor(VSCode.FG_DIM))
        mi.setData(0, Qt.ItemDataRole.UserRole, ("match", filepath, lineno))
        parent.addChild(mi)
        if self._tree.topLevelItemCount() <= 20:
            parent.setExpanded(True)

    def _on_finished(self, count: int) -> None:
        files = self._tree.topLevelItemCount()
        if count:
            tmpl = tr("results_summary")
            self._lbl_status.setText(tmpl.format(n=count, f=files))
        else:
            self._lbl_status.setText(tr("No results"))
        self._btn_search.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_double_click(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "match":
            self.open_result.emit(data[1], data[2])

class BottomPanel(QWidget):
    goto_line   = Signal(str, int)
    open_result = Signal(str, int)

    refresh_lint = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(260)
        self.setMinimumHeight(100)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        tab_bar = QWidget()
        tab_bar.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-top:1px solid {VSCode.BORDER};"
        )
        tab_lay = QHBoxLayout(tab_bar)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.setSpacing(0)

        def _style(active: bool) -> str:
            return (
                f"color:{'#d4d4d4' if active else '#858585'};"
                f"background:{'#1e1e1e' if active else '#252526'};"
                f"border-right:1px solid #3c3c3c;"
                f"border-bottom:{'2px solid #007acc' if active else 'none'};"
                f"padding:6px 16px; font-size:11px; font-weight:bold; letter-spacing:.5px;"
            )

        self._btn_problems = QPushButton(tr("PROBLEMS"))
        self._btn_search   = QPushButton(tr("SEARCH IN FILES"))
        for b in [self._btn_problems, self._btn_search]:
            b.setFlat(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_problems.setStyleSheet(_style(True))
        self._btn_search.setStyleSheet(_style(False))
        self._btn_problems.clicked.connect(lambda: self._show_tab(0))
        self._btn_search.clicked.connect(lambda: self._show_tab(1))

        btn_close = QPushButton("✕")
        btn_close.setFlat(True)
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:14px; background:transparent;"
        )
        btn_close.clicked.connect(lambda: self.setVisible(False))

        tab_lay.addWidget(self._btn_problems)
        tab_lay.addWidget(self._btn_search)
        tab_lay.addStretch()
        tab_lay.addWidget(btn_close)
        lay.addWidget(tab_bar)

        self.problems_panel = ProblemsPanel()
        self.search_panel   = SearchInFilesPanel()

        self.problems_panel.goto_line.connect(self.goto_line)
        self.problems_panel.refresh_needed.connect(self.refresh_lint)
        self.search_panel.open_result.connect(self.open_result)

        lay.addWidget(self.problems_panel)
        lay.addWidget(self.search_panel)
        self.search_panel.hide()

        self._active_tab = 0
        self._style = _style

    def _show_tab(self, idx: int) -> None:
        self._active_tab = idx
        self.problems_panel.setVisible(idx == 0)
        self.search_panel.setVisible(idx == 1)
        self._btn_problems.setStyleSheet(self._style(idx == 0))
        self._btn_search.setStyleSheet(self._style(idx == 1))

    def show_problems(self) -> None:
        self.setVisible(True)
        self._show_tab(0)

    def show_search(self) -> None:
        self.setVisible(True)
        self._show_tab(1)
        self.search_panel._input.setFocus()
        self.search_panel._input.selectAll()
