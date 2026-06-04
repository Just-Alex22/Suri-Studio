
from __future__ import annotations

import os
import sys
import shlex
import shutil
import signal
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStyle, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QRect
from PySide6.QtGui  import (
    QPainter, QColor, QFont, QFontMetrics, QKeyEvent,
    QPalette, QCursor,
)

from core.theme     import VSCode, get_best_mono_font
from core.translate import tr

_HAVE_PTY = False
try:
    import pyte
    import ptyprocess
    _HAVE_PTY = True
except ImportError:
    pass

_IS_WINDOWS = sys.platform == "win32"

_ANSI_COLORS: dict[str, str] = {
    "black":         "#1e1e1e",
    "red":           "#f44747",
    "green":         "#4ec994",
    "brown":         "#ce9178",
    "blue":          "#569cd6",
    "magenta":       "#c678dd",
    "cyan":          "#56b6c2",
    "white":         "#d4d4d4",
    "brightblack":   "#555555",
    "brightred":     "#f99157",
    "brightgreen":   "#98c379",
    "brightyellow":  "#e5c07b",
    "brightblue":    "#61afef",
    "brightmagenta": "#e06c75",
    "brightcyan":    "#88d8b0",
    "brightwhite":   "#ffffff",
}

_DEFAULT_FG = QColor("#d4d4d4")
_DEFAULT_BG = QColor("#1e1e1e")
_CURSOR_CLR = QColor("#aeafad")

def _resolve_color(name: str, is_bg: bool) -> QColor:

    if name == "default":
        return _DEFAULT_BG if is_bg else _DEFAULT_FG
    if name in _ANSI_COLORS:
        return QColor(_ANSI_COLORS[name])
    if len(name) == 6:
        try:
            return QColor(f"#{name}")
        except Exception:
            pass
    return _DEFAULT_BG if is_bg else _DEFAULT_FG

if _HAVE_PTY:
    class TermScreen(pyte.DiffScreen):

        def __init__(self, cols: int, rows: int):
            super().__init__(cols, rows)
            self._alt_active    = False
            self._saved_buffer  = None
            self._saved_cursor  = None

        def set_mode(self, mode, private=False):
            if private and mode in (47, 1049):
                self._enter_alt()
            else:
                super().set_mode(mode, private)

        def reset_mode(self, mode, private=False):
            if private and mode in (47, 1049):
                self._exit_alt()
            else:
                super().reset_mode(mode, private)

        def _enter_alt(self):
            if self._alt_active:
                return
            import copy
            self._saved_buffer = copy.deepcopy(self.buffer)
            self._saved_cursor = (self.cursor.x, self.cursor.y)
            self._alt_active   = True
            self.erase_in_display(2)
            self.dirty.update(range(self.lines))

        def _exit_alt(self):
            if not self._alt_active:
                return
            if self._saved_buffer is not None:
                self.buffer       = self._saved_buffer
                self._saved_buffer = None
            if self._saved_cursor is not None:
                self.cursor.x, self.cursor.y = self._saved_cursor
                self._saved_cursor = None
            self._alt_active = False
            self.dirty.update(range(self.lines))

class PtyReaderThread(QThread):
    data_ready = Signal(bytes)
    pty_closed = Signal()

    def __init__(self, proc):
        super().__init__()
        self._proc    = proc
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self._proc.read(4096)
                if data:
                    self.data_ready.emit(data)
            except (EOFError, OSError):
                break
        self.pty_closed.emit()

    def stop(self):
        self._running = False

class TerminalView(QWidget):

    title_changed = Signal(str)

    _KEY_MAP: dict = {
        Qt.Key.Key_Return:    b"\r",
        Qt.Key.Key_Enter:     b"\r",
        Qt.Key.Key_Backspace: b"\x7f",
        Qt.Key.Key_Delete:    b"\x1b[3~",
        Qt.Key.Key_Escape:    b"\x1b",
        Qt.Key.Key_Tab:       b"\t",
        Qt.Key.Key_Backtab:   b"\x1b[Z",
        Qt.Key.Key_Up:        b"\x1b[A",
        Qt.Key.Key_Down:      b"\x1b[B",
        Qt.Key.Key_Right:     b"\x1b[C",
        Qt.Key.Key_Left:      b"\x1b[D",
        Qt.Key.Key_Home:      b"\x1b[H",
        Qt.Key.Key_End:       b"\x1b[F",
        Qt.Key.Key_PageUp:    b"\x1b[5~",
        Qt.Key.Key_PageDown:  b"\x1b[6~",
        Qt.Key.Key_F1:        b"\x1bOP",
        Qt.Key.Key_F2:        b"\x1bOQ",
        Qt.Key.Key_F3:        b"\x1bOR",
        Qt.Key.Key_F4:        b"\x1bOS",
        Qt.Key.Key_F5:        b"\x1b[15~",
        Qt.Key.Key_F6:        b"\x1b[17~",
        Qt.Key.Key_F7:        b"\x1b[18~",
        Qt.Key.Key_F8:        b"\x1b[19~",
        Qt.Key.Key_F9:        b"\x1b[20~",
        Qt.Key.Key_F10:       b"\x1b[21~",
        Qt.Key.Key_F11:       b"\x1b[23~",
        Qt.Key.Key_F12:       b"\x1b[24~",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._font  = get_best_mono_font(10)
        fm           = QFontMetrics(self._font)
        self._cw     = fm.horizontalAdvance("M")
        self._ch     = fm.height()
        self._ascent = fm.ascent()
        self._cols   = 80
        self._rows   = 24

        self._screen : "TermScreen | None"           = None
        self._stream : "pyte.ByteStream | None"      = None
        self._proc   : "ptyprocess.PtyProcess | None" = None
        self._reader : PtyReaderThread | None         = None

        self._cursor_visible  = True
        self._repaint_pending = False

        self._blink = QTimer(self)
        self._blink.setInterval(530)
        self._blink.timeout.connect(self._blink_cursor)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, _DEFAULT_BG)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def start_shell(self, cwd: str | None = None):
        self._cols, self._rows = self._compute_grid()
        self._screen = TermScreen(self._cols, self._rows)
        self._stream = pyte.ByteStream(self._screen)
        self._screen.set_mode(pyte.modes.LNM)

        shell = self._detect_shell()
        env   = self._build_env()

        try:
            self._proc = ptyprocess.PtyProcess.spawn(
                [shell],
                cwd        = cwd or str(Path.home()),
                env        = env,
                dimensions = (self._rows, self._cols),
            )
        except Exception as exc:
            if self._screen:
                for ch in str(exc):
                    self._screen.draw(ch)
            self.update()
            return

        self._reader = PtyReaderThread(self._proc)
        self._reader.data_ready.connect(self._on_data, Qt.ConnectionType.QueuedConnection)
        self._reader.pty_closed.connect(self._on_closed, Qt.ConnectionType.QueuedConnection)
        self._reader.start()
        self._blink.start()

    def stop_shell(self):

        self._blink.stop()

        if self._proc is not None:
            try:
                if self._proc.isalive():
                    self._proc.terminate()
            except Exception:
                pass
            try:

                self._proc.close()
            except Exception:
                pass
            self._proc = None

        if self._reader is not None:
            self._reader.stop()

            if not self._reader.wait(2000):

                self._reader.terminate()
                self._reader.wait(1000)

            try:
                self._reader.data_ready.disconnect(self._on_data)
            except RuntimeError:
                pass
            try:
                self._reader.pty_closed.disconnect(self._on_closed)
            except RuntimeError:
                pass
            self._reader = None

    def _on_data(self, data: bytes):

        if self._screen is None or self._stream is None or self._proc is None:
            return
        self._stream.feed(data)
        if self._screen.title:
            self.title_changed.emit(self._screen.title)
        if self._screen.dirty:
            self._queue_repaint()
        self._screen.dirty.clear()

    def _on_closed(self):

        self._blink.stop()
        self.update()

    def _blink_cursor(self):
        self._cursor_visible = not self._cursor_visible
        if self._screen:
            row = self._screen.cursor.y
            self.update(QRect(0, row * self._ch, self.width(), self._ch))

    def _queue_repaint(self):
        if not self._repaint_pending:
            self._repaint_pending = True
            QTimer.singleShot(0, self._flush_repaint)

    def _flush_repaint(self):
        self._repaint_pending = False
        self.update()

    def paintEvent(self, _event):
        if self._screen is None:
            p = QPainter(self)
            p.fillRect(self.rect(), _DEFAULT_BG)
            return

        p   = QPainter(self)
        buf = self._screen.buffer
        cx  = self._screen.cursor.x
        cy  = self._screen.cursor.y
        cw  = self._cw
        ch  = self._ch
        asc = self._ascent

        for row in range(self._screen.lines):
            row_buf = buf[row]
            for col in range(self._screen.columns):
                cell = row_buf.get(col, self._screen.default_char)
                x = col * cw
                y = row * ch

                fg = _resolve_color(cell.fg, is_bg=False)
                bg = _resolve_color(cell.bg, is_bg=True)

                if cell.reverse:
                    fg, bg = bg, fg

                is_cursor = (col == cx and row == cy)
                if is_cursor and self._cursor_visible:
                    bg = _CURSOR_CLR
                    fg = _DEFAULT_BG

                p.fillRect(x, y, cw, ch, bg)

                if cell.data and cell.data != " ":
                    if cell.bold or cell.italics:
                        f = QFont(self._font)
                        f.setBold(cell.bold)
                        f.setItalic(cell.italics)
                        p.setFont(f)
                    else:
                        p.setFont(self._font)
                    p.setPen(fg)
                    p.drawText(x, y + asc, cell.data)

                if cell.underscore:
                    p.setPen(fg)
                    p.drawLine(x, y + ch - 2, x + cw - 1, y + ch - 2)

                if cell.strikethrough:
                    p.setPen(fg)
                    mid = y + ch // 2
                    p.drawLine(x, mid, x + cw - 1, mid)

        grid_w = self._screen.columns * cw
        grid_h = self._screen.lines   * ch
        if grid_w < self.width():
            p.fillRect(grid_w, 0, self.width() - grid_w, self.height(), _DEFAULT_BG)
        if grid_h < self.height():
            p.fillRect(0, grid_h, self.width(), self.height() - grid_h, _DEFAULT_BG)

    def keyPressEvent(self, event: QKeyEvent):
        if self._proc is None or not self._proc.isalive():
            return

        key  = event.key()
        ctrl = Qt.KeyboardModifier.ControlModifier
        mods = event.modifiers()

        if mods & ctrl:
            if   key == Qt.Key.Key_C: self._write(b"\x03"); return
            elif key == Qt.Key.Key_D: self._write(b"\x04"); return
            elif key == Qt.Key.Key_Z: self._write(b"\x1a"); return
            elif key == Qt.Key.Key_L: self._write(b"\x0c"); return
            elif key == Qt.Key.Key_W: self._write(b"\x17"); return
            elif key == Qt.Key.Key_A: self._write(b"\x01"); return
            elif key == Qt.Key.Key_E: self._write(b"\x05"); return
            elif key == Qt.Key.Key_U: self._write(b"\x15"); return
            elif key == Qt.Key.Key_K: self._write(b"\x0b"); return

        if key in self._KEY_MAP:
            self._write(self._KEY_MAP[key])
            return

        text = event.text()
        if text:
            self._write(text.encode("utf-8", errors="replace"))

    def _write(self, data: bytes):
        if self._proc and self._proc.isalive():
            try:
                self._proc.write(data)
            except OSError:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols, new_rows = self._compute_grid()
        if (new_cols, new_rows) == (self._cols, self._rows):
            return
        self._cols, self._rows = new_cols, new_rows
        if self._screen:
            self._screen.resize(new_rows, new_cols)
            self._screen.dirty.update(range(new_rows))
        if self._proc and self._proc.isalive():
            try:
                self._proc.setwinsize(new_rows, new_cols)
            except Exception:
                pass
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(self._cols * self._cw, self._rows * self._ch)

    def _compute_grid(self) -> tuple[int, int]:
        w    = max(self.width(),  self._cw * 40)
        h    = max(self.height(), self._ch * 10)
        return max(40, w // self._cw), max(10, h // self._ch)

    def _detect_shell(self) -> str:
        if _IS_WINDOWS:
            return os.environ.get("COMSPEC", "cmd.exe")
        for candidate in (os.environ.get("SHELL", ""), shutil.which("bash") or "", shutil.which("sh") or ""):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["TERM"]             = "xterm-256color"
        env["COLORTERM"]        = "truecolor"
        env["PYTHONUNBUFFERED"] = "1"
        env["COLUMNS"]          = str(self._cols)
        env["LINES"]            = str(self._rows)
        return env

    def send_text(self, text: str):
        self._write(text.encode("utf-8", errors="replace"))

    def send_command(self, cmd: str):
        self.send_text(cmd + "\n")

    def set_cwd(self, path: str):
        if path and os.path.isdir(path):
            self.send_command(f"cd {shlex.quote(path)}")

    @property
    def is_alive(self) -> bool:
        return bool(self._proc and self._proc.isalive())

class TerminalWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cwd = str(Path.home())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(8, 0, 8, 0)

        self._lbl_title = QLabel(tr("TERMINAL"))
        self._lbl_title.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )

        self._btn_kill = QPushButton()
        self._btn_kill.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        self._btn_kill.setToolTip(tr("Kill / restart shell"))
        self._btn_kill.setFixedSize(22, 22)
        self._btn_kill.setStyleSheet("border:none; background:transparent;")
        self._btn_kill.clicked.connect(self._restart)

        hdr_lay.addWidget(self._lbl_title)
        hdr_lay.addStretch()
        hdr_lay.addWidget(self._btn_kill)
        layout.addWidget(hdr)

        if _HAVE_PTY:
            self._view = TerminalView()
            self._view.title_changed.connect(self._on_title)
            layout.addWidget(self._view)
            self._view.start_shell(cwd=self.cwd)
        else:
            self._view = None
            self._build_fallback(layout)

    def _build_fallback(self, layout):
        from PySide6.QtWidgets import QPlainTextEdit, QLineEdit
        from PySide6.QtCore    import QProcess

        warn = QLabel(
            "⚠  pyte / ptyprocess no instalados.\n"
            "   pip install pyte ptyprocess\n"
            "   Modo básico activo (sin ncurses)."
        )
        warn.setStyleSheet(f"color:{VSCode.FG_DIM}; padding:8px; font-size:12px;")
        layout.addWidget(warn)

        self._fb_output = QPlainTextEdit()
        self._fb_output.setReadOnly(True)
        self._fb_output.setStyleSheet(
            f"background:{VSCode.TERMINAL_BG}; color:{VSCode.TERMINAL_FG};"
            "border:none; font-family:monospace; font-size:12px;"
        )
        layout.addWidget(self._fb_output)

        self._fb_input = QLineEdit()
        self._fb_input.setPlaceholderText("$ comando…")
        self._fb_input.setStyleSheet(
            f"background:{VSCode.TERMINAL_BG}; color:{VSCode.TERMINAL_FG};"
            f"border:none; border-top:1px solid {VSCode.BORDER}; padding:4px 8px; font-size:12px;"
        )
        self._fb_input.returnPressed.connect(self._fallback_run)
        layout.addWidget(self._fb_input)
        self._fb_proc = None

    def _fallback_run(self):
        from PySide6.QtCore import QProcess
        cmd = self._fb_input.text().strip()
        if not cmd:
            return
        self._fb_input.clear()
        self._fb_output.appendPlainText(f"$ {cmd}")
        proc = QProcess(self)
        proc.setWorkingDirectory(self.cwd)
        proc.readyReadStandardOutput.connect(
            lambda: self._fb_output.appendPlainText(
                bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
            )
        )
        proc.readyReadStandardError.connect(
            lambda: self._fb_output.appendPlainText(
                bytes(proc.readAllStandardError()).decode("utf-8", errors="replace")
            )
        )
        proc.start("bash", ["-c", cmd])
        self._fb_proc = proc

    def _on_title(self, title: str):
        label = (title[:40] + "…") if len(title) > 40 else title
        self._lbl_title.setText(label or tr("TERMINAL"))

    def _restart(self):
        if isinstance(self._view, TerminalView):
            self._view.stop_shell()
            self._view.start_shell(cwd=self.cwd)
            self._lbl_title.setText(tr("TERMINAL"))

    def set_cwd(self, path: str):
        if path and os.path.isdir(path):
            self.cwd = path
            if isinstance(self._view, TerminalView):
                self._view.set_cwd(path)

    def send_command(self, cmd: str):
        if isinstance(self._view, TerminalView):
            self._view.send_command(cmd)

    def closeEvent(self, event):
        if isinstance(self._view, TerminalView):
            self._view.stop_shell()
        super().closeEvent(event)
