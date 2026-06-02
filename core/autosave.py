# core/autosave.py — Snapshots y recuperación de crashes

import json
import time
import hashlib
from pathlib import Path

from PySide6.QtCore import QTimer, QObject, Signal


def _autosave_dir() -> Path:
    d = Path.home() / ".cache" / "sonia" / "autosave"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _snapshot_path(tab_id: str) -> Path:
    return _autosave_dir() / f"{tab_id}.suri_snapshot"


def _all_snapshots() -> list[Path]:
    return list(_autosave_dir().glob("*.suri_snapshot"))


def snapshots_exist() -> bool:
    return bool(_all_snapshots())


def load_snapshots() -> list[dict]:
    result = []
    for p in _all_snapshots():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["_snapshot_path"] = str(p)
            result.append(data)
        except Exception:
            pass
    return result


def delete_all_snapshots():
    for p in _all_snapshots():
        try:
            p.unlink()
        except Exception:
            pass


class AutosaveManager(QObject):
    # 60 segundos — reducido de 30s para ahorrar CPU/IO
    INTERVAL_MS = 60_000

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._win = main_window

        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._run)
        self._timer.start()

    def _run(self):
        tw = self._win.tab_widget
        for i in range(tw.count()):
            tab = tw.widget(i)
            from editor.editor import SplitEditorContainer
            if not isinstance(tab, SplitEditorContainer):
                continue
            if not (tab.is_modified() or tab.primary._is_new):
                continue
            content = tab.editor.toPlainText()
            if not content.strip():
                continue
            tab_id = (
                hashlib.md5(tab.filepath.encode()).hexdigest()
                if tab.filepath else hex(id(tab))[2:]
            )
            data = {
                "tab_id":    tab_id,
                "filepath":  tab.filepath or "",
                "title":     tw.tabText(i),
                "content":   content,
                "timestamp": time.time(),
            }
            try:
                _snapshot_path(tab_id).write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

    def delete_snapshot_for(self, filepath: str):
        if filepath:
            tab_id = hashlib.md5(filepath.encode()).hexdigest()
            p = _snapshot_path(tab_id)
            if p.exists():
                try: p.unlink()
                except Exception: pass

    def stop(self):
        self._timer.stop()
