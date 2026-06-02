# ui/git_panel.py — Panel Git lateral de Sonia
# Todos los strings UI usan tr() para soporte de 11 idiomas.

from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QInputDialog, QStyle,
)
from PySide6.QtCore  import Qt, QThread, Signal
from PySide6.QtGui   import QColor, QFont

from core.theme     import VSCode
from core.translate import tr


# ─────────────────────────────────────────────────────────────────────────────
#  Utilidades
# ─────────────────────────────────────────────────────────────────────────────
def _git(args: list[str], cwd: str) -> tuple[str, str, int]:
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=cwd, timeout=15
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), -1


def find_repo_root(path: str) -> str | None:
    if not path or not shutil.which("git"):
        return None
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    try:
        out, _, code = _git(["rev-parse", "--show-toplevel"], str(p))
        return out if code == 0 and out else None
    except Exception:
        return None


_STATUS_META: dict[str, tuple[str, str]] = {
    "M":  ("M", "#e5c07b"),
    "A":  ("A", "#98c379"),
    "D":  ("D", "#e06c75"),
    "R":  ("R", "#61afef"),
    "C":  ("C", "#61afef"),
    "U":  ("U", "#e06c75"),
    "??": ("?", "#858585"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Workers
# ─────────────────────────────────────────────────────────────────────────────
class GitStatusWorker(QThread):
    done = Signal(list)

    def __init__(self, repo: str):
        super().__init__()
        self._repo = repo

    def run(self):
        out, _, code = _git(["status", "--porcelain", "-u"], self._repo)
        items = []
        if code == 0:
            for line in out.splitlines():
                if len(line) < 4:
                    continue
                xy   = line[:2]
                path = line[3:].strip().strip('"')
                if " -> " in path:
                    path = path.split(" -> ")[-1]
                items.append((xy, path))
        self.done.emit(items)


class GitDiffWorker(QThread):
    done = Signal(str)

    def __init__(self, repo: str, relpath: str):
        super().__init__()
        self._repo    = repo
        self._relpath = relpath

    def run(self):
        out, _, _ = _git(["diff", "HEAD", "--", self._relpath], self._repo)
        if not out.strip():
            out, _, _ = _git(["diff", "--cached", "--", self._relpath], self._repo)
        self.done.emit(out)


class GitActionWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, repo: str, args: list[str]):
        super().__init__()
        self._repo = repo
        self._args = args

    def run(self):
        out, err, code = _git(self._args, self._repo)
        self.done.emit(code == 0, out or err or "")


# ─────────────────────────────────────────────────────────────────────────────
#  Panel Git
# ─────────────────────────────────────────────────────────────────────────────
class GitPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo:          str | None = None
        self._status_worker: QThread | None = None
        self._action_worker: QThread | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-bottom:1px solid {VSCode.BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 6, 8, 6)

        self._lbl_title = QLabel(tr("GIT"))
        self._lbl_title.setStyleSheet(
            f"color:{VSCode.FG_DIM}; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )

        btn_ref = QPushButton()
        btn_ref.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        btn_ref.setFixedSize(22, 22)
        btn_ref.setToolTip(tr("git_refresh"))
        btn_ref.setStyleSheet("border:none; background:transparent;")
        btn_ref.clicked.connect(self.refresh)

        hdr_lay.addWidget(self._lbl_title)
        hdr_lay.addStretch()
        hdr_lay.addWidget(btn_ref)
        lay.addWidget(hdr)

        # ── Barra de acciones ─────────────────────────────────────────────
        action_bar = QWidget()
        action_bar.setStyleSheet(
            f"background:{VSCode.BG_LIGHT}; border-bottom:1px solid {VSCode.BORDER};"
        )
        ab_lay = QHBoxLayout(action_bar)
        ab_lay.setContentsMargins(6, 5, 6, 5)
        ab_lay.setSpacing(4)

        _btn_qss = (
            f"QPushButton {{"
            f"background:{VSCode.BG_LIGHTER}; color:{VSCode.FG};"
            f"border:1px solid {VSCode.BORDER}; border-radius:3px;"
            f"padding:4px 6px; font-size:11px; font-weight:bold;"
            f"}}"
            f"QPushButton:hover {{background:{VSCode.BLUE_ACCENT}; color:{VSCode.WHITE}; border-color:{VSCode.BLUE_ACCENT};}}"
            f"QPushButton:pressed {{background:{VSCode.BLUE}; color:{VSCode.WHITE};}}"
            f"QPushButton:disabled {{color:{VSCode.FG_INACTIVE};}}"
        )

        self._btn_push   = QPushButton("↑ Push")
        self._btn_pull   = QPushButton("↓ Pull")
        self._btn_commit = QPushButton("✓ Commit")
        self._btn_reset  = QPushButton("✕ Reset")

        self._btn_push.setToolTip(tr("git_push_tip"))
        self._btn_pull.setToolTip(tr("git_pull_tip"))
        self._btn_commit.setToolTip(tr("git_commit_tip"))
        self._btn_reset.setToolTip(tr("git_reset_tip"))

        for btn in [self._btn_push, self._btn_pull, self._btn_commit, self._btn_reset]:
            btn.setStyleSheet(_btn_qss)
            btn.setEnabled(False)
            ab_lay.addWidget(btn)

        self._btn_push.clicked.connect(self._do_push)
        self._btn_pull.clicked.connect(self._do_pull)
        self._btn_commit.clicked.connect(self._do_commit)
        self._btn_reset.clicked.connect(self._do_reset)

        lay.addWidget(action_bar)

        # ── Árbol con diff expandible ─────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(12)
        self._tree.setAnimated(True)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background:{VSCode.BG}; border:none; outline:none; font-size:12px;
            }}
            QTreeWidget::item {{ padding:3px 4px; }}
            QTreeWidget::item:selected {{ background:{VSCode.SELECTION}; color:{VSCode.WHITE}; }}
            QTreeWidget::item:hover {{ background:{VSCode.BG_LIGHTER}; }}
        """)
        self._tree.itemExpanded.connect(self._on_expanded)
        lay.addWidget(self._tree, 1)

        # ── Status ────────────────────────────────────────────────────────
        self._lbl_status = QLabel(tr("No repo"))
        self._lbl_status.setStyleSheet(
            f"color:{VSCode.FG_INACTIVE}; font-size:11px; padding:4px 10px;"
            f"border-top:1px solid {VSCode.BORDER};"
        )
        lay.addWidget(self._lbl_status)

    # ── API pública ───────────────────────────────────────────────────────
    def set_repo(self, path: str) -> None:
        root = find_repo_root(path)
        if root == self._repo:
            return
        self._repo = root
        if root:
            branch = self._current_branch()
            self._lbl_title.setText(f"{tr('GIT')}  {branch}")
            self._set_btns(True)
            self.refresh()
        else:
            self._lbl_title.setText(tr("GIT"))
            self._lbl_status.setText(tr("No repo"))
            self._tree.clear()
            self._set_btns(False)

    def refresh(self) -> None:
        if not self._repo:
            return
        if self._status_worker and self._status_worker.isRunning():
            return
        self._lbl_status.setText("…")
        self._status_worker = GitStatusWorker(self._repo)
        self._status_worker.done.connect(self._on_status)
        self._status_worker.start()

    # ── Estado ───────────────────────────────────────────────────────────
    def _on_status(self, items: list) -> None:
        self._tree.clear()
        if not items:
            self._lbl_status.setText(tr("No changes"))
            return

        staged    = [(xy, p) for xy, p in items if xy[0] not in (' ', '?')]
        unstaged  = [(xy, p) for xy, p in items if xy[1] not in (' ', '?')]
        untracked = [(xy, p) for xy, p in items if xy.strip() == "??"]

        for label, group, color in [
            (tr("git_staged"),    staged,    "#98c379"),
            (tr("git_unstaged"),  unstaged,  "#e5c07b"),
            (tr("git_untracked"), untracked, "#858585"),
        ]:
            if not group:
                continue
            sec = QTreeWidgetItem([f"  {label}  ({len(group)})"])
            sec.setForeground(0, QColor(color))
            sec.setFlags(sec.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            f = QFont(); f.setBold(True); f.setPointSize(11)
            sec.setFont(0, f)
            self._tree.addTopLevelItem(sec)
            sec.setExpanded(True)

            for xy, relpath in group:
                code = xy.strip() or "M"
                meta = _STATUS_META.get(code, _STATUS_META.get(code[0], ("?", "#858585")))
                letter, clr = meta
                fi = QTreeWidgetItem([f"  {letter}  {relpath}"])
                fi.setForeground(0, QColor(clr))
                fi.setData(0, Qt.ItemDataRole.UserRole, ("file", relpath))
                ph = QTreeWidgetItem([tr("git_loading_diff")])
                ph.setForeground(0, QColor(VSCode.FG_DIM))
                ph.setData(0, Qt.ItemDataRole.UserRole, ("ph",))
                fi.addChild(ph)
                sec.addChild(fi)

        total = len(items)
        self._lbl_status.setText(tr("git_n_changes").format(n=total))

    # ── Diff expandible ───────────────────────────────────────────────────
    def _on_expanded(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "file":
            return
        if item.childCount() == 1:
            ch = item.child(0)
            if ch.data(0, Qt.ItemDataRole.UserRole) == ("ph",):
                w = GitDiffWorker(self._repo, data[1])
                w.done.connect(lambda diff, i=item: self._on_diff(i, diff))
                w.start()
                item._dw = w   # evitar GC

    def _on_diff(self, item: QTreeWidgetItem, diff: str) -> None:
        item.takeChildren()
        lines = diff.splitlines()
        if not lines:
            empty = QTreeWidgetItem([tr("git_no_diff")])
            empty.setForeground(0, QColor(VSCode.FG_INACTIVE))
            item.addChild(empty)
            return

        _MONO = QFont("JetBrains Mono", 11)
        for line in lines[:300]:
            if line.startswith(("+++", "---")):   color = VSCode.FG_DIM
            elif line.startswith("+"):             color = "#98c379"
            elif line.startswith("-"):             color = "#e06c75"
            elif line.startswith("@@"):            color = VSCode.CYAN
            elif line.startswith("diff "):         color = VSCode.BLUE_LIGHT
            else:                                  color = VSCode.FG_DIM
            it = QTreeWidgetItem([f"  {line[:140]}"])
            it.setForeground(0, QColor(color))
            it.setFont(0, _MONO)
            item.addChild(it)

        if len(lines) > 300:
            trunc = QTreeWidgetItem([tr("git_diff_truncated")])
            trunc.setForeground(0, QColor(VSCode.FG_INACTIVE))
            item.addChild(trunc)

    # ── Acciones ──────────────────────────────────────────────────────────
    def _do_push(self):
        self._run(["push"], tr("git_push_ok"))

    def _do_pull(self):
        self._run(["pull"], tr("git_pull_ok"))

    def _do_commit(self):
        msg, ok = QInputDialog.getText(self, "Commit", tr("Commit message…"))
        if not ok:
            return
        if not msg.strip():
            QMessageBox.warning(self, "Commit", tr("git_commit_empty"))
            return
        self._run(["commit", "-am", msg.strip()], tr("git_commit_ok"))

    def _do_reset(self):
        r = QMessageBox.question(
            self, "Reset", tr("git_reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            self._run(["reset", "--hard", "HEAD"], tr("git_reset_ok"))

    def _run(self, args: list[str], ok_msg: str) -> None:
        if not self._repo:
            return
        if not shutil.which("git"):
            QMessageBox.warning(self, "Git", tr("git_no_git"))
            return
        self._set_btns(False)
        self._lbl_status.setText(tr("git_running"))
        w = GitActionWorker(self._repo, args)
        w.done.connect(lambda ok, msg, s=ok_msg: self._on_done(ok, msg, s))
        w.start()
        self._action_worker = w

    def _on_done(self, success: bool, msg: str, ok_msg: str) -> None:
        self._set_btns(True)
        if success:
            self._lbl_status.setText(ok_msg)
            self.refresh()
        else:
            QMessageBox.critical(self, "Git", tr("git_error").format(err=msg))
            self._lbl_status.setText(tr("git_error_status"))

    # ── Helpers ───────────────────────────────────────────────────────────
    def _set_btns(self, enabled: bool) -> None:
        for b in [self._btn_push, self._btn_pull,
                  self._btn_commit, self._btn_reset]:
            b.setEnabled(enabled)

    def _current_branch(self) -> str:
        if not self._repo:
            return ""
        out, _, code = _git(["branch", "--show-current"], self._repo)
        return f"({out})" if code == 0 and out else ""
