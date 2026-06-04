
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSettings

APP    = "Suri Studio"
ORG    = "CuerdOS"
MAX_RECENT = 12

def _s() -> QSettings:
    return QSettings(ORG, APP)

def save_window(win) -> None:
    s = _s()
    s.setValue("window/geometry",  win.saveGeometry())
    s.setValue("window/state",     win.saveState())
    s.setValue("window/maximized", win.isMaximized())
    s.setValue("splitter/main",    win.main_splitter.saveState())
    s.setValue("splitter/left",    win._left_splitter.saveState())
    s.setValue("splitter/right",   win.right_panel.splitter.saveState())
    s.setValue("panels/tree",      win._file_tree_visible)
    s.setValue("panels/right",     win._right_panel_visible)
    s.setValue("panels/git",       win._git_panel_visible)

def restore_window(win) -> None:
    s = _s()
    geom = s.value("window/geometry")
    if geom:
        win.restoreGeometry(geom)
    state = s.value("window/state")
    if state:
        win.restoreState(state)
    main_sp = s.value("splitter/main")
    if main_sp:
        win.main_splitter.restoreState(main_sp)
    right_sp = s.value("splitter/right")
    if right_sp:
        win.right_panel.splitter.restoreState(right_sp)
    tree_vis = s.value("panels/tree",  True, type=bool)
    rp_vis   = s.value("panels/right", True, type=bool)
    git_vis  = s.value("panels/git",   False, type=bool)
    if not tree_vis:
        win.toggle_file_tree()
    if not rp_vis:
        win.toggle_right_panel()
    if git_vis:
        win.toggle_git_panel()

def save_font_size(size: int) -> None:
    _s().setValue("editor/font_size", size)

def load_font_size() -> int:
    return int(_s().value("editor/font_size", 13))

def save_folder(path: str) -> None:
    _s().setValue("explorer/folder", path)

def load_folder() -> str:
    return str(_s().value("explorer/folder", str(Path.home())))

def save_session(win) -> None:
    from editor.editor import SplitEditorContainer
    s = _s()
    paths = []
    for i in range(win.tab_widget.count()):
        tab = win.tab_widget.widget(i)
        if (isinstance(tab, SplitEditorContainer)
                and tab.filepath
                and Path(tab.filepath).is_file()
                and len(tab.filepath) > 1):
            paths.append(tab.filepath)
    s.setValue("session/files",   paths)
    s.setValue("session/current", win.tab_widget.currentIndex())

def load_session() -> tuple[list[str], int]:
    s     = _s()
    paths = s.value("session/files", []) or []
    idx   = int(s.value("session/current", 0))
    valid = [
        p for p in paths
        if p and Path(p).exists() and Path(p).is_file() and len(p) > 1
    ]
    return valid, min(idx, max(0, len(valid) - 1))

def clear_session() -> None:
    s = _s()
    s.remove("session/files")
    s.remove("session/current")

def save_cursor_pos(filepath: str, line: int, col: int) -> None:

    if not filepath:
        return
    key = f"cursor/{_hash(filepath)}"
    _s().setValue(key, f"{line},{col}")

def load_cursor_pos(filepath: str) -> tuple[int, int]:

    if not filepath:
        return 0, 0
    key = f"cursor/{_hash(filepath)}"
    val = _s().value(key, "0,0")
    try:
        parts = str(val).split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0

def _hash(path: str) -> str:
    import hashlib
    return hashlib.md5(path.encode()).hexdigest()[:16]

def add_recent(path: str) -> None:
    s = _s()
    recent = s.value("recent/files", []) or []
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    s.setValue("recent/files", recent[:MAX_RECENT])

def get_recent() -> list[str]:
    s      = _s()
    recent = s.value("recent/files", []) or []
    return [p for p in recent if Path(p).exists()]

def remove_recent(path: str) -> None:
    s = _s()
    recent = s.value("recent/files", []) or []
    if path in recent:
        recent.remove(path)
    s.setValue("recent/files", recent)

def clear_recent() -> None:
    _s().remove("recent/files")

def snippets_path() -> Path:

    d = Path.home() / ".config" / "sonia"
    d.mkdir(parents=True, exist_ok=True)
    return d / "snippets.json"
