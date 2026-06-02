# core — tema, resaltado, autocompletado, autosave, settings, translate, snippets
from .theme      import VSCode, FONT_FAMILY, build_qss, load_theme, set_theme, get_theme, THEMES
from .highlighter import SyntaxHighlighter
from .completer  import CompletionPopup
from .autosave   import (
    AutosaveManager, snapshots_exist,
    load_snapshots, delete_all_snapshots,
)
from .settings   import (
    save_window, restore_window, save_session, load_session,
    save_font_size, load_font_size, save_folder, load_folder,
    add_recent, get_recent, clear_recent,
    save_cursor_pos, load_cursor_pos, snippets_path,
)
from .translate  import tr, set_language, get_language, load_language, LANGUAGES
from .user_snippets import load_user_snippets, save_user_snippets, get_snippets_for_lang
