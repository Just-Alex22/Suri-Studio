
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QTabBar, QTreeView, QFileSystemModel,
    QLabel, QPushButton, QFileDialog, QMessageBox, QStyle,
    QDialog, QDialogButtonBox, QScrollArea,
)
from PySide6.QtCore  import Qt, QSize
from PySide6.QtGui   import (
    QKeySequence, QAction, QPainter, QColor, QIcon,
    QFont, QFontMetricsF, QPixmap,
)

from core.theme     import VSCode, load_theme, set_theme, get_theme, THEMES, build_qss
from core.autosave  import AutosaveManager
from core.settings  import (
    save_window, restore_window, save_session, load_session,
    save_font_size, load_font_size, save_folder, load_folder,
    add_recent, get_recent, clear_recent,
)
from core.translate import tr, load_language, set_language, get_language, LANGUAGES
from core.highlighter import SyntaxHighlighter
from editor.editor  import SplitEditorContainer, NewFileDialog
from tools.terminal import TerminalWidget
from tools.scratchpad import ScratchPadWidget
from tools.runner   import run_file, build_only, get_template
from ui.panels      import BottomPanel
from ui.palette     import CommandPalette
from ui.git_panel   import GitPanel
from ui.symbols_panel import SymbolsPanel

def _assets_dir() -> Path:
    return Path(__file__).parent.parent / "assets"

def _needs_embedded_menubar() -> bool:

    import sys, os

    if sys.platform in ("darwin", "win32"):
        return False

    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type != "wayland":
        return False

    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    safe_desktops   = {"KDE", "GNOME", "UNITY", "PANTHEON", "DEEPIN"}
    for safe in safe_desktops:
        if safe in current_desktop:
            return False

    if os.environ.get("QT_QPA_PLATFORMTHEME", ""):
        return False

    return True

class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.splitter  = QSplitter(Qt.Orientation.Vertical)
        self.terminal  = TerminalWidget()
        self.scratchpad = ScratchPadWidget()
        self.splitter.addWidget(self.terminal)
        self.splitter.addWidget(self.scratchpad)
        self.splitter.setSizes([350, 200])
        lay.addWidget(self.splitter)

    @property
    def terminal_widget(self) -> TerminalWidget:
        return self.terminal

    def save_scratch(self) -> None:
        self.scratchpad.save_now()

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("About Suri Studio"))
        self.setFixedSize(480, 340)
        self.setSizeGripEnabled(False)

        bg_path = _assets_dir() / "about_background.jpg"
        if bg_path.exists():
            pix = QPixmap(str(bg_path)).scaled(
                480, 340,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            pal = self.palette()
            pal.setBrush(self.backgroundRole(), pix)
            self.setPalette(pal)
            self.setAutoFillBackground(True)

            overlay_style = "background: rgba(20,20,20,0.72); color: #d4d4d4;"
        else:
            self.setStyleSheet(f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG};")
            overlay_style = f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG};"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        container = QWidget()
        container.setStyleSheet(overlay_style)
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(28, 24, 28, 18)
        c_lay.setSpacing(10)

        top = QHBoxLayout(); top.setSpacing(20)
        logo_path = _assets_dir() / "logo.svg"
        if logo_path.exists():
            try:
                from PySide6.QtSvg import QSvgRenderer
                renderer = QSvgRenderer(str(logo_path))
                if renderer.isValid():
                    pix_logo = QPixmap(80, 80)
                    pix_logo.fill(Qt.GlobalColor.transparent)
                    p = QPainter(pix_logo)
                    renderer.render(p); p.end()
                    lbl_logo = QLabel()
                    lbl_logo.setPixmap(pix_logo)
                    lbl_logo.setFixedSize(80, 80)
                    lbl_logo.setStyleSheet("background:transparent;")
                    top.addWidget(lbl_logo)
                else:
                    self._placeholder(top)
            except Exception:
                self._placeholder(top)
        else:
            self._placeholder(top)

        nb = QVBoxLayout(); nb.setSpacing(4)
        for text, fs, fw, color in [
            ("Suri Studio",         "26px", "bold",   "#ffffff"),
            (tr("app_subtitle"),    "11px", "normal", "rgba(255,255,255,0.80)"),
            (tr("app_framework").format(theme=THEMES.get(get_theme(), "VSCode Dark+")),
                                    "10px", "normal", "rgba(255,255,255,0.60)"),
        ]:
            l = QLabel(text)
            l.setStyleSheet(
                f"font-size:{fs}; font-weight:{fw}; color:{color}; background:transparent;"
            )
            nb.addWidget(l)
        nb.addStretch()
        top.addLayout(nb); top.addStretch()
        c_lay.addLayout(top)

        sep = QWidget(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.20);")
        c_lay.addWidget(sep)

        grid = QVBoxLayout(); grid.setSpacing(5)
        for lbl_t, val_t, url in [
            (tr("Developed by"),  "CuerdOS Dev Team",  None),
            (tr("Copyright"),     "© 2026 CuerdOS Dev Team", None),
            (tr("License"),       "MIT License",       "https://opensource.org/licenses/MIT"),
            (tr("Website"),       "cuerdos.github.io", "https://cuerdos.github.io"),
        ]:
            row = QHBoxLayout()
            lk = QLabel(lbl_t + ":")
            lk.setFixedWidth(115)
            lk.setStyleSheet("color:rgba(255,255,255,0.60); font-size:12px; background:transparent;")
            lk.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            if url:
                lv = QLabel(f'<a href="{url}" style="color:#9cdcfe; text-decoration:none;">{val_t}</a>')
                lv.setOpenExternalLinks(True)
                lv.setStyleSheet("background:transparent;")
            else:
                lv = QLabel(val_t)
                lv.setStyleSheet("color:#d4d4d4; font-size:12px; background:transparent;")
            lv.setWordWrap(True)
            row.addWidget(lk); row.addWidget(lv, 1)
            grid.addLayout(row)
        c_lay.addLayout(grid)
        c_lay.addStretch()

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)

        bb.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.12); color: #ffffff;"
            " border: 1px solid rgba(255,255,255,0.25); border-radius:3px; padding:4px 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.22); }"
        )
        c_lay.addWidget(bb, 0, Qt.AlignmentFlag.AlignRight)

        lay.addWidget(container)

    def _placeholder(self, top):
        ph = QLabel("S")
        ph.setStyleSheet(
            "font-size:48px; font-weight:bold; color:#007acc;"
            "background:rgba(0,0,0,0.3); border-radius:8px;"
        )
        ph.setFixedSize(80, 80)
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(ph)

class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Keyboard shortcuts"))
        self.resize(540, 560)
        self.setStyleSheet(f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG};")

        SHORTCUTS = [
            (tr("File"), [
                ("Ctrl+N",          tr("New")),
                ("Ctrl+O",          tr("Open…")),
                ("Ctrl+S",          tr("Save")),
                ("Ctrl+Shift+S",    tr("Save as…")),
                ("Ctrl+W",          tr("Close tab")),
                ("Ctrl+Q",          tr("Quit")),
            ]),
            (tr("Edit"), [
                ("Ctrl+Z / Ctrl+Y", tr("Undo") + " / " + tr("Redo")),
                ("Ctrl+D",          tr("Duplicate line")),
                ("Ctrl+/",          tr("Toggle comment")),
                ("Alt+↑ / Alt+↓",   tr("Move line up") + " / " + tr("Move line down")),
                ("Ctrl+L",          tr("Select all")),
                ("Tab / Shift+Tab", tr("Indent/Dedent")),
            ]),
            (tr("Find / Replace"), [
                ("Ctrl+F",          tr("Find / Replace")),
                ("Ctrl+Shift+F",    tr("Search in files…")),
                ("Ctrl+P",          tr("Command palette")),
                ("Ctrl+G",          tr("Go to line…")),
                ("Ctrl+Shift+M",    tr("Problems panel")),
            ]),
            (tr("View"), [
                ("Ctrl+B",          tr("File tree")),
                ("Ctrl+`",          tr("Terminal / Scratch Pad")),
                ("Ctrl+\\",         tr("Split editor")),
                ("Ctrl+Shift+\\",   tr("Close split")),
                ("Alt+Z",           tr("Word wrap")),
                ("Ctrl+Tab",        tr("Next tab")),
                ("Ctrl+Shift+Tab",  tr("Previous tab")),
                ("Ctrl+1…5",        tr("Tab N")),
                ("Ctrl+= / Ctrl+-", tr("Increase font") + " / " + tr("Decrease font")),
            ]),
            (tr("Run"), [
                ("F5",              tr("Run file")),
            ]),
        ]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(0)

        title = QLabel(f"  {tr('Keyboard shortcuts')}")
        title.setStyleSheet(
            f"background:{VSCode.BG}; color:{VSCode.FG}; font-size:15px;"
            f"font-weight:bold; padding:14px 16px;"
            f"border-bottom:1px solid {VSCode.BORDER};"
        )
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        container = QWidget()
        container.setStyleSheet(f"background:{VSCode.BG_LIGHT};")
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(16, 12, 16, 12)
        vlay.setSpacing(14)

        for section, items in SHORTCUTS:
            sec_lbl = QLabel(section.upper())
            sec_lbl.setStyleSheet(
                f"color:{VSCode.BLUE_ACCENT}; font-size:11px; font-weight:bold;"
                f"letter-spacing:1px; padding:4px 0 2px;"
            )
            vlay.addWidget(sec_lbl)
            line = QWidget(); line.setFixedHeight(1)
            line.setStyleSheet(f"background:{VSCode.BORDER};")
            vlay.addWidget(line)
            for keys, desc in items:
                row = QHBoxLayout(); row.setContentsMargins(0, 3, 0, 3)
                kl = QLabel(keys)
                kl.setStyleSheet(
                    f"color:{VSCode.CYAN}; background:{VSCode.BG};"
                    f"border:1px solid {VSCode.BORDER}; border-radius:3px;"
                    f"padding:1px 6px; font-size:12px;"
                )
                kl.setFixedWidth(190)
                kl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                dl = QLabel(desc)
                dl.setStyleSheet(
                    f"color:{VSCode.FG}; font-size:12px; background:transparent;"
                )
                row.addWidget(kl); row.addWidget(dl, 1)
                vlay.addLayout(row)

        vlay.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        bb.setContentsMargins(12, 0, 12, 0)
        outer.addWidget(bb, alignment=Qt.AlignmentFlag.AlignRight)

class SoniaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        load_language()
        load_theme()

        _disable_native_menu = _needs_embedded_menubar()
        if _disable_native_menu:
            try:
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.setAttribute(
                    Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True
                )
            except Exception:
                pass

        self.setWindowTitle("Suri Studio")
        self.resize(1400, 800)
        self._tab_counter = 0
        self._repo_path:  str | None = None

        self.setAcceptDrops(True)
        self._set_window_icon()
        self._build_menu()
        self._build_central()
        self._build_toolbar()
        self._build_statusbar()

        try:
            self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        except Exception:
            pass

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self._autosave = AutosaveManager(self, parent=self)

        self._palette = CommandPalette(self)
        self._palette.open_file.connect(self.open_file)
        self._register_palette_commands()

        restore_window(self)
        sizes = self.main_splitter.sizes()
        if sizes:
            needs_fix = False
            if len(sizes) >= 1 and sizes[0] < 160:
                sizes[0] = 220; needs_fix = True
            if len(sizes) >= 3 and sizes[2] < 200:
                sizes[2] = 360; needs_fix = True
            if needs_fix:
                self.main_splitter.setSizes(sizes)
        if self._right_panel_visible:
            self.right_panel.show()
        else:
            self.right_panel.hide()
        font_size = load_font_size()

        saved_folder = load_folder()
        if saved_folder and Path(saved_folder).exists():
            self._repo_path = saved_folder
            self.fs_model.setRootPath(saved_folder)
            self.tree_view.setRootIndex(self.fs_model.index(saved_folder))
            self._palette.set_folder(saved_folder)
            self.bottom_panel.search_panel.set_folder(saved_folder)

        session_files, session_idx = load_session()
        if session_files:
            for path in session_files:
                self._open_file_silent(path)
            self.tab_widget.setCurrentIndex(
                min(session_idx, self.tab_widget.count() - 1)
            )
        else:
            self.new_file()

        if font_size != 13:
            self._apply_font_size_all(font_size)

        self._refresh_recent_menu()

    def _set_window_icon(self) -> None:
        logo = _assets_dir() / "logo.svg"
        if not logo.exists():
            return
        try:
            from PySide6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(str(logo))
            if not renderer.isValid():
                return
            icon = QIcon()
            for size in [16, 32, 48, 64, 128, 256]:
                pix = QPixmap(size, size)
                pix.fill(Qt.GlobalColor.transparent)
                p = QPainter(pix)
                renderer.render(p)
                p.end()
                icon.addPixmap(pix)
            self.setWindowIcon(icon)
        except Exception:
            pass

    def _si(self, px):
        return self.style().standardIcon(px)

    def _build_menu(self):
        mb = self.menuBar()
        sp = QStyle.StandardPixmap

        m = mb.addMenu(tr("File"))
        self._act(m, tr("New"),          "Ctrl+N",       self.new_file)
        self._act(m, tr("Open…"),        "Ctrl+O",       self.open_file)
        self._act(m, tr("Save"),         "Ctrl+S",       self.save_current)
        self._act(m, tr("Save as…"),     "Ctrl+Shift+S", self.save_current_as)
        m.addSeparator()
        self._menu_recent = m.addMenu(tr("Open recent"))
        m.addSeparator()
        self._act(m, tr("Close tab"),    "Ctrl+W",       self.close_current_tab)
        m.addSeparator()
        self._act(m, tr("Quit"),         "Ctrl+Q",       self.close)

        m = mb.addMenu(tr("Edit"))
        self._act(m, tr("Undo"),         "Ctrl+Z",
                  lambda: self._cur_editor() and self._cur_editor().undo())
        self._act(m, tr("Redo"),         "Ctrl+Y",
                  lambda: self._cur_editor() and self._cur_editor().redo())
        m.addSeparator()
        self._act(m, tr("Cut"),          "Ctrl+X",
                  lambda: self._cur_editor() and self._cur_editor().cut())
        self._act(m, tr("Copy"),         "Ctrl+C",
                  lambda: self._cur_editor() and self._cur_editor().copy())
        self._act(m, tr("Paste"),        "Ctrl+V",
                  lambda: self._cur_editor() and self._cur_editor().paste())
        self._act(m, tr("Select all"),   "Ctrl+A",
                  lambda: self._cur_editor() and self._cur_editor().selectAll())
        m.addSeparator()
        self._act(m, tr("Duplicate line"), "Ctrl+D",
                  lambda: self._cur_editor() and self._cur_editor().duplicate_line())
        self._act(m, tr("Toggle comment"), "Ctrl+/",
                  lambda: self._cur_editor() and self._cur_editor().toggle_comment())
        self._act(m, tr("Remove all comments"), None,
                  lambda: self._cur_editor() and self._cur_editor().remove_all_comments())
        self._act(m, tr("Move line up"),   "Alt+Up",
                  lambda: self._cur_editor() and self._cur_editor().move_line_up())
        self._act(m, tr("Move line down"), "Alt+Down",
                  lambda: self._cur_editor() and self._cur_editor().move_line_down())
        m.addSeparator()
        self._act(m, tr("Find / Replace"),  "Ctrl+F",       self.toggle_find)
        self._act(m, tr("Search in files…"),"Ctrl+Shift+F", self._search_in_files)
        self._act(m, tr("Go to line…"),     "Ctrl+G",       self._go_to_line_cur)
        self._act(m, tr("Command palette"), "Ctrl+P",       self._open_palette)

        m = mb.addMenu(tr("View"))
        self._act(m, tr("File tree"),           "Ctrl+B",       self.toggle_file_tree)
        self._act(m, tr("Terminal / Scratch Pad"),"Ctrl+`",     self.toggle_right_panel)
        self._act(m, tr("Git"),                 "Ctrl+Shift+G", self.toggle_git_panel)
        self._act(m, "Símbolos",               "Ctrl+Shift+O", self.toggle_symbols_panel)
        self._act(m, tr("Problems panel"),      "Ctrl+Shift+M", self._toggle_bottom_problems)
        m.addSeparator()
        self._act(m, tr("Increase font"),  "Ctrl+=",         self._font_size_up)
        self._act(m, tr("Decrease font"),  "Ctrl+-",         self._font_size_down)
        self._act(m, tr("Default font"),   "Ctrl+0",         self._font_size_reset)
        m.addSeparator()
        self._act_wrap = QAction(tr("Word wrap"), self)
        self._act_wrap.setShortcut(QKeySequence("Alt+Z"))
        self._act_wrap.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._act_wrap.setCheckable(True)
        self._act_wrap.setChecked(False)
        self._act_wrap.triggered.connect(self._toggle_word_wrap)
        m.addAction(self._act_wrap)
        m.addSeparator()
        self._act(m, tr("Split editor"),   "Ctrl+\\",        self._split_editor)
        self._act(m, tr("Close split"),    "Ctrl+Shift+\\",  self._close_split)
        m.addSeparator()
        self._act(m, tr("Next tab"),       "Ctrl+Tab",       self._next_tab)
        self._act(m, tr("Previous tab"),   "Ctrl+Shift+Tab", self._prev_tab)
        for i in range(1, 6):
            self._act(m, tr("Tab N").format(n=i), f"Ctrl+{i}", lambda _, n=i-1: self._go_tab(n))

        m = mb.addMenu(tr("Run"))
        self._act(m, tr("Run file"),          "F5",         self._run_current)
        self._act(m, tr("Build only"),         "F6",         self._build_only)
        m.addSeparator()
        self._act(m, tr("Toggle bookmark"),    "F7",         self._toggle_bookmark)
        self._act(m, tr("Next bookmark"),      "Ctrl+F7",    self._next_bookmark)
        self._act(m, tr("Prev bookmark"),      "Shift+F7",   self._prev_bookmark)
        m.addSeparator()
        self._act(m, tr("Go to definition"),   "F12",        self._goto_definition)
        self._act(m, tr("Navigate back"),      "Alt+Left",   self._navigate_back)
        self._act(m, tr("Navigate forward"),   "Alt+Right",  self._navigate_forward)

        m = mb.addMenu(tr("Help"))
        self._act(m, tr("Keyboard shortcuts"), "Ctrl+?", self._shortcuts)
        m.addSeparator()

        self._act(m, tr("Custom snippets"), "Ctrl+Shift+P", self._open_snippets)
        m.addSeparator()

        theme_menu = m.addMenu(tr("Color theme"))
        cur_theme  = get_theme()
        for code, name in THEMES.items():
            a = QAction(name, self)
            a.setData(code)
            a.setCheckable(True)
            a.setChecked(code == cur_theme)
            a.triggered.connect(self._change_theme)
            theme_menu.addAction(a)

        lang_menu = m.addMenu(tr("Language"))
        cur_lang  = get_language()
        for code, name in LANGUAGES.items():
            a = QAction(name, self)
            a.setData(code)
            a.setCheckable(True)
            a.setChecked(code == cur_lang)
            a.triggered.connect(self._change_language)
            lang_menu.addAction(a)
        m.addSeparator()
        self._act(m, tr("About Suri Studio"), None, self._about)

    def _act(self, menu, label: str, shortcut, slot):
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        if slot:
            a.triggered.connect(slot)
        menu.addAction(a)
        return a

    def _build_toolbar(self):
        tb = self.addToolBar("Principal")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))
        tb.setStyleSheet(
            f"QToolBar {{ background:{VSCode.BG_LIGHT}; border:none;"
            f" border-bottom:1px solid {VSCode.BORDER}; spacing:2px; padding:2px 4px; }}"
            f"QToolButton {{ background:transparent; border:none; border-radius:3px;"
            f" padding:3px 5px; color:{VSCode.FG}; }}"
            f"QToolButton:hover {{ background:{VSCode.BG_LIGHTER}; }}"
            f"QToolButton:pressed {{ background:{VSCode.BLUE_ACCENT}; }}"
        )
        sp = QStyle.StandardPixmap
        for label, px, slot in [
            (tr("New"),              sp.SP_FileIcon,               self.new_file),
            (tr("Open…"),            sp.SP_DirOpenIcon,            self.open_file),
            (tr("Save"),             sp.SP_DialogSaveButton,       self.save_current),
            (None, None, None),
            (tr("Run file"),         sp.SP_MediaPlay,              self._run_current),
            (None, None, None),
            (tr("Find / Replace"),   sp.SP_FileDialogContentsView, self.toggle_find),
        ]:
            if label is None:
                tb.addSeparator()
            else:
                a = QAction(self._si(px), label, self)
                a.triggered.connect(slot)
                tb.addAction(a)

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        h_area   = QWidget()
        main_lay = QHBoxLayout(h_area)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.icon_bar = QWidget()
        self.icon_bar.setFixedWidth(40)
        self.icon_bar.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-right:1px solid {VSCode.BORDER};"
        )
        icon_lay = QVBoxLayout(self.icon_bar)
        icon_lay.setContentsMargins(0, 8, 0, 8)
        icon_lay.setSpacing(2)
        sp = QStyle.StandardPixmap

        self.btn_tree     = self._icon_btn(self._si(sp.SP_DirIcon),
                                           f"{tr('File tree')} (Ctrl+B)",
                                           self.toggle_file_tree)
        self.btn_rp       = self._icon_btn(self._si(sp.SP_ComputerIcon),
                                           f"{tr('Terminal / Scratch Pad')} (Ctrl+`)",
                                           self.toggle_right_panel)
        self.btn_problems = self._icon_btn(self._si(sp.SP_MessageBoxWarning),
                                           f"{tr('Problems panel')} (Ctrl+Shift+M)",
                                           self._toggle_bottom_problems)
        self.btn_git      = self._icon_btn(self._si(sp.SP_DriveNetIcon),
                                           f"{tr('Git')} (Ctrl+Shift+G)",
                                           self.toggle_git_panel)
        self.btn_symbols  = self._icon_btn(self._si(sp.SP_FileDialogListView),
                                           "Símbolos (Ctrl+Shift+O)",
                                           self.toggle_symbols_panel)
        self.btn_problems.setChecked(False)
        self.btn_git.setChecked(False)
        self.btn_symbols.setChecked(False)

        icon_lay.addWidget(self.btn_tree)
        icon_lay.addWidget(self.btn_rp)
        icon_lay.addWidget(self.btn_problems)
        icon_lay.addWidget(self.btn_git)
        icon_lay.addWidget(self.btn_symbols)
        icon_lay.addStretch()
        main_lay.addWidget(self.icon_bar)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_lay.addWidget(self.main_splitter, 1)

        self._left_splitter = QSplitter(Qt.Orientation.Vertical)
        self._left_splitter.setHandleWidth(1)
        self._left_splitter.setMinimumWidth(180)
        self._left_splitter.setMaximumWidth(340)

        self.file_tree_panel = QWidget()
        tree_lay = QVBoxLayout(self.file_tree_panel)
        tree_lay.setContentsMargins(0, 0, 0, 0)
        tree_lay.setSpacing(0)

        tree_hdr = QLabel(tr("Explorer").upper())
        tree_hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; color:{VSCode.FG_DIM}; font-size:11px;"
            f"font-weight:bold; letter-spacing:1px; padding:6px 10px;"
            f"border-bottom:1px solid {VSCode.BORDER};"
        )

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(str(Path.home()))

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(str(Path.home())))
        self.tree_view.setHeaderHidden(True)
        for col in (1, 2, 3):
            self.tree_view.hideColumn(col)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(14)
        self.tree_view.doubleClicked.connect(self._tree_open_file)
        self.tree_view.clicked.connect(self._tree_auto_repo)

        btn_folder = QPushButton()
        btn_folder.setIcon(self._si(QStyle.StandardPixmap.SP_DirOpenIcon))
        btn_folder.setText(f"  {tr('Open folder…')}")
        btn_folder.clicked.connect(self._open_folder)
        btn_folder.setStyleSheet(
            f"margin:4px; text-align:left; border:none;"
            f"background:transparent; color:{VSCode.FG_DIM};"
        )
        tree_lay.addWidget(tree_hdr)
        tree_lay.addWidget(btn_folder)
        tree_lay.addWidget(self.tree_view, 1)

        self.git_panel     = GitPanel()
        self.symbols_panel = SymbolsPanel()
        self.symbols_panel.goto_line.connect(self._goto_symbol_line)
        self._git_panel_visible     = False
        self._symbols_panel_visible = False

        self._left_splitter.addWidget(self.file_tree_panel)
        self._left_splitter.addWidget(self.symbols_panel)
        self._left_splitter.addWidget(self.git_panel)
        self.git_panel.hide()
        self.symbols_panel.hide()
        self.main_splitter.addWidget(self._left_splitter)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.main_splitter.addWidget(self.tab_widget)

        self.right_panel = RightPanel()
        self.right_panel.setMinimumWidth(260)
        self.right_panel.setMaximumWidth(640)
        self.main_splitter.addWidget(self.right_panel)

        self.main_splitter.setSizes([220, 800, 360])
        self.main_splitter.setHandleWidth(1)

        self._file_tree_visible   = True
        self._right_panel_visible = True

        outer.addWidget(h_area, 1)

        self.bottom_panel = BottomPanel()
        self.bottom_panel.setVisible(False)
        self.bottom_panel.goto_line.connect(self._goto_problem_line)
        self.bottom_panel.open_result.connect(self._goto_search_result)
        self.bottom_panel.refresh_lint.connect(self._force_relint)
        outer.addWidget(self.bottom_panel)

    def _icon_btn(self, icon, tooltip: str, slot) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setIconSize(QSize(18, 18))
        btn.setObjectName("sidebar_btn")
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setFixedSize(36, 36)
        btn.clicked.connect(slot)
        return btn

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.lbl_file = QLabel(tr("Untitled"))
        self.lbl_lang = QLabel("text")
        self.lbl_pos  = QLabel(f"{tr('Ln')} 1, {tr('Col')} 1")
        self.lbl_enc  = QLabel("UTF-8")
        sb.addWidget(self.lbl_file, 1)
        for lbl in [self.lbl_lang, self.lbl_pos, self.lbl_enc]:
            sb.addPermanentWidget(lbl)

    def new_file(self):
        dlg = NewFileDialog(suggested_lang='text', parent=self)
        if dlg.exec() == NewFileDialog.DialogCode.Rejected:
            return
        lang = dlg.chosen_lang()
        tab  = self._create_tab(initial_lang=lang)
        template = get_template(lang)
        if template and tab:
            tab.editor.setPlainText(template)
            tab.editor.document().setModified(False)
        self._offer_linter_install(lang)

    def _offer_linter_install(self, lang: str) -> None:

        import shutil
        linter_info = {
            'python':     ('ruff',       'pip install ruff'),
            'javascript': ('eslint',     'npm install -g eslint'),
            'typescript': ('eslint',     'npm install -g eslint'),
            'bash':       ('shellcheck', 'sudo apt install shellcheck  /  sudo dnf install ShellCheck'),
            'ruby':       ('rubocop',    'gem install rubocop'),
            'css':        ('stylelint',  'npm install -g stylelint'),
            'scss':       ('stylelint',  'npm install -g stylelint'),
        }
        if lang not in linter_info:
            return
        tool, install_cmd = linter_info[lang]
        if shutil.which(tool):
            return
        r = QMessageBox.question(
            self,
            tr("linter_missing_title").format(lang=lang),
            tr("linter_missing_msg").format(lang=lang, tool=tool, cmd=install_cmd),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            if not self._right_panel_visible:
                self.toggle_right_panel()
            self.right_panel.terminal.set_cwd(str(Path.home()))
            self.right_panel.terminal._append(
                tr("Install linter hint").format(tool=tool), "#e5c07b"
            )
            self.right_panel.terminal._append(
                f"  {install_cmd}", "#98c379"
            )

    def _create_tab(self, filepath=None, initial_lang=None):
        self._tab_counter += 1
        tab = SplitEditorContainer(filepath=filepath, initial_lang=initial_lang)
        tab.editor.cursorPositionChanged.connect(self._update_cursor_pos)
        tab.modified_changed.connect(lambda _: self._on_tab_modified(tab))

        if tab.primary._lint_mgr is not None:
            tab.primary._lint_mgr.errors_updated.connect(
                lambda errs, t=tab: self._on_lint_results(t, errs)
            )
        name = Path(filepath).name if filepath else f"{tr('Untitled')} {self._tab_counter}"
        idx  = self.tab_widget.addTab(tab, name)
        self.tab_widget.setCurrentIndex(idx)
        if filepath:
            self._update_statusbar(tab)
        tab.editor.setFocus()
        return tab

    def open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Open…"))
        if not path:
            return
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, SplitEditorContainer) and tab.filepath == path:
                self.tab_widget.setCurrentIndex(i); return
        self._create_tab(filepath=path)
        add_recent(path)
        self._refresh_recent_menu()

        self._update_repo(str(Path(path).parent))
        if not self._palette._folder:
            self._palette.set_folder(str(Path(path).parent))

    def _open_file_silent(self, path: str):
        if not Path(path).exists(): return
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, SplitEditorContainer) and tab.filepath == path:
                return
        self._create_tab(filepath=path)

    def save_current(self):
        tab = self._cur_tab()
        if tab:
            tab.save(); self._refresh_tab_title(tab); self._update_statusbar(tab)

    def save_current_as(self):
        tab = self._cur_tab()
        if tab:
            tab.save_as(); self._refresh_tab_title(tab); self._update_statusbar(tab)
            if tab.filepath:
                add_recent(tab.filepath); self._refresh_recent_menu()

    def close_tab(self, index: int):
        tab = self.tab_widget.widget(index)
        if isinstance(tab, SplitEditorContainer):

            tab.primary.save_cursor()
            if tab.is_modified():
                name = Path(tab.filepath).name if tab.filepath else tr("Untitled")
                r = QMessageBox.question(
                    self, tr("Unsaved changes"),
                    f"{tr('Save changes in')} «{name}»?",
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel,
                )
                if r == QMessageBox.StandardButton.Save:
                    if not tab.save(): return
                elif r == QMessageBox.StandardButton.Cancel:
                    return
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.new_file()

    def close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0: self.close_tab(idx)

    def _refresh_recent_menu(self):
        self._menu_recent.clear()
        recent = get_recent()
        if not recent:
            a = QAction(tr("No recent files"), self); a.setEnabled(False)
            self._menu_recent.addAction(a); return
        for path in recent:
            a = QAction(f"{Path(path).name}  —  {path}", self)
            a.setData(path); a.triggered.connect(self._open_recent)
            self._menu_recent.addAction(a)
        self._menu_recent.addSeparator()
        clr = QAction(tr("Clear recent"), self)
        clr.triggered.connect(lambda: (clear_recent(), self._refresh_recent_menu()))
        self._menu_recent.addAction(clr)

    def _open_recent(self):
        a = self.sender()
        if a: self.open_file(a.data())

    def _next_tab(self):
        n = self.tab_widget.count()
        if n > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % n)

    def _prev_tab(self):
        n = self.tab_widget.count()
        if n > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % n)

    def _go_tab(self, idx: int):
        if idx < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(idx)

    def _font_size_up(self):   self._change_font_size(+1)
    def _font_size_down(self): self._change_font_size(-1)
    def _font_size_reset(self): self._apply_font_size_all(13)

    def _change_font_size(self, delta: int):
        e = self._cur_editor()
        if e:
            new_size = max(8, min(32, e.font().pointSize() + delta))
            self._apply_font_size_all(new_size)

    def _set_editor_font_size(self, size: int):
        self._apply_font_size_all(size)

    def _apply_font_size_all(self, size: int):

        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if isinstance(tab, SplitEditorContainer):
                for ed in [tab.primary.editor, *(
                    [tab.secondary.editor] if tab.secondary else []
                )]:
                    f = ed.font()
                    f.setPointSize(size)
                    ed.setFont(f)
                    ed.setTabStopDistance(
                        QFontMetricsF(f).horizontalAdvance(' ') * 4
                    )
        save_font_size(size)

    def _tree_open_file(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path):
            self.open_file(path)
            self.right_panel.terminal_widget.set_cwd(str(Path(path).parent))

    def _tree_auto_repo(self, index):

        path = self.fs_model.filePath(index)
        if not path:
            return

        folder = path if os.path.isdir(path) else str(Path(path).parent)
        self._update_repo(folder)

    def _update_repo(self, folder: str) -> None:

        if folder == self._repo_path:
            return
        self._repo_path = folder
        if self._git_panel_visible:
            self.git_panel.set_repo(folder)

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Open folder…"))
        if folder:
            self._repo_path = folder
            self.fs_model.setRootPath(folder)
            self.tree_view.setRootIndex(self.fs_model.index(folder))
            self._palette.set_folder(folder)
            self.bottom_panel.search_panel.set_folder(folder)
            if self._git_panel_visible:
                self.git_panel.set_repo(folder)
            save_folder(folder)

    def toggle_file_tree(self):
        self._file_tree_visible = not self._file_tree_visible
        if self._file_tree_visible:
            self.file_tree_panel.show()
        else:
            self.file_tree_panel.hide()
        self.btn_tree.setChecked(self._file_tree_visible)

    def toggle_right_panel(self):
        self._right_panel_visible = not self._right_panel_visible
        if self._right_panel_visible:
            self.right_panel.show()
        else:
            self.right_panel.hide()
        self.btn_rp.setChecked(self._right_panel_visible)

    def toggle_git_panel(self):
        self._git_panel_visible = not self._git_panel_visible
        if self._git_panel_visible:
            self.git_panel.show()
            if self._repo_path:
                self.git_panel.set_repo(self._repo_path)
        else:
            self.git_panel.hide()
        self.btn_git.setChecked(self._git_panel_visible)

    def toggle_find(self):
        tab = self._cur_tab()
        if tab: tab.find_bar.toggle()

    def _go_to_line_cur(self):
        tab = self._cur_tab()
        if tab: tab._go_to_line()

    def _toggle_word_wrap(self):
        e = self._cur_editor()
        if e: self._act_wrap.setChecked(e.toggle_word_wrap())

    def _split_editor(self):
        tab = self._cur_tab()
        if tab and not tab.has_split(): tab.split()

    def _close_split(self):
        tab = self._cur_tab()
        if tab and tab.has_split(): tab.close_split()

    def _toggle_bottom_problems(self):
        if self.bottom_panel.isVisible() and self.bottom_panel._active_tab == 0:
            self.bottom_panel.setVisible(False)
            self.btn_problems.setChecked(False)
        else:
            self.bottom_panel.show_problems()
            self.btn_problems.setChecked(True)

    def _search_in_files(self):
        folder = self.fs_model.rootPath() or str(Path.home())
        self.bottom_panel.search_panel.set_folder(folder)
        self.bottom_panel.show_search()

    def _goto_problem_line(self, filepath: str, line_0: int):
        self.open_file(filepath)
        tab = self._cur_tab()
        if tab:
            block  = tab.editor.document().findBlockByNumber(line_0)
            cursor = tab.editor.textCursor()
            cursor.setPosition(block.position())
            tab.editor.setTextCursor(cursor)
            tab.editor.centerCursor()
            tab.editor.setFocus()

    def _goto_search_result(self, filepath: str, line_1: int):
        self._goto_problem_line(filepath, line_1 - 1)

    def _open_palette(self):
        folder = self.fs_model.rootPath() or str(Path.home())
        self._palette.set_folder(folder)
        self._palette.open()

    def _register_palette_commands(self):
        for cmd_id, label, cb in [
            ("new_file",     tr("cmd_new_file"),    self.new_file),
            ("open_file",    tr("cmd_open_file"),   self.open_file),
            ("save",         tr("cmd_save"),        self.save_current),
            ("save_as",      tr("cmd_save_as"),     self.save_current_as),
            ("find",         tr("cmd_find"),        self.toggle_find),
            ("search_files", tr("cmd_search_files"),self._search_in_files),
            ("goto_line",    tr("cmd_goto_line"),   self._go_to_line_cur),
            ("split",        tr("cmd_split"),       self._split_editor),
            ("close_split",  tr("cmd_close_split"), self._close_split),
            ("wrap",         tr("cmd_wrap"),        self._toggle_word_wrap),
            ("run",          tr("cmd_run"),         self._run_current),
            ("problems",     tr("cmd_problems"),    self._toggle_bottom_problems),
            ("open_folder",  tr("cmd_open_folder"), self._open_folder),
            ("remove_comments", tr("cmd_remove_comments"),
             lambda: self._cur_editor() and self._cur_editor().remove_all_comments()),
            ("git",          tr("cmd_git"),          self.toggle_git_panel),
            ("language",     tr("cmd_language"),    self._shortcuts),
        ]:
            self._palette.register_command(cmd_id, label, cb)

    def _change_language(self):
        a = self.sender()
        if a:
            set_language(a.data())
            QMessageBox.information(
                self, tr("Restart required"), tr("Restart required msg"),
                QMessageBox.StandardButton.Ok,
            )

    def _force_relint(self):
        tab = self._cur_tab()
        if tab and tab.primary._lint_mgr is not None:
            tab.primary._lint_mgr._run_lint()

    def _on_lint_results(self, tab, errors: list):
        if self._cur_tab() is tab:
            self.bottom_panel.problems_panel.update_problems(
                tab.filepath or "", errors
            )

    def _run_current(self):
        tab = self._cur_tab()
        if not tab: return
        if tab.is_modified():
            r = QMessageBox.question(
                self, tr("Save before run"), tr("Save before run msg"),
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Cancel: return
            if r == QMessageBox.StandardButton.Yes:
                if not tab.save(): return
        if not self._right_panel_visible:
            self.toggle_right_panel()
        run_file(tab.filepath, self.right_panel.terminal_widget, self)

    def _cur_tab(self):
        w = self.tab_widget.currentWidget()
        return w if isinstance(w, SplitEditorContainer) else None

    def _cur_editor(self):
        tab = self._cur_tab()
        return tab.editor if tab else None

    def _refresh_tab_title(self, tab):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) is tab:
                title = tab.get_title()

                if tab.is_modified():
                    title = f"• {title}"
                self.tab_widget.setTabText(i, title)
                break

    def _on_tab_modified(self, tab):
        self._refresh_tab_title(tab)

    def _on_tab_changed(self, index: int):
        for i in range(self.tab_widget.count()):
            if i != index:
                w = self.tab_widget.widget(i)
                if isinstance(w, SplitEditorContainer):
                    w.primary.save_cursor()
        tab = self.tab_widget.widget(index)
        if isinstance(tab, SplitEditorContainer):
            self._update_statusbar(tab)
            tab.editor.cursorPositionChanged.connect(self._update_cursor_pos)
            self._act_wrap.setChecked(tab.editor._word_wrap)
            errs = tab.primary._lint_mgr.get_errors() if tab.primary._lint_mgr else []
            self.bottom_panel.problems_panel.update_problems(
                tab.filepath or "", errs
            )
            if self._symbols_panel_visible:
                lang = tab.editor._current_lang()
                if tab.filepath:
                    self.symbols_panel.set_file(tab.filepath, lang)
                else:
                    self.symbols_panel.update_content(tab.editor.toPlainText(), lang)

    def _update_statusbar(self, tab):
        name = Path(tab.filepath).name if tab.filepath else tr("Untitled")
        self.lbl_file.setText(name)
        lang = tab.editor.highlighter.language if tab.editor.highlighter else "text"
        self.lbl_lang.setText(lang)

    def _update_cursor_pos(self):
        e = self._cur_editor()
        if e:
            c = e.textCursor()
            self.lbl_pos.setText(
                f"{tr('Ln')} {c.blockNumber()+1}, {tr('Col')} {c.columnNumber()+1}"
            )

    def _shortcuts(self): ShortcutsDialog(self).exec()
    def _about(self):     AboutDialog(self).exec()

    def _change_theme(self):
        a = self.sender()
        if a:
            set_theme(a.data())
            from PySide6.QtWidgets import QApplication
            QApplication.instance().setStyleSheet(build_qss())
            QMessageBox.information(
                self, tr("Theme changed"),
                tr("theme_applied_msg").format(theme=THEMES.get(a.data(), a.data())),
                QMessageBox.StandardButton.Ok,
            )

    def _open_snippets(self):
        from core.user_snippets import SnippetEditorDialog
        dlg = SnippetEditorDialog(self)
        dlg.exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():

            for url in event.mimeData().urls():
                if url.isLocalFile():
                    from pathlib import Path as _P
                    if _P(url.toLocalFile()).is_file():
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                from pathlib import Path as _P
                if _P(path).is_file():
                    self.open_file(path)
        event.acceptProposedAction()

    def toggle_symbols_panel(self):
        self._symbols_panel_visible = not self._symbols_panel_visible
        if self._symbols_panel_visible:
            self.symbols_panel.show()
            tab = self._cur_tab()
            if tab and tab.filepath:
                lang = tab.editor._current_lang()
                self.symbols_panel.set_file(tab.filepath, lang)
            elif tab:
                code = tab.editor.toPlainText()
                lang = tab.editor._current_lang()
                self.symbols_panel.update_content(code, lang)
        else:
            self.symbols_panel.hide()
        self.btn_symbols.setChecked(self._symbols_panel_visible)

    def _goto_symbol_line(self, line_1based: int) -> None:
        tab = self._cur_tab()
        if tab:
            block  = tab.editor.document().findBlockByNumber(line_1based - 1)
            cursor = tab.editor.textCursor()
            cursor.setPosition(block.position())
            tab.editor.setTextCursor(cursor)
            tab.editor.centerCursor()
            tab.editor.setFocus()

    def _build_only(self):
        tab = self._cur_tab()
        if not tab:
            return
        if tab.is_modified():
            if not tab.save():
                return
        if not self._right_panel_visible:
            self.toggle_right_panel()
        build_only(tab.filepath, self.right_panel.terminal_widget, self)

    def _toggle_bookmark(self):
        e = self._cur_editor()
        if e:
            e.toggle_bookmark()

    def _next_bookmark(self):
        e = self._cur_editor()
        if e:
            e.next_bookmark()

    def _prev_bookmark(self):
        e = self._cur_editor()
        if e:
            e.prev_bookmark()

    def _goto_definition(self):
        e = self._cur_editor()
        if e:
            e.goto_definition()

    def _navigate_back(self):
        e = self._cur_editor()
        if e:
            e.navigate_back()

    def _navigate_forward(self):
        e = self._cur_editor()
        if e:
            e.navigate_forward()

    def closeEvent(self, event):

        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if not (isinstance(tab, SplitEditorContainer) and tab.is_modified()):
                continue
            name = Path(tab.filepath).name if tab.filepath else tr("Untitled")
            r = QMessageBox.question(
                self,
                tr("Unsaved changes"),
                f"{tr('Save changes in')} «{name}»?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if r == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if r == QMessageBox.StandardButton.Save:
                if not tab.save():

                    event.ignore()
                    return

        save_window(self)
        save_session(self)
        save_folder(self.fs_model.rootPath())
        e = self._cur_editor()
        if e: save_font_size(e.font().pointSize())

        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, SplitEditorContainer):
                w.primary.save_cursor()
        self.right_panel.save_scratch()
        self._autosave.stop()
        from core.autosave import delete_all_snapshots
        delete_all_snapshots()
        event.accept()
