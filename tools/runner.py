import os
import shlex
import shutil
from pathlib import Path

from PySide6.QtCore    import QUrl
from PySide6.QtGui     import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from core.highlighter import SyntaxHighlighter


_RUNNERS: dict[str, list[str]] = {
    'python':     ['python3', '{file}'],
    'javascript': ['node',    '{file}'],
    'typescript': ['ts-node', '{file}'],
    'ruby':       ['ruby',    '{file}'],
    'php':        ['php',     '{file}'],
    'lua':        ['lua',     '{file}'],
    'bash':       ['bash',    '{file}'],
    'go':         ['go',      'run', '{file}'],
    'perl':       ['perl',    '{file}'],
}

_COMPILERS: dict[str, dict] = {
    'cpp':  {'compile': ['g++',   '{file}', '-o', '{dir}/{stem}', '-Wall'],
             'run':     ['{dir}/{stem}']},
    'c':    {'compile': ['gcc',   '{file}', '-o', '{dir}/{stem}', '-Wall'],
             'run':     ['{dir}/{stem}']},
    'java': {'compile': ['javac', '{file}'],
             'run':     ['java',  '-cp', '{dir}', '{stem}']},
    'rust': {'compile': ['rustc', '{file}', '-o', '{dir}/{stem}'],
             'run':     ['{dir}/{stem}']},
    'kotlin': {'compile': ['kotlinc', '{file}', '-include-runtime', '-d', '{dir}/{stem}.jar'],
               'run':     ['java', '-jar', '{dir}/{stem}.jar']},
}

_SYSTEM_OPEN  = {'html', 'xml', 'svg', 'markdown', 'pdf'}
_NOT_RUNNABLE = {'css', 'scss', 'json', 'toml', 'yaml', 'ini', 'sql', 'text'}

_FILE_TEMPLATES: dict[str, str] = {
    'python':     '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n\ndef main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
    'bash':       '#!/usr/bin/env bash\nset -euo pipefail\n\n',
    'cpp':        '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}\n',
    'c':          '#include <stdio.h>\n\nint main(void) {\n    printf("Hello, World!\\n");\n    return 0;\n}\n',
    'java':       'public class {Stem} {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}\n',
    'rust':       'fn main() {\n    println!("Hello, World!");\n}\n',
    'go':         'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, World!")\n}\n',
    'html':       '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Document</title>\n</head>\n<body>\n    \n</body>\n</html>\n',
    'javascript': '\'use strict\';\n\n',
    'typescript': '',
    'css':        '/* Styles */\n',
    'markdown':   '# Title\n\n',
}


def get_template(lang: str, stem: str = "Main") -> str:
    tpl = _FILE_TEMPLATES.get(lang, "")
    return tpl.replace("{Stem}", stem.capitalize())


def _substitute(args: list[str], filepath: str) -> list[str]:
    p    = Path(filepath)
    subs = {'{file}': str(p), '{dir}': str(p.parent), '{stem}': p.stem}
    return [subs.get(a, a) for a in args]


def build_only(filepath: str | None, terminal_widget, parent_widget) -> bool:
    if not filepath:
        QMessageBox.information(parent_widget, "Compilar",
                                "Guarda el archivo primero.")
        return False
    lang = SyntaxHighlighter.detect_language(filepath)
    if lang not in _COMPILERS:
        QMessageBox.information(parent_widget, "Compilar",
                                f"«{lang}» no requiere compilación previa.")
        return False
    info        = _COMPILERS[lang]
    compile_cmd = ' '.join(_substitute(info['compile'], filepath))
    _run_in_terminal(terminal_widget, compile_cmd, Path(filepath).parent)
    return True


def run_file(filepath: str | None, terminal_widget, parent_widget) -> bool:
    if not filepath:
        QMessageBox.information(parent_widget, "Ejecutar",
                                "Guarda el archivo primero.")
        return False
    path = Path(filepath)
    if not path.exists():
        QMessageBox.warning(parent_widget, "Ejecutar",
                            f"El archivo no existe:\n{filepath}")
        return False
    lang = SyntaxHighlighter.detect_language(filepath)
    if lang in _SYSTEM_OPEN or path.suffix.lower() in ('.html', '.htm', '.md', '.svg'):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return True
    if lang in _NOT_RUNNABLE:
        QMessageBox.information(parent_widget, "Ejecutar",
                                f"Los archivos «{lang}» no se ejecutan directamente.")
        return False
    if lang in _COMPILERS:
        info        = _COMPILERS[lang]
        compile_cmd = ' '.join(_substitute(info['compile'], filepath))
        run_cmd     = ' '.join(_substitute(info['run'],     filepath))
        _run_in_terminal(terminal_widget, f"{compile_cmd} && {run_cmd}", path.parent)
        return True
    if lang in _RUNNERS:
        interp = _RUNNERS[lang][0]
        if not shutil.which(interp):
            QMessageBox.warning(parent_widget, "Ejecutar",
                                f"No se encontró «{interp}» en el PATH.")
            return False
        args     = _substitute(_RUNNERS[lang], filepath)
        full_cmd = ' '.join(f'"{a}"' if ' ' in a else a for a in args)
        _run_in_terminal(terminal_widget, full_cmd, path.parent)
        return True
    if shutil.which('xdg-open'):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return True
    QMessageBox.information(parent_widget, "Ejecutar",
                            f"No sé cómo ejecutar archivos «{lang}».")
    return False


def _run_in_terminal(terminal, cmd: str, cwd: Path):
    full = f"cd {shlex.quote(str(cwd))} && {cmd}"
    terminal.send_command(full)
