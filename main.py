
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore    import QTimer
from PySide6.QtGui     import QFont

from core.theme      import load_theme, build_qss, scaled_font_size
from core.translate  import tr, load_language
from core.autosave   import snapshots_exist, load_snapshots, delete_all_snapshots
from core.highlighter import SyntaxHighlighter
from ui.mainwindow   import SoniaMainWindow
from ui.splash       import make_splash
from editor.editor   import SplitEditorContainer

def _restore_session(window: SoniaMainWindow):
    snapshots = load_snapshots()
    if not snapshots:
        return

    names   = [f"  • {s.get('title', 'Sin título')}" for s in snapshots]
    summary = "\n".join(names[:10])
    if len(names) > 10:
        summary += f"\n  … y {len(names) - 10} más"

    r = QMessageBox.question(
        window,
        tr("Recover session"),
        tr("recover_msg").format(n=len(snapshots), files=summary),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )

    if r == QMessageBox.StandardButton.No:
        delete_all_snapshots()
        return

    if window.tab_widget.count() == 1:
        first = window.tab_widget.widget(0)
        if (isinstance(first, SplitEditorContainer)
                and not first.is_modified()
                and not first.filepath):
            window.tab_widget.removeTab(0)

    for snap in snapshots:
        filepath = snap.get("filepath", "")
        content  = snap.get("content", "")
        title    = snap.get("title", tr("Untitled"))

        if filepath and Path(filepath).exists():
            window.open_file(filepath)
            tab = window._cur_tab()
            if tab:
                tab.editor.setPlainText(content)
                tab.editor.document().setModified(True)
                tab.primary._on_modified()
        else:
            window.new_file()
            tab = window._cur_tab()
            if tab:
                lang = SyntaxHighlighter.detect_language(filepath)
                tab.load_content(content, lang if lang != 'text' else 'text')
                idx = window.tab_widget.currentIndex()
                window.tab_widget.setTabText(idx, f"⟳ {title}")

    QMessageBox.information(
        window,
        tr("Session recovered"),
        tr("session_recovered_msg").format(n=len(snapshots)),
        QMessageBox.StandardButton.Ok,
    )

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Suri Studio")

    load_language()
    load_theme()

    app.setStyleSheet(build_qss())

    splash = make_splash()
    splash.show()
    app.processEvents()

    app_font = QFont()
    app_font.setPointSize(scaled_font_size(10))
    app.setFont(app_font)

    import time
    _t0 = time.monotonic()

    window = SoniaMainWindow()

    def _launch():

        elapsed_ms = int((time.monotonic() - _t0) * 1000)
        remaining  = max(0, 800 - elapsed_ms)
        if remaining > 0:
            QTimer.singleShot(remaining, _do_launch)
        else:
            _do_launch()

    def _do_launch():
        splash.finish(window)
        window.show()
        if snapshots_exist():
            _restore_session(window)

    _launch()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
