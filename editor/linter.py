
from __future__ import annotations
import re
import shutil
import subprocess
import tempfile
import json
from pathlib import Path

from PySide6.QtCore    import QThread, Signal, QTimer, QObject
from PySide6.QtGui     import QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import QTextEdit

class LintWorker(QThread):
    results_ready = Signal(list)

    def __init__(self, code: str, lang: str, filepath: str = ""):
        super().__init__()
        self._code     = code
        self._lang     = lang
        self._filepath = filepath

    def run(self) -> None:
        try:
            results = _dispatch(self._code, self._lang, self._filepath)
        except Exception:
            results = []
        self.results_ready.emit(results)

def _dispatch(code: str, lang: str, filepath: str) -> list:
    if lang == 'python':
        return _python(code, filepath)
    if lang in ('javascript', 'typescript'):
        return _js(code, lang, filepath)
    if lang == 'bash':
        return _bash(code, filepath)
    if lang == 'ruby':
        return _ruby(code, filepath)
    if lang in ('css', 'scss'):
        return _css(code, lang, filepath)
    return []

def _python(code: str, filepath: str) -> list:
    result = _ruff(code) or _pyflakes(code)
    return result

def _ruff(code: str) -> list | None:
    if not shutil.which('ruff'):
        return None
    with _tmp('.py', code) as tmp:
        r = _run(['ruff', 'check', '--output-format=concise', '--no-fix', tmp])
    results = []
    for line in r.splitlines():
        m = re.match(r'.+:(\d+):(\d+): (\w+) (.+)', line)
        if m:
            ln, col = int(m.group(1)) - 1, int(m.group(2)) - 1
            code_id, msg = m.group(3), m.group(4)
            sev = 'error' if code_id.startswith(('E9', 'F8')) else 'warning'
            results.append((ln, col, f"{code_id}: {msg}", sev))
    return results or None

def _pyflakes(code: str) -> list:
    if not shutil.which('pyflakes'):
        return []
    with _tmp('.py', code) as tmp:
        r = _run(['pyflakes', tmp])
    results = []
    for line in r.splitlines():
        m = re.match(r'.+:(\d+)(?::(\d+))?: (.+)', line)
        if m:
            ln  = int(m.group(1)) - 1
            col = int(m.group(2) or 0)
            results.append((ln, col, m.group(3), 'error'))
    return results

def _js(code: str, lang: str, filepath: str) -> list:
    if not shutil.which('eslint'):
        return []
    ext = '.ts' if lang == 'typescript' else '.js'

    if filepath and Path(filepath).exists():
        src = filepath
        use_tmp = False
    else:
        use_tmp = True

    if use_tmp:
        with _tmp(ext, code) as tmp:
            r = _run(['eslint', '--format=json', '--no-ignore', tmp])
            src = tmp
    else:
        r = _run(['eslint', '--format=json', filepath])

    results = []
    try:
        data = json.loads(r)
        for file_result in data:
            for msg in file_result.get('messages', []):
                ln   = msg.get('line', 1) - 1
                col  = msg.get('column', 1) - 1
                text = msg.get('message', '')
                rule = msg.get('ruleId', '')
                sev  = 'error' if msg.get('severity', 1) == 2 else 'warning'
                full = f"{rule}: {text}" if rule else text
                results.append((ln, col, full, sev))
    except (json.JSONDecodeError, KeyError):
        pass
    return results

def _bash(code: str, filepath: str) -> list:
    if not shutil.which('shellcheck'):
        return []
    with _tmp('.sh', code) as tmp:
        r = _run(['shellcheck', '--format=json', tmp])
    results = []
    try:
        data = json.loads(r)
        for item in data:
            ln   = item.get('line', 1) - 1
            col  = item.get('column', 1) - 1
            msg  = item.get('message', '')
            code_id = item.get('code', '')
            level   = item.get('level', 'warning')
            sev  = 'error' if level == 'error' else 'warning'
            results.append((ln, col, f"SC{code_id}: {msg}", sev))
    except (json.JSONDecodeError, KeyError):
        pass
    return results

def _ruby(code: str, filepath: str) -> list:
    if not shutil.which('rubocop'):
        return []
    with _tmp('.rb', code) as tmp:
        r = _run(['rubocop', '--format=json', '--no-color', tmp])
    results = []
    try:
        data = json.loads(r)
        for file_result in data.get('files', []):
            for offense in file_result.get('offenses', []):
                loc  = offense.get('location', {})
                ln   = loc.get('line', 1) - 1
                col  = loc.get('column', 1) - 1
                msg  = offense.get('message', '')
                cop  = offense.get('cop_name', '')
                sev  = offense.get('severity', 'convention')
                level = 'error' if sev in ('error', 'fatal') else 'warning'
                results.append((ln, col, f"{cop}: {msg}", level))
    except (json.JSONDecodeError, KeyError):
        pass
    return results

def _css(code: str, lang: str, filepath: str) -> list:
    if not shutil.which('stylelint'):
        return []
    ext = '.scss' if lang == 'scss' else '.css'
    with _tmp(ext, code) as tmp:
        r = _run(['stylelint', '--formatter=json', tmp])
    results = []
    try:
        data = json.loads(r)
        for file_result in data:
            for warn in file_result.get('warnings', []):
                ln   = warn.get('line', 1) - 1
                col  = warn.get('column', 1) - 1
                msg  = warn.get('text', '')
                sev  = 'error' if warn.get('severity') == 'error' else 'warning'
                results.append((ln, col, msg, sev))
    except (json.JSONDecodeError, KeyError):
        pass
    return results

class _tmp:

    def __init__(self, suffix: str, content: str):
        self._suffix  = suffix
        self._content = content
        self._path    = None

    def __enter__(self) -> str:
        import tempfile
        f = tempfile.NamedTemporaryFile(
            suffix=self._suffix, mode='w',
            encoding='utf-8', delete=False
        )
        f.write(self._content)
        f.close()
        self._path = f.name
        return self._path

    def __exit__(self, *_) -> None:
        if self._path:
            Path(self._path).unlink(missing_ok=True)

def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15
        )
        return r.stdout + r.stderr
    except Exception:
        return ""

_LINTABLE = {'python', 'javascript', 'typescript', 'bash', 'ruby', 'css', 'scss'}

class LintManager(QObject):

    errors_updated = Signal(list)
    DELAY_MS = 900

    _FMT_ERROR:   QTextCharFormat | None = None
    _FMT_WARNING: QTextCharFormat | None = None

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._worker: LintWorker | None = None
        self._timer  = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.DELAY_MS)
        self._timer.timeout.connect(self._run_lint)
        self._errors: list = []

        editor.document().contentsChanged.connect(self._schedule)

    def _schedule(self) -> None:
        lang = self._editor._current_lang()
        if lang in _LINTABLE:
            self._timer.start()
        else:
            self._clear_marks()
            self._errors = []
            self.errors_updated.emit([])

    def _run_lint(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        lang     = self._editor._current_lang()
        code     = self._editor.toPlainText()
        filepath = getattr(self._editor, 'filepath', '') or ''
        self._worker = LintWorker(code, lang, filepath)
        self._worker.results_ready.connect(self._apply_results)
        self._worker.start()

    def _apply_results(self, results: list) -> None:
        self._errors = results
        self._mark_errors()
        self.errors_updated.emit(results)

    def _clear_marks(self) -> None:
        sels = [s for s in self._editor.extraSelections()
                if not getattr(s, '_lint', False)]
        self._editor.setExtraSelections(sels)

    def _mark_errors(self) -> None:
        if LintManager._FMT_ERROR is None:
            e = QTextCharFormat()
            e.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            e.setUnderlineColor(QColor("#f44747"))
            LintManager._FMT_ERROR = e
            w = QTextCharFormat()
            w.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            w.setUnderlineColor(QColor("#e5c07b"))
            LintManager._FMT_WARNING = w

        doc       = self._editor.document()
        lint_sels = []
        for ln, col, msg, sev in self._errors:
            block = doc.findBlockByNumber(ln)
            if not block.isValid():
                continue
            fmt = LintManager._FMT_ERROR if sev == 'error' else LintManager._FMT_WARNING
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            sel.format.setToolTip(msg)
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfWord,
                                QTextCursor.MoveMode.KeepAnchor)
            if not cursor.selectedText().strip():
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                    QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor
            sel._lint  = True
            lint_sels.append(sel)

        existing = [s for s in self._editor.extraSelections()
                    if not getattr(s, '_lint', False)]
        self._editor.setExtraSelections(existing + lint_sels)

    def get_errors(self) -> list:
        return self._errors

    def stop(self) -> None:
        self._timer.stop()
        if self._worker:
            self._worker.wait(300)
