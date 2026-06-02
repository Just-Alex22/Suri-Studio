# editor.py — CodeEditor con todas las features

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPlainTextEdit,
    QTextEdit, QLineEdit, QCheckBox, QPushButton,
    QFileDialog, QMessageBox, QInputDialog, QDialog,
    QVBoxLayout as QVL, QDialogButtonBox, QListWidget, QListWidgetItem,
    QComboBox, QLabel, QFormLayout,
)
from PySide6.QtCore import Qt, QRect, QSize, QRegularExpression, Signal, QTimer
from PySide6.QtGui import (
    QFont, QFontMetricsF, QColor, QPainter,
    QTextCursor, QTextFormat, QTextDocument, QKeySequence, QShortcut,
    QTextCharFormat,
)

from core.theme import VSCode, FONT_FAMILY
from core.highlighter import SyntaxHighlighter
from core.completer import CompletionPopup
from core.translate import tr

LANG_COMMENT = {
    'python': '#', 'ruby': '#', 'bash': '#', 'yaml': '#',
    'toml': '#', 'ini': '#', 'php': '//', 'javascript': '//',
    'typescript': '//', 'cpp': '//', 'java': '//', 'rust': '//',
    'go': '//', 'kotlin': '//', 'swift': '//', 'lua': '--',
    'sql': '--', 'css': '//', 'scss': '//',
    'html': '', 'xml': '', 'markdown': '',
}

_AUTOCOMPLETE_LANGS = {
    'python', 'javascript', 'typescript', 'cpp', 'java', 'rust', 'go',
    'bash', 'html', 'css', 'scss', 'sql', 'markdown', 'json', 'yaml',
}

# Diálogo para elegir lenguaje al crear archivo nuevo
_ALL_LANGS = [
    'text', 'python', 'javascript', 'typescript', 'html', 'css', 'scss',
    'cpp', 'java', 'rust', 'go', 'bash', 'sql', 'json', 'toml',
    'yaml', 'markdown', 'ruby', 'php', 'kotlin', 'swift', 'lua', 'xml', 'ini',
]


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo: elegir lenguaje para archivo nuevo
# ─────────────────────────────────────────────────────────────────────────────
class NewFileDialog(QDialog):
    def __init__(self, suggested_lang='text', parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("New file"))
        self.setFixedSize(300, 140)
        self.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG};"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        lbl = QLabel(tr("Language for new file"))
        lbl.setStyleSheet(f"color:{VSCode.FG_DIM}; font-size:12px;")

        self.combo = QComboBox()
        self.combo.addItems(_ALL_LANGS)
        idx = self.combo.findText(suggested_lang)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(lbl, self.combo)
        lay.addLayout(form)

        hint = QLabel(tr("Auto-detect on save"))
        hint.setStyleSheet(f"color:{VSCode.FG_INACTIVE}; font-size:11px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def chosen_lang(self) -> str:
        return self.combo.currentText()


# ─────────────────────────────────────────────────────────────────────────────
#  Área de numeración de líneas
# ─────────────────────────────────────────────────────────────────────────────
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor._line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor._paint_line_numbers(event)


# ─────────────────────────────────────────────────────────────────────────────
#  Editor principal
# ─────────────────────────────────────────────────────────────────────────────
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath    = None
        self.highlighter = None

        from core.theme import get_best_mono_font, FONT_FAMILY_EDITOR
        font = get_best_mono_font(13)
        self.setFont(font)
        self.setStyleSheet(
            f"QPlainTextEdit {{ font-family: {FONT_FAMILY_EDITOR};"
            f" font-size: 13px; }}"
        )

        try:
            from PySide6.QtCore import Qt as _Qt
            self.setAttribute(_Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        except Exception:
            pass

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(' ') * 4
        )

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        # Redibujar la franja de cambios cuando cambia el estado de modificación
        self.document().modificationChanged.connect(
            lambda _: self.line_number_area.update()
        )

        self._update_line_number_area_width(0)
        self._highlight_current_line()

        self._auto_pairs = {'"': '"', "'": "'", '(': ')', '[': ']', '{': '}'}

        # Autocompletado — carga diferida: se instancia al primer keystroke
        self._popup = None
        self.textChanged.connect(self._on_text_changed)

        # Resaltado de ocurrencias — timer para no recalcular en cada tecla
        self._occurrence_timer = QTimer(self)
        self._occurrence_timer.setSingleShot(True)
        self._occurrence_timer.setInterval(300)
        self._occurrence_timer.timeout.connect(self._highlight_occurrences)
        self._occurrence_fmt = QTextCharFormat()
        self._occurrence_fmt.setBackground(QColor("#3a3a2a"))
        self._occurrence_fmt.setForeground(QColor(VSCode.YELLOW))

        # Bracket matching
        self._bracket_open  = "({["
        self._bracket_close = ")}]"
        self._bracket_fmt   = QTextCharFormat()
        self._bracket_fmt.setBackground(QColor("#3b4048"))
        self._bracket_fmt.setForeground(QColor(VSCode.CYAN))

        # Word wrap state
        self._word_wrap    = False
        self._lint_manager = None

        self._bookmarks: set[int]  = set()
        self._bookmark_fmt         = QTextCharFormat()
        self._bookmark_fmt.setBackground(QColor("#1a3a5c"))

        self._pos_history:     list[int] = []
        self._pos_history_idx: int       = -1
        self._pos_recording:   bool      = True
        self._pos_timer = QTimer(self)
        self._pos_timer.setSingleShot(True)
        self._pos_timer.setInterval(1200)
        self._pos_timer.timeout.connect(self._record_position)
        self.cursorPositionChanged.connect(lambda: self._pos_timer.start())

    # ── Historial de posición ─────────────────────────────────────────────
    def _record_position(self) -> None:
        if not self._pos_recording:
            return
        pos = self.textCursor().position()
        if self._pos_history and self._pos_history[self._pos_history_idx] == pos:
            return
        if self._pos_history_idx < len(self._pos_history) - 1:
            self._pos_history = self._pos_history[:self._pos_history_idx + 1]
        self._pos_history.append(pos)
        if len(self._pos_history) > 100:
            self._pos_history.pop(0)
        self._pos_history_idx = len(self._pos_history) - 1

    def navigate_back(self) -> None:
        if self._pos_history_idx > 0:
            self._pos_history_idx -= 1
            self._jump_to(self._pos_history[self._pos_history_idx])

    def navigate_forward(self) -> None:
        if self._pos_history_idx < len(self._pos_history) - 1:
            self._pos_history_idx += 1
            self._jump_to(self._pos_history[self._pos_history_idx])

    def _jump_to(self, pos: int) -> None:
        self._pos_recording = False
        c = self.textCursor()
        c.setPosition(pos)
        self.setTextCursor(c)
        self.centerCursor()
        self._pos_recording = True

    # ── Marcadores de línea ───────────────────────────────────────────────
    def toggle_bookmark(self) -> None:
        line = self.textCursor().blockNumber()
        if line in self._bookmarks:
            self._bookmarks.discard(line)
        else:
            self._bookmarks.add(line)
        self.line_number_area.update()
        self._apply_bookmark_highlights()

    def _apply_bookmark_highlights(self) -> None:
        doc    = self.document()
        extras = []
        fmt    = QTextCharFormat()
        fmt.setBackground(QColor("#1a3a5c"))
        fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
        for line in self._bookmarks:
            block = doc.findBlockByNumber(line)
            if not block.isValid():
                continue
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            c = QTextCursor(block)
            sel.cursor = c
            extras.append(sel)
        non_bm = [s for s in self.extraSelections()
                  if s.format.background().color() != QColor("#1a3a5c")]
        self.setExtraSelections(non_bm + extras)

    def next_bookmark(self) -> None:
        if not self._bookmarks:
            return
        cur    = self.textCursor().blockNumber()
        after  = sorted(b for b in self._bookmarks if b > cur)
        target = after[0] if after else sorted(self._bookmarks)[0]
        c = self.textCursor()
        c.setPosition(self.document().findBlockByNumber(target).position())
        self.setTextCursor(c); self.centerCursor()

    def prev_bookmark(self) -> None:
        if not self._bookmarks:
            return
        cur    = self.textCursor().blockNumber()
        before = sorted((b for b in self._bookmarks if b < cur), reverse=True)
        target = before[0] if before else sorted(self._bookmarks, reverse=True)[0]
        c = self.textCursor()
        c.setPosition(self.document().findBlockByNumber(target).position())
        self.setTextCursor(c); self.centerCursor()

    # ── Ir a definición ───────────────────────────────────────────────────
    def goto_definition(self) -> None:
        import shutil, subprocess
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()
        if not word or not self.filepath:
            return
        if shutil.which("ctags") or shutil.which("universal-ctags"):
            tool = "universal-ctags" if shutil.which("universal-ctags") else "ctags"
            try:
                import json
                r = subprocess.run(
                    [tool, "--output-format=json", "-f", "-", self.filepath],
                    capture_output=True, text=True, timeout=5,
                    cwd=str(Path(self.filepath).parent)
                )
                for raw in r.stdout.splitlines():
                    try:
                        tag = json.loads(raw)
                        if tag.get("name") == word:
                            ln = tag.get("line", 1)
                            c  = self.textCursor()
                            c.setPosition(self.document().findBlockByNumber(ln - 1).position())
                            self.setTextCursor(c); self.centerCursor(); return
                    except Exception:
                        continue
            except Exception:
                pass
        lang = self._current_lang()
        patterns = {
            "python":     [rf'def\s+{re.escape(word)}\s*\(', rf'class\s+{re.escape(word)}\s*[:(]'],
            "javascript": [rf'function\s+{re.escape(word)}\s*\(', rf'class\s+{re.escape(word)}\b',
                           rf'const\s+{re.escape(word)}\s*='],
            "typescript": [rf'function\s+{re.escape(word)}\s*\(', rf'class\s+{re.escape(word)}\b',
                           rf'interface\s+{re.escape(word)}\b', rf'type\s+{re.escape(word)}\s*='],
            "cpp":        [rf'[\w:*&]+\s+{re.escape(word)}\s*\(', rf'class\s+{re.escape(word)}\b'],
            "rust":       [rf'fn\s+{re.escape(word)}\s*', rf'struct\s+{re.escape(word)}\b'],
        }
        pats = patterns.get(lang, [rf'\b{re.escape(word)}\s*[=({{(]'])
        cur_block = self.textCursor().blockNumber()
        try:
            lines = Path(self.filepath).read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, text in enumerate(lines):
                if i == cur_block:
                    continue
                if any(re.search(p, text) for p in pats):
                    c = self.textCursor()
                    c.setPosition(self.document().findBlockByNumber(i).position())
                    self.setTextCursor(c); self.centerCursor(); return
        except Exception:
            pass
    def set_language(self, language):
        if self.highlighter:
            self.highlighter.setDocument(None)
        self.highlighter = (
            SyntaxHighlighter(self.document(), language)
            if language != 'text' else None
        )

    def _current_lang(self):
        return self.highlighter.language if self.highlighter else 'text'

    # ── Word wrap ─────────────────────────────────────────────────────────
    def toggle_word_wrap(self):
        self._word_wrap = not self._word_wrap
        if self._word_wrap:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return self._word_wrap

    # ── Números de línea ──────────────────────────────────────────────────
    def _line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        fm = QFontMetricsF(self.font())
        # 4px extra a la izquierda para la franja de cambios
        return int(fm.horizontalAdvance('9') * (digits + 2)) + 14

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self._line_number_area_width(), cr.height())
        )
        if self._popup and self._popup.isVisible():
            self._popup and self._popup.hide()

    def _paint_line_numbers(self, event):
        painter = QPainter(self.line_number_area)
        w = self.line_number_area.width()
        painter.fillRect(event.rect(), QColor(VSCode.BG_LIGHT))
        if self.document().isModified():
            painter.fillRect(QRect(0, event.rect().top(), 3, event.rect().height()),
                             QColor(VSCode.YELLOW))
        block     = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top       = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom    = top + self.blockBoundingRect(block).height()
        fm        = QFontMetricsF(self.font())
        cur_line  = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if block_num in self._bookmarks:
                    painter.fillRect(QRect(3, int(top), w - 3, int(fm.height())),
                                     QColor("#1a3a5c"))
                    painter.setPen(QColor(VSCode.BLUE_ACCENT))
                    painter.drawText(4, int(top), 12, int(fm.height()),
                                     Qt.AlignmentFlag.AlignLeft, "◆")
                color = VSCode.FG if block_num == cur_line else VSCode.FG_DIM
                painter.setPen(QColor(color))
                painter.setFont(self.font())
                painter.drawText(14, int(top), w - 18, int(fm.height()),
                                 Qt.AlignmentFlag.AlignRight, str(block_num + 1))
            block     = block.next()
            top       = bottom
            bottom    = top + self.blockBoundingRect(block).height()
            block_num += 1

    # ── Señales de cursor/texto ───────────────────────────────────────────
    def _on_cursor_changed(self):
        self._highlight_current_line()
        self._match_brackets()
        self._occurrence_timer.start()

    def _on_text_changed(self):
        lang = self._current_lang()
        if lang in _AUTOCOMPLETE_LANGS:
            # Instanciar el popup la primera vez que el usuario escribe
            if self._popup is None:
                from core.completer import CompletionPopup
                self._popup = CompletionPopup(self)
            self._popup.schedule_update()
        elif self._popup:
            self._popup and self._popup.hide()

    # ── Resaltado de línea actual ─────────────────────────────────────────
    def _highlight_current_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#282828"))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        sel._kind = 'curline'
        self._refresh_extra_selections(curline=sel)

    # ── Resaltado de ocurrencias ──────────────────────────────────────────
    def _highlight_occurrences(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            # Seleccionar la palabra bajo el cursor
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()

        occur_sels = []
        if len(word) >= 2 and re.match(r'^\w+$', word):
            doc     = self.document()
            search  = QTextDocument.FindFlag(0)
            search |= QTextDocument.FindFlag.FindWholeWords
            c       = doc.find(word, 0, search)
            while not c.isNull():
                sel = QTextEdit.ExtraSelection()
                sel.format = self._occurrence_fmt
                sel.cursor = c
                sel._kind  = 'occurrence'
                occur_sels.append(sel)
                c = doc.find(word, c, search)

        self._refresh_extra_selections(occurrences=occur_sels)

    # ── Bracket matching ──────────────────────────────────────────────────
    def _match_brackets(self):
        cursor = self.textCursor()
        pos    = cursor.position()
        doc    = self.document()
        text   = doc.toPlainText()
        bracket_sels = []

        def find_match(pos, ch, pair, forward):
            depth = 0
            step  = 1 if forward else -1
            i     = pos
            while 0 <= i < len(text):
                if text[i] == ch:
                    depth += 1
                elif text[i] == pair:
                    depth -= 1
                    if depth == 0:
                        return i
                i += step
            return -1

        # Carácter antes o en el cursor
        for offset in (0, -1):
            p = pos + offset
            if 0 <= p < len(text):
                ch = text[p]
                if ch in self._bracket_open:
                    pair_ch  = self._bracket_close[self._bracket_open.index(ch)]
                    match_p  = find_match(p + 1, ch, pair_ch, True)
                elif ch in self._bracket_close:
                    pair_ch  = self._bracket_open[self._bracket_close.index(ch)]
                    match_p  = find_match(p - 1, ch, pair_ch, False)
                else:
                    continue

                for bp in (p, match_p):
                    if bp >= 0:
                        c = QTextCursor(doc)
                        c.setPosition(bp)
                        c.movePosition(
                            QTextCursor.MoveOperation.NextCharacter,
                            QTextCursor.MoveMode.KeepAnchor
                        )
                        sel = QTextEdit.ExtraSelection()
                        sel.format = self._bracket_fmt
                        sel.cursor = c
                        sel._kind  = 'bracket'
                        bracket_sels.append(sel)
                break

        self._refresh_extra_selections(brackets=bracket_sels)

    # ── Gestión centralizada de ExtraSelections ───────────────────────────
    def _refresh_extra_selections(self, **kwargs):
        if not hasattr(self, '_extra_store'):
            self._extra_store = {}
        self._extra_store.update(kwargs)
        combined = []
        for key in ('curline', 'occurrences', 'brackets', 'lint'):
            val = self._extra_store.get(key)
            if val is None:
                continue
            if isinstance(val, list):
                combined.extend(val)
            else:
                combined.append(val)
        self.setExtraSelections(combined)

    # ── Operaciones de texto ──────────────────────────────────────────────
    def duplicate_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText('\n' + text)

    def toggle_comment(self):
        lang   = self._current_lang()
        marker = LANG_COMMENT.get(lang, '#')
        if not marker:
            return
        cursor = self.textCursor()
        start  = cursor.selectionStart()
        end    = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        first_block = cursor.blockNumber()
        cursor.setPosition(end)
        if cursor.atBlockStart() and end > start:
            cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        last_block = cursor.blockNumber()

        all_commented = True
        c = self.textCursor()
        c.setPosition(start)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        for _ in range(last_block - first_block + 1):
            if not c.block().text().lstrip().startswith(marker):
                all_commented = False
                break
            c.movePosition(QTextCursor.MoveOperation.NextBlock)

        c = self.textCursor()
        c.setPosition(start)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.beginEditBlock()
        for _ in range(last_block - first_block + 1):
            line = c.block().text()
            if all_commented:
                idx = line.find(marker)
                if idx >= 0:
                    c.setPosition(c.block().position() + idx)
                    for _ in range(len(marker)):
                        c.deleteChar()
                    if c.block().text()[idx:idx+1] == ' ':
                        c.deleteChar()
            else:
                c.setPosition(c.block().position())
                stripped = line.lstrip()
                indent   = len(line) - len(stripped)
                c.setPosition(c.block().position() + indent)
                c.insertText(marker + ' ')
            c.movePosition(QTextCursor.MoveOperation.NextBlock)
        c.endEditBlock()

    def remove_all_comments(self):
        """Elimina todos los comentarios del documento (líneas enteras e inline)."""
        lang   = self._current_lang()
        marker = LANG_COMMENT.get(lang, '#')
        if not marker:
            return
        doc    = self.document()
        cursor = self.textCursor()
        cursor.beginEditBlock()
        block  = doc.begin()
        while block.isValid():
            text   = block.text()
            stripped = text.lstrip()
            next_b = block.next()
            if stripped.startswith(marker):
                # Línea entera de comentario — borrar bloque completo.
                # Seleccionamos desde el inicio del bloque hasta el inicio
                # del siguiente (incluye el \n), excepto si es el último
                # bloque del documento (donde no hay \n final).
                c = QTextCursor(block)
                c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                if next_b.isValid():
                    # Hay bloque siguiente: seleccionar hasta su inicio (incluye \n)
                    c.movePosition(
                        QTextCursor.MoveOperation.NextBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                else:
                    # Último bloque: extender la selección hacia atrás para
                    # incluir el \n que lo separa del bloque anterior (si existe).
                    start = block.position()
                    end   = block.position() + block.length() - 1  # sin \n final de Qt
                    if start > 0:
                        c.setPosition(start - 1)   # retroceder al \n anterior
                    c.setPosition(max(end, c.position()),
                                  QTextCursor.MoveMode.KeepAnchor)
                c.removeSelectedText()
            else:
                # Comentario inline — buscar marcador fuera de strings
                idx = self._find_comment_start(text, marker)
                if idx > 0:
                    c = QTextCursor(block)
                    c.setPosition(block.position() + idx)
                    c.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor
                    )
                    c.removeSelectedText()
                    # Limpiar espacio en blanco sobrante al final
                    new_text = block.text().rstrip()
                    c2 = QTextCursor(block)
                    c2.select(QTextCursor.SelectionType.BlockUnderCursor)
                    c2.insertText(new_text)
            block = next_b
        cursor.endEditBlock()

    @staticmethod
    def _find_comment_start(text: str, marker: str) -> int:
        """
        Devuelve la posición del marcador de comentario ignorando
        los que están dentro de strings (simples o dobles).
        Devuelve -1 si no hay comentario fuera de strings.
        """
        in_single = False
        in_double = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif not in_single and not in_double:
                if text[i:i+len(marker)] == marker:
                    return i
            i += 1
        return -1

    def move_line_up(self):
        cursor = self.textCursor()
        if cursor.blockNumber() == 0:
            return
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(text + '\n')
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        self.setTextCursor(cursor)

    def move_line_down(self):
        cursor = self.textCursor()
        if cursor.blockNumber() == self.document().blockCount() - 1:
            return
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        cursor.removeSelectedText()
        cursor.deleteChar()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText('\n' + text)
        self.setTextCursor(cursor)

    def select_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    def indent_selection(self, dedent=False):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            if dedent:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                line   = cursor.block().text()
                spaces = len(line) - len(line.lstrip(' '))
                for _ in range(min(4, spaces)):
                    cursor.deleteChar()
            else:
                self.insertPlainText('    ')
            return
        start = cursor.selectionStart()
        end   = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        first = cursor.blockNumber()
        cursor.setPosition(end)
        if cursor.atBlockStart() and end > start:
            cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        last = cursor.blockNumber()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        for _ in range(last - first + 1):
            if dedent:
                line   = cursor.block().text()
                spaces = len(line) - len(line.lstrip(' '))
                for _ in range(min(4, spaces)):
                    cursor.deleteChar()
            else:
                cursor.insertText('    ')
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
        cursor.endEditBlock()

    # ── keyPressEvent ─────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        if self._popup and self._popup.handle_key(event):
            return

        key  = event.key()
        mods = event.modifiers()
        text = event.text()

        ctrl  = mods == Qt.KeyboardModifier.ControlModifier
        alt   = mods == Qt.KeyboardModifier.AltModifier
        shift = mods == Qt.KeyboardModifier.ShiftModifier
        ctrl_shift = mods == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)

        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right,
                   Qt.Key.Key_Home, Qt.Key.Key_End,
                   Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            self._popup and self._popup.hide()

        if key == Qt.Key.Key_F7:
            if shift:
                self.prev_bookmark()
            elif ctrl:
                self.next_bookmark()
            else:
                self.toggle_bookmark()
            return

        if key == Qt.Key.Key_F12:
            self.goto_definition(); return

        if alt and key == Qt.Key.Key_Left:
            self.navigate_back(); return
        if alt and key == Qt.Key.Key_Right:
            self.navigate_forward(); return

        if ctrl and key == Qt.Key.Key_D:
            self.duplicate_line(); return
        if ctrl and key == Qt.Key.Key_Slash:
            self.toggle_comment(); return
        if ctrl and key == Qt.Key.Key_L:
            self.select_line(); return
        if alt and key == Qt.Key.Key_Up:
            self.move_line_up(); return
        if alt and key == Qt.Key.Key_Down:
            self.move_line_down(); return

        if key == Qt.Key.Key_Tab:
            if self.textCursor().hasSelection():
                self.indent_selection(dedent=False)
            else:
                self.insertPlainText('    ')
            return
        if key == Qt.Key.Key_Backtab:
            self.indent_selection(dedent=True); return

        if key == Qt.Key.Key_Return:
            self._popup and self._popup.hide()
            cursor     = self.textCursor()
            block_text = cursor.block().text()
            indent     = len(block_text) - len(block_text.lstrip())
            extra      = '    ' if block_text.rstrip().endswith((':', '{', '(', '[')) else ''
            super().keyPressEvent(event)
            self.insertPlainText(' ' * indent + extra)
            return

        if text and not (text.isalnum() or text in ('_', '.')):
            self._popup and self._popup.hide()

        if text in self._auto_pairs:
            super().keyPressEvent(event)
            self.insertPlainText(self._auto_pairs[text])
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            self._rect_anchor    = event.pos()
            self._rect_selecting = True
        else:
            self._rect_selecting = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_rect_selecting', False):
            self._do_rect_select(self._rect_anchor, event.pos())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._rect_selecting = False
        super().mouseReleaseEvent(event)

    def _do_rect_select(self, p1, p2) -> None:
        c1   = self.cursorForPosition(p1)
        c2   = self.cursorForPosition(p2)
        rmin = min(c1.blockNumber(), c2.blockNumber())
        rmax = max(c1.blockNumber(), c2.blockNumber())
        cmin = min(c1.columnNumber(), c2.columnNumber())
        cmax = max(c1.columnNumber(), c2.columnNumber())
        doc  = self.document()
        fmt  = QTextCharFormat()
        fmt.setBackground(QColor(VSCode.SELECTION))
        sels = []
        for row in range(rmin, rmax + 1):
            block = doc.findBlockByNumber(row)
            if not block.isValid():
                continue
            blen  = len(block.text())
            start = block.position() + min(cmin, blen)
            end   = block.position() + min(cmax, blen)
            if start >= end:
                continue
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            c = QTextCursor(doc)
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            sels.append(sel)
        others = [s for s in self.extraSelections()
                  if s.format.background().color() != QColor(VSCode.SELECTION)]
        self.setExtraSelections(others + sels)


# ─────────────────────────────────────────────────────────────────────────────
#  Barra Buscar / Reemplazar
# ─────────────────────────────────────────────────────────────────────────────
class FindReplaceBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("find_bar")
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.find_input    = QLineEdit(placeholderText=tr("Find…"))
        self.replace_input = QLineEdit(placeholderText=tr("Replace with…"))
        self.case_check    = QCheckBox("Aa")
        self.case_check.setToolTip(tr("Case sensitive"))
        self.regex_check   = QCheckBox(".*")
        self.regex_check.setToolTip(tr("Regex"))
        self.btn_prev      = QPushButton("↑")
        self.btn_next      = QPushButton("↓")
        self.btn_repl      = QPushButton(tr("Replace"))
        self.btn_all       = QPushButton(tr("All"))
        self.btn_close     = QPushButton("✕")

        self.btn_prev.setFixedWidth(28)
        self.btn_next.setFixedWidth(28)
        self.btn_close.setFixedWidth(28)
        self.find_input.setMinimumWidth(200)
        self.replace_input.setMinimumWidth(180)

        for w in [self.find_input, self.replace_input, self.case_check,
                  self.regex_check, self.btn_prev, self.btn_next,
                  self.btn_repl, self.btn_all, self.btn_close]:
            layout.addWidget(w)
        layout.addStretch()

        self.setStyleSheet(
            f"background-color: {VSCode.BG_LIGHT}; "
            f"border-top: 1px solid {VSCode.BORDER};"
        )
        self.find_input.returnPressed.connect(lambda: self.btn_next.click())

    def toggle(self):
        self.setVisible(not self.isVisible())
        if self.isVisible():
            self.find_input.setFocus()
            self.find_input.selectAll()


# ─────────────────────────────────────────────────────────────────────────────
#  Tab de editor
# ─────────────────────────────────────────────────────────────────────────────
class EditorTab(QWidget):
    modified_changed  = Signal(bool)

    def __init__(self, filepath=None, parent=None, initial_lang=None):
        super().__init__(parent)
        self.filepath       = filepath
        self._saved_content = ""
        self._is_new        = (filepath is None)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor   = CodeEditor()
        self.find_bar = FindReplaceBar()

        layout.addWidget(self.editor)
        layout.addWidget(self.find_bar)

        # Linter — carga diferida: se crea tras detectar el lenguaje
        self._lint_mgr = None

        self.editor.document().contentsChanged.connect(self._on_modified)
        self.find_bar.btn_next.clicked.connect(lambda: self._find(forward=True))
        self.find_bar.btn_prev.clicked.connect(lambda: self._find(forward=False))
        self.find_bar.btn_repl.clicked.connect(self._replace_one)
        self.find_bar.btn_all.clicked.connect(self._replace_all)
        self.find_bar.btn_close.clicked.connect(self.find_bar.toggle)

        QShortcut(QKeySequence("Ctrl+G"), self, self._go_to_line)
        QShortcut(QKeySequence("Escape"), self,
                  lambda: self.find_bar.setVisible(False))

        if filepath:
            self._load_file(filepath)
        else:
            lang = initial_lang or 'text'
            self.editor.set_language(lang)
            self._init_linter_if_needed(lang)

    def _init_linter_if_needed(self, lang: str) -> None:
        """Instancia LintManager solo si el lenguaje tiene soporte de linting."""
        _LINTABLE = {'python', 'javascript', 'typescript', 'bash', 'ruby', 'css', 'scss'}
        if lang in _LINTABLE and self._lint_mgr is None:
            from editor.linter import LintManager
            self._lint_mgr = LintManager(self.editor, parent=self)

    # ── Carga / guardado ──────────────────────────────────────────────────
    def _load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            self._saved_content = content
            self.editor.setPlainText(content)
            lang = SyntaxHighlighter.detect_language(path)
            self.editor.set_language(lang)
            self.editor.document().setModified(False)
            self._is_new = False
            self._init_linter_if_needed(lang)
            # Restaurar posición del cursor
            self._restore_cursor()
        except Exception as e:
            self.editor.setPlainText(tr("Error opening").format(err=e))

    def _restore_cursor(self) -> None:
        if not self.filepath:
            return
        try:
            from core.settings import load_cursor_pos
            line, col = load_cursor_pos(self.filepath)
            if line == 0 and col == 0:
                return
            doc    = self.editor.document()
            block  = doc.findBlockByNumber(line)
            if not block.isValid():
                return
            cursor = self.editor.textCursor()
            pos    = block.position() + min(col, block.length() - 1)
            cursor.setPosition(pos)
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()
        except Exception:
            pass

    def save_cursor(self) -> None:
        """Guarda la posición actual del cursor en QSettings."""
        if not self.filepath:
            return
        try:
            from core.settings import save_cursor_pos
            cursor = self.editor.textCursor()
            save_cursor_pos(
                self.filepath,
                cursor.blockNumber(),
                cursor.columnNumber()
            )
        except Exception:
            pass

    def load_content(self, content: str, language: str = 'text'):
        self.editor.setPlainText(content)
        self.editor.set_language(language)
        self.editor.document().setModified(True)
        self._is_new = True

    def save(self):
        if not self.filepath:
            return self.save_as()
        try:
            content = self.editor.toPlainText()
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self._saved_content = content
            self._is_new = False
            self.editor.document().setModified(False)
            self.modified_changed.emit(False)
            self._delete_snapshot()
            self.save_cursor()
            # Re-detectar lenguaje si cambió la extensión
            lang = SyntaxHighlighter.detect_language(self.filepath)
            if lang != self.editor._current_lang():
                self.editor.set_language(lang)
                self._init_linter_if_needed(lang)
            return True
        except Exception as e:
            QMessageBox.critical(self, tr("Error saving"), tr("Error saving").format(err=e))
            return False

    def _delete_snapshot(self):
        try:
            import hashlib
            if self.filepath:
                from core.autosave import _snapshot_path
                p = _snapshot_path(hashlib.md5(self.filepath.encode()).hexdigest())
                if p.exists():
                    p.unlink()
        except Exception:
            pass

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("Save as…"))
        if path:
            self.filepath = path
            return self.save()
        return False

    def is_modified(self):
        return self.editor.document().isModified()

    def get_title(self):
        name = Path(self.filepath).name if self.filepath else tr("Untitled")
        return name


    def _on_modified(self):
        self.modified_changed.emit(self.is_modified())

    def _go_to_line(self):
        total = self.editor.document().blockCount()
        line, ok = QInputDialog.getInt(
            self, tr("Go to line title"), tr("Go to line prompt").format(n=total),
            self.editor.textCursor().blockNumber() + 1, 1, total
        )
        if ok:
            cursor = self.editor.textCursor()
            cursor.setPosition(
                self.editor.document().findBlockByNumber(line - 1).position()
            )
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()

    # ── Buscar / Reemplazar ───────────────────────────────────────────────
    def _flags(self):
        f = QTextDocument.FindFlag(0)
        if self.find_bar.case_check.isChecked():
            f |= QTextDocument.FindFlag.FindCaseSensitively
        return f

    def _find(self, forward=True):
        term = self.find_bar.find_input.text()
        if not term:
            return
        flags  = self._flags()
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        doc    = self.editor.document()
        cursor = self.editor.textCursor()
        use_rx = self.find_bar.regex_check.isChecked()
        found  = (doc.find(QRegularExpression(term), cursor, flags)
                  if use_rx else doc.find(term, cursor, flags))
        if found.isNull():
            wrap = self.editor.textCursor()
            wrap.movePosition(
                QTextCursor.MoveOperation.Start if forward
                else QTextCursor.MoveOperation.End
            )
            self.editor.setTextCursor(wrap)
            found = (doc.find(QRegularExpression(term), wrap, flags)
                     if use_rx else doc.find(term, wrap, flags))
        if not found.isNull():
            self.editor.setTextCursor(found)

    def _replace_one(self):
        self._find(forward=True)
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.find_bar.replace_input.text())

    def _replace_all(self):
        term = self.find_bar.find_input.text()
        repl = self.find_bar.replace_input.text()
        if not term:
            return
        content = self.editor.toPlainText()
        if self.find_bar.regex_check.isChecked():
            flags = 0 if self.find_bar.case_check.isChecked() else re.IGNORECASE
            new_content = re.sub(term, repl, content, flags=flags)
        else:
            if self.find_bar.case_check.isChecked():
                new_content = content.replace(term, repl)
            else:
                new_content = re.sub(re.escape(term), repl, content,
                                     flags=re.IGNORECASE)
        self.editor.setPlainText(new_content)


# ─────────────────────────────────────────────────────────────────────────────
#  SplitEditorTab — dos editores lado a lado
# ─────────────────────────────────────────────────────────────────────────────
class SplitEditorContainer(QWidget):
    """
    Contenedor que aloja uno o dos EditorTab en un QSplitter.
    El tab principal vive en self.primary.
    Al hacer split se añade self.secondary.
    """
    modified_changed  = Signal(bool)

    def __init__(self, filepath=None, parent=None, initial_lang=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self.primary   = EditorTab(filepath=filepath, parent=self,
                                   initial_lang=initial_lang)
        self.secondary: EditorTab | None = None

        self._splitter.addWidget(self.primary)
        self._layout.addWidget(self._splitter)

        self.primary.modified_changed.connect(self.modified_changed)

    # Delegación al primario para compatibilidad con mainwindow
    @property
    def editor(self):  return self.primary.editor
    @property
    def find_bar(self): return self.primary.find_bar
    @property
    def filepath(self): return self.primary.filepath
    @filepath.setter
    def filepath(self, v): self.primary.filepath = v

    def save(self):     return self.primary.save()
    def save_as(self):  return self.primary.save_as()
    def is_modified(self): return self.primary.is_modified()
    def get_title(self):   return self.primary.get_title()
    def load_content(self, content, language='text'):
        self.primary.load_content(content, language)

    def split(self, filepath=None):
        """Abre un segundo editor a la derecha."""
        if self.secondary:
            return
        self.secondary = EditorTab(filepath=filepath, parent=self)
        self._splitter.addWidget(self.secondary)
        self._splitter.setSizes([500, 500])
        self.secondary.editor.setFocus()

    def close_split(self):
        """Cierra el editor secundario."""
        if self.secondary:
            self.secondary.setParent(None)
            self.secondary.deleteLater()
            self.secondary = None
            self.primary.editor.setFocus()

    def has_split(self) -> bool:
        return self.secondary is not None
