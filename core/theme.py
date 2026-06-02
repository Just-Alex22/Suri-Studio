# core/theme.py — Sistema de temas para Sonia
#
# VSCode es una clase cuyos atributos de clase se actualizan al cambiar tema.
# El código existente (VSCode.BG, VSCode.FG, etc.) no necesita ningún cambio.

from __future__ import annotations
from PySide6.QtCore import QSettings

APP = "Suri Studio"
ORG = "CuerdOS"

FONT_FAMILY_EDITOR = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace"
FONT_FAMILY        = FONT_FAMILY_EDITOR
FONT_SIZE          = "13px"
FONT_FAMILY_UI     = ""   # se resuelve en build_qss() tras crear QApplication


def _resolve_system_font() -> str:
    import sys
    try:
        from PySide6.QtGui import QFontDatabase
        families = set(QFontDatabase().families())
        if sys.platform == "darwin":
            candidates = [".AppleSystemUIFont", "Helvetica Neue", "Helvetica", "Arial"]
        elif sys.platform == "win32":
            candidates = ["Segoe UI", "Tahoma", "Arial"]
        else:
            candidates = ["Ubuntu", "Noto Sans", "DejaVu Sans", "Liberation Sans", "Arial"]
        for name in candidates:
            if name in families:
                return name
    except Exception:
        pass
    return "Arial"


def get_ui_scale() -> float:
    """
    Devuelve el factor de escala real de la pantalla principal.

    En Wayland con compositors minimalistas (LabWC, sway, river…) el
    scale factor no siempre llega correctamente a Qt porque depende de
    que el compositor implemente wp-fractional-scale-v1.  Leemos
    directamente del QScreen disponible, que es la fuente más fiable.
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                return screen.devicePixelRatio()
    except Exception:
        pass
    return 1.0


def scaled_font_size(base_pt: int = 10) -> int:
    """
    Devuelve el tamaño de fuente de UI escalado al DPI real.
    Compensa el caso en que el compositor Wayland no reportó scale
    pero el DPI lógico sí indica una pantalla HiDPI.
    Siempre devuelve al menos 1 para que QFont no se queje.
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                scale       = screen.devicePixelRatio()
                logical_dpi = screen.logicalDotsPerInch()
                if logical_dpi > 0 and logical_dpi > 120 and scale <= 1.0:
                    return max(1, int(base_pt * logical_dpi / 96))
    except Exception:
        pass
    return max(1, base_pt)

_MONO_CANDIDATES = [
    "Menlo",
    "Consolas",
    "SF Mono",
    "Monaco",
    "Ubuntu Mono",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Cascadia Code",
    "JetBrains Mono",
    "Fira Code",
    "Source Code Pro",
    "Roboto Mono",
    "Noto Mono",
    "Inconsolata",
    "Courier New",
]

def get_best_mono_font(size: int = 13):
    from PySide6.QtGui import QFontDatabase, QFont
    db       = QFontDatabase()
    families = db.families()
    for name in _MONO_CANDIDATES:
        if name in families:
            f = QFont(name, size)
            f.setStyleHint(QFont.StyleHint.Monospace)
            f.setFixedPitch(True)
            return f
    f = QFont()
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setFixedPitch(True)
    f.setPointSize(size)
    return f

THEMES: dict[str, str] = {
    "vscode":     "VS Code Dark+",
    "onedark":    "One Dark",
    "catppuccin": "Catppuccin Mocha",
    "gruvbox":    "Gruvbox Dark",
}

# ─────────────────────────────────────────────────────────────────────────────
#  Paletas completas — todos los atributos que usa el código
# ─────────────────────────────────────────────────────────────────────────────
_PALETTES: dict[str, dict] = {
    "vscode": {
        # Fondos
        "BG":             "#1e1e1e",
        "BG_LIGHT":       "#252526",
        "BG_LIGHTER":     "#2d2d30",
        "BORDER":         "#3c3c3c",
        # Texto
        "FG":             "#d4d4d4",
        "FG_DIM":         "#858585",
        "FG_INACTIVE":    "#6d6d6d",
        "WHITE":          "#ffffff",
        # Acentos
        "BLUE_ACCENT":    "#007acc",
        "BLUE":           "#569cd6",
        "BLUE_LIGHT":     "#9cdcfe",
        # Statusbar
        "STATUSBAR_BG":   "#007acc",
        "STATUSBAR_FG":   "#ffffff",
        # Sintaxis
        "GREEN":          "#6a9955",
        "STRING":         "#ce9178",
        "YELLOW":         "#dcdcaa",
        "CYAN":           "#4ec9b0",
        "PURPLE":         "#c586c0",
        "NUM":            "#b5cea8",
        "KEYWORD2":       "#569cd6",
        "DECORATOR":      "#dcdcaa",
        # Terminal
        "TERMINAL_BG":    "#0c0c0c",
        "TERMINAL_FG":    "#cccccc",
        # Selección
        "SELECTION":      "#094771",
        # Dots de pestañas
        "TAB_DOT_MODIFIED": "#e5c07b",
        "TAB_DOT_SAVED":    "#4ec9b0",
        "TAB_DOT_NEW":      "#858585",
    },
    "onedark": {
        "BG":             "#282c34",
        "BG_LIGHT":       "#2c313c",
        "BG_LIGHTER":     "#323842",
        "BORDER":         "#3e4452",
        "FG":             "#abb2bf",
        "FG_DIM":         "#5c6370",
        "FG_INACTIVE":    "#4b5263",
        "WHITE":          "#ffffff",
        "BLUE_ACCENT":    "#61afef",
        "BLUE":           "#61afef",
        "BLUE_LIGHT":     "#56b6c2",
        "STATUSBAR_BG":   "#21252b",
        "STATUSBAR_FG":   "#9da5b4",
        "GREEN":          "#98c379",
        "STRING":         "#e5c07b",
        "YELLOW":         "#e5c07b",
        "CYAN":           "#56b6c2",
        "PURPLE":         "#c678dd",
        "NUM":            "#d19a66",
        "KEYWORD2":       "#61afef",
        "DECORATOR":      "#e5c07b",
        "TERMINAL_BG":    "#21252b",
        "TERMINAL_FG":    "#abb2bf",
        "SELECTION":      "#3e4452",
        "TAB_DOT_MODIFIED": "#e5c07b",
        "TAB_DOT_SAVED":    "#98c379",
        "TAB_DOT_NEW":      "#5c6370",
    },
    "catppuccin": {
        "BG":             "#1e1e2e",
        "BG_LIGHT":       "#313244",
        "BG_LIGHTER":     "#45475a",
        "BORDER":         "#585b70",
        "FG":             "#cdd6f4",
        "FG_DIM":         "#a6adc8",
        "FG_INACTIVE":    "#6c7086",
        "WHITE":          "#cdd6f4",
        "BLUE_ACCENT":    "#89b4fa",
        "BLUE":           "#89b4fa",
        "BLUE_LIGHT":     "#89dceb",
        "STATUSBAR_BG":   "#181825",
        "STATUSBAR_FG":   "#a6adc8",
        "GREEN":          "#a6e3a1",
        "STRING":         "#a6e3a1",
        "YELLOW":         "#f9e2af",
        "CYAN":           "#94e2d5",
        "PURPLE":         "#cba6f7",
        "NUM":            "#fab387",
        "KEYWORD2":       "#89b4fa",
        "DECORATOR":      "#f9e2af",
        "TERMINAL_BG":    "#11111b",
        "TERMINAL_FG":    "#cdd6f4",
        "SELECTION":      "#45475a",
        "TAB_DOT_MODIFIED": "#f9e2af",
        "TAB_DOT_SAVED":    "#a6e3a1",
        "TAB_DOT_NEW":      "#6c7086",
    },
    "gruvbox": {
        "BG":             "#282828",
        "BG_LIGHT":       "#3c3836",
        "BG_LIGHTER":     "#504945",
        "BORDER":         "#665c54",
        "FG":             "#ebdbb2",
        "FG_DIM":         "#928374",
        "FG_INACTIVE":    "#7c6f64",
        "WHITE":          "#fbf1c7",
        "BLUE_ACCENT":    "#458588",
        "BLUE":           "#83a598",
        "BLUE_LIGHT":     "#8ec07c",
        "STATUSBAR_BG":   "#1d2021",
        "STATUSBAR_FG":   "#a89984",
        "GREEN":          "#b8bb26",
        "STRING":         "#b8bb26",
        "YELLOW":         "#fabd2f",
        "CYAN":           "#8ec07c",
        "PURPLE":         "#d3869b",
        "NUM":            "#d65d0e",
        "KEYWORD2":       "#83a598",
        "DECORATOR":      "#fabd2f",
        "TERMINAL_BG":    "#1d2021",
        "TERMINAL_FG":    "#ebdbb2",
        "SELECTION":      "#504945",
        "TAB_DOT_MODIFIED": "#fabd2f",
        "TAB_DOT_SAVED":    "#8ec07c",
        "TAB_DOT_NEW":      "#928374",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  VSCode — clase simple con atributos de clase actualizables
# ─────────────────────────────────────────────────────────────────────────────
class VSCode:
    """
    Clase de colores del tema activo.
    Uso: VSCode.BG, VSCode.FG, VSCode.BLUE_ACCENT, etc.
    Los atributos se actualizan al llamar a set_theme().
    """
    # Valores iniciales (VSCode Dark+ por defecto)
    BG             = "#1e1e1e"
    BG_LIGHT       = "#252526"
    BG_LIGHTER     = "#2d2d30"
    BORDER         = "#3c3c3c"
    FG             = "#d4d4d4"
    FG_DIM         = "#858585"
    FG_INACTIVE    = "#6d6d6d"
    WHITE          = "#ffffff"
    BLUE_ACCENT    = "#007acc"
    BLUE           = "#569cd6"
    BLUE_LIGHT     = "#9cdcfe"
    STATUSBAR_BG   = "#007acc"
    STATUSBAR_FG   = "#ffffff"
    GREEN          = "#6a9955"
    STRING         = "#ce9178"
    YELLOW         = "#dcdcaa"
    CYAN           = "#4ec9b0"
    PURPLE         = "#c586c0"
    NUM            = "#b5cea8"
    KEYWORD2       = "#569cd6"
    DECORATOR      = "#dcdcaa"
    TERMINAL_BG    = "#0c0c0c"
    TERMINAL_FG    = "#cccccc"
    SELECTION      = "#094771"
    TAB_DOT_MODIFIED = "#e5c07b"
    TAB_DOT_SAVED    = "#4ec9b0"
    TAB_DOT_NEW      = "#858585"


# ─────────────────────────────────────────────────────────────────────────────
#  API pública
# ─────────────────────────────────────────────────────────────────────────────
_current_theme: str = "vscode"


def get_theme() -> str:
    return _current_theme


def set_theme(name: str) -> None:
    """Cambia el tema activo y actualiza todos los atributos de VSCode."""
    global _current_theme
    if name not in _PALETTES:
        return
    _current_theme = name
    palette = _PALETTES[name]
    # Actualizar los atributos de clase de VSCode
    for key, val in palette.items():
        setattr(VSCode, key, val)
    QSettings(ORG, APP).setValue("ui/theme", name)


def load_theme() -> None:
    """Carga el tema guardado en QSettings. Llamar antes de construir la UI."""
    saved = QSettings(ORG, APP).value("ui/theme", "vscode")
    set_theme(saved if saved in _PALETTES else "vscode")


def build_qss() -> str:
    global FONT_FAMILY_UI
    if not FONT_FAMILY_UI:
        FONT_FAMILY_UI = _resolve_system_font()

    # Tamaño de fuente de UI adaptado al DPI real del compositor
    ui_font_pt  = scaled_font_size(10)          # puntos para QFont
    ui_font_css = f"{ui_font_pt}pt"             # en el QSS usamos pt, no px

    bg           = VSCode.BG
    bg_light     = VSCode.BG_LIGHT
    bg_lighter   = VSCode.BG_LIGHTER
    border       = VSCode.BORDER
    fg           = VSCode.FG
    fg_dim       = VSCode.FG_DIM
    white        = VSCode.WHITE
    blue         = VSCode.BLUE_ACCENT
    statusbar_bg = VSCode.STATUSBAR_BG
    statusbar_fg = VSCode.STATUSBAR_FG
    terminal_bg  = VSCode.TERMINAL_BG
    terminal_fg  = VSCode.TERMINAL_FG
    selection    = VSCode.SELECTION

    return f"""
* {{
    font-size: {ui_font_css};
    outline: 0;
}}
QMainWindow, QWidget, QMenuBar, QMenu, QToolBar,
QStatusBar, QDialog, QMessageBox, QLabel, QPushButton,
QCheckBox, QLineEdit, QComboBox, QTabBar, QTreeView,
QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit {{
    font-family: {FONT_FAMILY_UI};
    font-size: {ui_font_css};
}}
QMainWindow, QWidget {{
    background-color: {bg};
    color: {fg};
}}
QMenuBar {{
    background-color: {bg_light};
    color: {fg};
    border-bottom: 1px solid {border};
    padding: 0;
}}
QMenuBar::item {{ padding: 4px 10px; min-height: 20px; }}
QMenuBar::item:selected {{ background-color: {bg_lighter}; }}
QMenu {{
    background-color: {bg_light};
    color: {fg};
    border: 1px solid {border};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 5px 28px 5px 12px;
    min-height: 22px;   /* evita que el texto quede recortado en LabWC/sway */
}}
QMenu::item:selected {{ background-color: {blue}; color: {white}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 3px 0; }}
QToolBar {{
    background-color: {bg_light};
    border-bottom: 1px solid {border};
    spacing: 2px;
    padding: 2px 4px;
}}
QToolBar QToolButton {{
    background: transparent;
    border: none;
    border-radius: 3px;
    padding: 3px 5px;
    color: {fg};
}}
QToolBar QToolButton:hover {{ background: {bg_lighter}; }}
QToolBar QToolButton:pressed {{ background: {blue}; }}
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {border};
}}
QTabBar {{
    background: {bg_light};
}}
QTabBar::tab {{
    background: {bg_light};
    color: {fg_dim};
    border: none;
    padding: 6px 18px 6px 24px;
    border-right: 1px solid {border};
    font-size: {ui_font_css};
}}
QTabBar::tab:selected {{
    background: {bg};
    color: {fg};
    border-top: 1px solid {blue};
}}
QTabBar::tab:hover:!selected {{
    background: {bg_lighter};
    color: {fg};
}}
QPlainTextEdit, QTextEdit {{
    background-color: {bg};
    color: {fg};
    border: none;
    outline: none;
    selection-background-color: {selection};
}}
QTreeView {{
    background-color: {bg_light};
    color: {fg};
    border: none;
    outline: none;
}}
QTreeView::item {{ padding: 2px 0; height: 22px; }}
QTreeView::item:hover {{ background-color: {bg_lighter}; }}
QTreeView::item:selected {{ background-color: {selection}; color: {white}; }}
QHeaderView::section {{
    background-color: {bg_light};
    color: {fg_dim};
    border: none;
    border-bottom: 1px solid {border};
    padding: 3px 6px;
}}
QSplitter::handle {{ background-color: {border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}
QStatusBar {{
    background-color: {statusbar_bg};
    color: {statusbar_fg};
    border: none;
    padding: 0;
    font-size: {ui_font_css};
}}
QStatusBar QLabel {{
    color: {statusbar_fg};
    padding: 0 8px;
    border: none;
    outline: none;
}}
QStatusBar::item {{ border: none; outline: none; }}
QPushButton {{
    background-color: {bg_lighter};
    color: {fg};
    border: 1px solid {border};
    border-radius: 2px;
    padding: 4px 10px;
}}
QPushButton:hover {{ background-color: {bg_lighter}; border-color: {fg_dim}; }}
QPushButton:pressed {{ background-color: {blue}; color: {white}; }}
QLineEdit {{
    background-color: {bg_lighter};
    color: {fg};
    border: 1px solid {border};
    border-radius: 2px;
    padding: 3px 6px;
    selection-background-color: {blue};
}}
QLineEdit:focus {{ border-color: {border}; outline: 0; }}
QCheckBox {{ color: {fg}; spacing: 5px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {fg_dim};
    border-radius: 2px;
    background: {bg_lighter};
}}
QCheckBox::indicator:checked {{ background: {blue}; border-color: {blue}; }}
QScrollBar:vertical {{ background: {bg}; width: 10px; border: none; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 30px; margin: 1px; }}
QScrollBar::handle:vertical:hover {{ background: {fg_dim}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {bg}; height: 10px; border: none; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 30px; margin: 1px; }}
QScrollBar::handle:horizontal:hover {{ background: {fg_dim}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QDialog, QMessageBox {{ background-color: {bg_light}; color: {fg}; }}
QDialogButtonBox QPushButton {{ min-width: 80px; }}
QComboBox {{
    background-color: {bg_lighter};
    color: {fg};
    border: 1px solid {border};
    border-radius: 2px;
    padding: 3px 6px;
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {bg_light};
    color: {fg};
    selection-background-color: {blue};
    border: 1px solid {border};
}}
#terminal_output {{
    background-color: {terminal_bg};
    color: {terminal_fg};
    border: none;
}}
#terminal_input {{
    background-color: {terminal_bg};
    color: {terminal_fg};
    border: none;
    border-top: 1px solid {border};
    padding: 3px 8px;
}}
#scratchpad_editor {{
    background-color: {bg};
    color: {fg};
    border: none;
}}
#sidebar_btn {{
    background-color: transparent;
    color: {fg_dim};
    border: none;
    border-radius: 0;
    padding: 8px 4px;
}}
#sidebar_btn:hover {{ color: {fg}; background-color: {bg_lighter}; }}
#sidebar_btn:checked {{
    color: {fg};
    border-left: 2px solid {blue};
    background-color: {bg_lighter};
}}
QSlider::groove:horizontal {{ background: {border}; height: 3px; }}
QSlider::handle:horizontal {{
    background: {blue};
    width: 12px; height: 12px;
    margin: -5px 0; border-radius: 6px;
}}
QSlider::sub-page:horizontal {{ background: {blue}; }}
"""


VSCODE_QSS = ""
