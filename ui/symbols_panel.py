from __future__ import annotations
import ast
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit,
)
from PySide6.QtCore  import Qt, Signal, QTimer
from PySide6.QtGui   import QColor

from core.theme     import VSCode
from core.translate import tr


_ICONS = {
    "class":    "C", "function": "f", "method":   "m",
    "variable": "v", "import":   "i", "constant": "K", "section":  "#",
}
_COLORS = {
    "class":    "#c586c0", "function": "#dcdcaa", "method":   "#9cdcfe",
    "variable": "#9cdcfe", "import":   "#858585", "constant": "#4fc1ff",
    "section":  "#569cd6",
}


def parse_python_symbols(code: str) -> list[dict]:
    symbols = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return symbols
    class_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append({"name": node.name, "kind": "class", "line": node.lineno, "parent": None})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({"name": child.name, "kind": "method", "line": child.lineno, "parent": node.name})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not any(isinstance(p, ast.ClassDef) and node in ast.walk(p)
                       for p in ast.walk(tree) if isinstance(p, ast.ClassDef) and p is not node):
                symbols.append({"name": node.name, "kind": "function", "line": node.lineno, "parent": None})
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    kind = "constant" if t.id.isupper() else "variable"
                    symbols.append({"name": t.id, "kind": kind, "line": node.lineno, "parent": None})
    symbols.sort(key=lambda s: s["line"])
    return symbols


_REGEXES: dict[str, list] = {
    "javascript": [
        (r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', "function"),
        (r'^\s*(?:export\s+)?class\s+(\w+)', "class"),
        (r'^\s*(?:const|let|var)\s+(\w+)\s*=', "variable"),
    ],
    "typescript": [
        (r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', "function"),
        (r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', "class"),
        (r'^\s*(?:export\s+)?interface\s+(\w+)', "class"),
        (r'^\s*(?:export\s+)?type\s+(\w+)\s*=', "constant"),
        (r'^\s*(?:const|let)\s+(\w+)\s*[=:]', "variable"),
    ],
    "cpp": [
        (r'^\s*(?:class|struct)\s+(\w+)', "class"),
        (r'^\s*#define\s+(\w+)', "constant"),
        (r'^\s*(?:[\w:*&<>]+\s+)+(\w+)\s*\(', "function"),
    ],
    "c": [
        (r'^\s*struct\s+(\w+)', "class"),
        (r'^\s*#define\s+(\w+)', "constant"),
        (r'^\s*(?:[\w*]+\s+)+(\w+)\s*\(', "function"),
    ],
    "java": [
        (r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+(\w+)', "class"),
        (r'^\s*(?:public|private|protected)[\w\s<>[\]]*\s+(\w+)\s*\(', "method"),
    ],
    "rust": [
        (r'^\s*(?:pub\s+)?fn\s+(\w+)', "function"),
        (r'^\s*(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)', "class"),
        (r'^\s*const\s+(\w+)', "constant"),
    ],
    "go": [
        (r'^\s*func\s+(\w+)', "function"),
        (r'^\s*type\s+(\w+)\s+(?:struct|interface)', "class"),
        (r'^\s*(?:var|const)\s+(\w+)', "variable"),
    ],
    "ruby": [
        (r'^\s*(?:class|module)\s+(\w+)', "class"),
        (r'^\s*def\s+(\w+)', "function"),
    ],
    "php": [
        (r'^\s*(?:abstract\s+)?class\s+(\w+)', "class"),
        (r'^\s*(?:public|private|protected)?\s*function\s+(\w+)', "method"),
    ],
    "markdown": [(r'^#{1,6}\s+(.+)', "section")],
}


def parse_generic_symbols(code: str, lang: str) -> list[dict]:
    symbols = []
    for i, line in enumerate(code.splitlines(), 1):
        for pattern, kind in _REGEXES.get(lang, []):
            m = re.match(pattern, line)
            if m:
                symbols.append({"name": m.group(1).strip(), "kind": kind, "line": i, "parent": None})
                break
    return symbols


class SymbolsPanel(QWidget):
    goto_line = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filepath = ""
        self._lang     = ""
        self._symbols: list[dict] = []
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(600)
        self._debounce.timeout.connect(self._refresh)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QLabel("SÍMBOLOS")
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG_DIM};"
            f"font-size:11px; font-weight:bold; letter-spacing:1px;"
            f"padding:6px 10px; border-bottom:1px solid {VSCode.BORDER};"
        )
        lay.addWidget(hdr)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrar símbolos…")
        self._filter.setStyleSheet(
            f"background:{VSCode.BG}; color:{VSCode.FG};"
            f"border:none; border-bottom:1px solid {VSCode.BORDER};"
            f"padding:5px 8px; font-size:12px;"
        )
        self._filter.textChanged.connect(self._apply_filter)
        lay.addWidget(self._filter)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background:{VSCode.BG}; border:none; outline:none; font-size:12px;
            }}
            QTreeWidget::item {{ padding:2px 4px; }}
            QTreeWidget::item:selected {{ background:{VSCode.SELECTION}; color:{VSCode.WHITE}; }}
            QTreeWidget::item:hover {{ background:{VSCode.BG_LIGHTER}; }}
        """)
        self._tree.itemDoubleClicked.connect(self._on_activate)
        lay.addWidget(self._tree, 1)

    def set_file(self, filepath: str, lang: str) -> None:
        self._filepath = filepath
        self._lang     = lang
        self._debounce.start()

    def update_content(self, code: str, lang: str) -> None:
        self._lang = lang
        self._parse(code)
        self._rebuild()

    def _refresh(self) -> None:
        if not self._filepath:
            return
        try:
            code = Path(self._filepath).read_text(encoding="utf-8", errors="ignore")
            self._parse(code)
            self._rebuild()
        except Exception:
            pass

    def _parse(self, code: str) -> None:
        if self._lang == "python":
            self._symbols = parse_python_symbols(code)
        else:
            self._symbols = parse_generic_symbols(code, self._lang)

    def _rebuild(self, query: str = "") -> None:
        self._tree.clear()
        q = query.lower()
        classes: dict[str, QTreeWidgetItem] = {}
        for sym in self._symbols:
            if q and q not in sym["name"].lower():
                continue
            kind  = sym["kind"]
            color = _COLORS.get(kind, VSCode.FG)
            badge = _ICONS.get(kind, "?")
            label = f"  {badge}  {sym['name']}  :{sym['line']}"
            it = QTreeWidgetItem([label])
            it.setForeground(0, QColor(color))
            it.setData(0, Qt.ItemDataRole.UserRole, sym["line"])
            if sym["parent"] and sym["parent"] in classes:
                classes[sym["parent"]].addChild(it)
            else:
                self._tree.addTopLevelItem(it)
                if kind == "class":
                    classes[sym["name"]] = it
                    it.setExpanded(True)

    def _apply_filter(self, query: str) -> None:
        self._rebuild(query)

    def _on_activate(self, item: QTreeWidgetItem, _col: int) -> None:
        line = item.data(0, Qt.ItemDataRole.UserRole)
        if line is not None:
            self.goto_line.emit(int(line))
