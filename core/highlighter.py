
from pathlib import Path
from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
from PySide6.QtCore import QRegularExpression

from core.theme import VSCode

class SyntaxHighlighter(QSyntaxHighlighter):

    LANG_EXTENSIONS = {
        'python':     ['.py', '.pyw', '.pyi'],
        'javascript': ['.js', '.mjs', '.cjs', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'html':       ['.html', '.htm', '.xhtml'],
        'css':        ['.css'],
        'scss':       ['.scss', '.sass'],
        'cpp':        ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx'],
        'java':       ['.java'],
        'rust':       ['.rs'],
        'go':         ['.go'],
        'bash':       ['.sh', '.bash', '.zsh', '.fish'],
        'sql':        ['.sql'],
        'json':       ['.json', '.jsonc'],
        'toml':       ['.toml'],
        'yaml':       ['.yaml', '.yml'],
        'markdown':   ['.md', '.markdown', '.mdx'],
        'ruby':       ['.rb', '.rake', '.gemspec'],
        'php':        ['.php'],
        'kotlin':     ['.kt', '.kts'],
        'swift':      ['.swift'],
        'lua':        ['.lua'],
        'xml':        ['.xml', '.svg', '.xsd', '.plist'],
        'ini':        ['.ini', '.cfg', '.conf'],
    }

    def __init__(self, document, language='text'):
        super().__init__(document)
        self.language = language
        self._rules = []
        self._build_rules()

    def _fmt(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:   fmt.setFontWeight(700)
        if italic: fmt.setFontItalic(True)
        return fmt

    def _add(self, pattern, fmt):
        rx = QRegularExpression(pattern)
        self._rules.append((rx, fmt))

    @property
    def _kw(self):    return self._fmt(VSCode.PURPLE, bold=False)
    @property
    def _kw2(self):   return self._fmt(VSCode.KEYWORD2)
    @property
    def _kw3(self):   return self._fmt(VSCode.BLUE_LIGHT)
    @property
    def _str(self):   return self._fmt(VSCode.STRING)
    @property
    def _num(self):   return self._fmt(VSCode.NUM)
    @property
    def _com(self):   return self._fmt(VSCode.GREEN, italic=True)
    @property
    def _fn(self):    return self._fmt(VSCode.YELLOW)
    @property
    def _cls(self):   return self._fmt(VSCode.CYAN)
    @property
    def _deco(self):  return self._fmt(VSCode.DECORATOR)
    @property
    def _tag(self):   return self._fmt(VSCode.BLUE)
    @property
    def _attr(self):  return self._fmt(VSCode.BLUE_LIGHT)
    @property
    def _var(self):   return self._fmt(VSCode.BLUE_LIGHT)
    @property
    def _op(self):    return self._fmt(VSCode.FG)

    def _build_rules(self):
        self._rules = []
        lang = self.language

        if lang == 'python':
            self._add(r'\b(False|None|True|and|as|assert|async|await|break|class|'
                      r'continue|def|del|elif|else|except|finally|for|from|global|'
                      r'if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|'
                      r'try|while|with|yield)\b', self._kw)
            self._add(r'\b(int|float|str|bool|bytes|list|dict|set|tuple|type|object|'
                      r'complex|bytearray|memoryview|range|frozenset)\b', self._kw2)
            self._add(r'\b(abs|all|any|bin|callable|chr|compile|delattr|dir|divmod|'
                      r'enumerate|eval|exec|filter|format|getattr|globals|hasattr|'
                      r'hash|help|hex|id|input|isinstance|issubclass|iter|len|locals|'
                      r'map|max|min|next|oct|open|ord|pow|print|property|repr|'
                      r'reversed|round|setattr|slice|sorted|staticmethod|sum|super|'
                      r'vars|zip|__import__)\b', self._fn)
            self._add(r'\bself\b|\bcls\b', self._kw3)
            self._add(r'@[\w.]+', self._deco)
            self._add(r'\bclass\s+(\w+)', self._cls)
            self._add(r'\bdef\s+(\w+)', self._fn)

            self._add(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', self._str)

            self._add(r'(f?b?r?"[^"\\]*(?:\\.[^"\\]*)*"|f?b?r?\'[^\'\\]*(?:\\.[^\'\\]*)*\')', self._str)
            self._add(r'\b(0x[0-9a-fA-F]+|0o[0-7]+|0b[01]+|\d+\.?\d*([eE][+-]?\d+)?j?)\b', self._num)
            self._add(r'#.*$', self._com)

        elif lang in ('javascript', 'typescript'):
            self._add(r'\b(async|await|break|case|catch|class|const|continue|debugger|'
                      r'default|delete|do|else|export|extends|finally|for|from|function|'
                      r'if|import|in|instanceof|let|new|of|return|static|super|switch|'
                      r'this|throw|try|typeof|var|void|while|with|yield)\b', self._kw)
            self._add(r'\b(null|undefined|true|false|NaN|Infinity)\b', self._kw3)
            self._add(r'\b(string|number|boolean|object|symbol|bigint|any|never|void|'
                      r'unknown|readonly|keyof|typeof|infer|is)\b', self._kw2)
            self._add(r'\b(console|document|window|Math|JSON|Promise|Array|Object|'
                      r'String|Number|Boolean|Symbol|Map|Set|WeakMap|WeakRef|Error|'
                      r'setTimeout|setInterval|clearTimeout|clearInterval|fetch|'
                      r'parseInt|parseFloat|isNaN|isFinite|encodeURI|decodeURI)\b', self._fn)
            self._add(r'`[^`\\]*(?:\\.[^`\\]*)*`', self._str)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b(0x[0-9a-fA-F]+|\d+\.?\d*([eE][+-]?\d+)?n?)\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'(?<![/])/(?![/*\s])[^/\n\\]*(?:\\.[^/\n\\]*)*/[gimsuy]*', self._str)
            self._add(r'(?<=\bfunction\s)(\w+)|(?<=\s)(\w+)(?=\s*\()', self._fn)
            self._add(r'(?<=class\s)(\w+)', self._cls)
            self._add(r'interface\s+(\w+)|type\s+(\w+)\s*=', self._cls)

        elif lang == 'html':
            self._add(r'<!--[\s\S]*?-->', self._com)
            self._add(r'<!DOCTYPE[^>]*>', self._kw)
            self._add(r'</?\s*\w[\w-]*', self._tag)
            self._add(r'/?\s*>', self._tag)
            self._add(r'\b[\w-]+(?=\s*=)', self._attr)
            self._add(r'"[^"]*"', self._str)
            self._add(r"'[^']*'", self._str)
            self._add(r'&\w+;|&#\d+;', self._kw3)

        elif lang in ('css', 'scss'):
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'//.*$', self._com)
            self._add(r'@[\w-]+', self._kw)
            self._add(r'\$[\w-]+', self._var)

            self._add(r'[.#:]?[\w-]+(?:\s*[>+~]\s*[.#:]?[\w-]+)*\s*(?=\{)', self._cls)

            self._add(r'::?[\w-]+', self._fn)

            self._add(r'[\w-]+(?=\s*:)', self._attr)

            self._add(r'#[0-9a-fA-F]{3,8}\b', self._num)

            self._add(r'"[^"]*"', self._str)
            self._add(r"'[^']*'", self._str)

            self._add(r'-?\d+\.?\d*(%|px|em|rem|vh|vw|vmin|vmax|ch|ex|cm|mm|in|pt|pc|fr|s|ms|deg|rad|turn|grad|dpi|dpcm|dppx)?', self._num)
            self._add(r'\b(auto|none|inherit|initial|unset|revert|normal|bold|italic|'
                      r'flex|grid|block|inline|absolute|relative|fixed|sticky|hidden|'
                      r'visible|solid|dashed|dotted|transparent)\b', self._kw2)

        elif lang == 'cpp':
            self._add(r'#\s*(include|define|undef|ifdef|ifndef|if|elif|else|endif|'
                      r'pragma|error|warning|line)\b', self._deco)
            self._add(r'<[\w./]+>', self._str)
            self._add(r'\b(alignas|alignof|and|and_eq|asm|auto|bitand|bitor|bool|'
                      r'break|case|catch|char|char8_t|char16_t|char32_t|class|compl|'
                      r'concept|const|consteval|constexpr|constinit|const_cast|'
                      r'continue|co_await|co_return|co_yield|decltype|default|delete|'
                      r'do|double|dynamic_cast|else|enum|explicit|export|extern|false|'
                      r'float|for|friend|goto|if|inline|int|long|mutable|namespace|'
                      r'new|noexcept|not|not_eq|nullptr|operator|or|or_eq|private|'
                      r'protected|public|register|reinterpret_cast|requires|return|'
                      r'short|signed|sizeof|static|static_assert|static_cast|struct|'
                      r'switch|template|this|thread_local|throw|true|try|typedef|'
                      r'typeid|typename|union|unsigned|using|virtual|void|volatile|'
                      r'wchar_t|while|xor|xor_eq)\b', self._kw)
            self._add(r'\b(int8_t|int16_t|int32_t|int64_t|uint8_t|uint16_t|uint32_t|'
                      r'uint64_t|size_t|ptrdiff_t|intptr_t|uintptr_t|string|vector|'
                      r'map|unordered_map|set|pair|optional|variant|tuple|shared_ptr|'
                      r'unique_ptr|weak_ptr|array|span|string_view)\b', self._cls)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b(0x[0-9a-fA-F]+[uUlL]*|0b[01]+[uUlL]*|0[0-7]+[uUlL]*|'
                      r'\d+\.?\d*([eE][+-]?\d+)?[fFlL]?)\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'\b\w+(?=\s*\()', self._fn)
            self._add(r'\b[A-Z][A-Z0-9_]{2,}\b', self._kw3)
            self._add(r'(?<=class\s|struct\s)(\w+)', self._cls)

        elif lang == 'java':
            self._add(r'\b(abstract|assert|break|case|catch|class|const|continue|'
                      r'default|do|else|enum|extends|final|finally|for|goto|if|'
                      r'implements|import|instanceof|interface|native|new|package|'
                      r'private|protected|public|return|static|strictfp|super|switch|'
                      r'synchronized|this|throw|throws|transient|try|volatile|while)\b', self._kw)
            self._add(r'\b(boolean|byte|char|double|float|int|long|short|void|var)\b', self._kw2)
            self._add(r'\b(null|true|false)\b', self._kw3)
            self._add(r'@\w+', self._deco)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b\d+\.?\d*[fFdDlL]?\b|0x[0-9a-fA-F]+[lL]?\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'(?<=class\s|interface\s|enum\s)(\w+)', self._cls)
            self._add(r'\b\w+(?=\s*\()', self._fn)

        elif lang == 'rust':
            self._add(r'\b(as|async|await|break|const|continue|crate|dyn|else|enum|'
                      r'extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|'
                      r'pub|ref|return|self|Self|static|struct|super|trait|true|type|'
                      r'union|unsafe|use|where|while)\b', self._kw)
            self._add(r'\b(bool|char|f32|f64|i8|i16|i32|i64|i128|isize|u8|u16|u32|'
                      r'u64|u128|usize|str|String|Vec|Box|Option|Result|HashMap|'
                      r'HashSet|Arc|Rc|Cell|RefCell|Mutex|RwLock)\b', self._cls)
            self._add(r'\b(println!|print!|eprintln!|eprint!|format!|vec!|assert!|'
                      r'assert_eq!|assert_ne!|panic!|todo!|unimplemented!|dbg!|'
                      r'include!|include_str!|concat!|env!|cfg!)\b', self._fn)
            self._add(r"b?r?\"[^\"\\]*(?:\\.[^\"\\]*)*\"", self._str)
            self._add(r"b?r?'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r"r#\"[\s\S]*?\"#", self._str)
            self._add(r'\b(0x[0-9a-fA-F_]+|0o[0-7_]+|0b[01_]+|\d[\d_]*\.?[\d_]*([eE][+-]?[\d_]+)?)\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'#\[[\s\S]*?\]', self._deco)
            self._add(r"'[a-z_]\w*\b(?!')", self._kw3)
            self._add(r'(?<=fn\s)(\w+)', self._fn)
            self._add(r'(?<=struct\s|enum\s|trait\s|impl\s)(\w+)', self._cls)

        elif lang == 'go':
            self._add(r'\b(break|case|chan|const|continue|default|defer|else|fallthrough|'
                      r'for|func|go|goto|if|import|interface|map|package|range|return|'
                      r'select|struct|switch|type|var)\b', self._kw)
            self._add(r'\b(bool|byte|complex64|complex128|error|float32|float64|int|'
                      r'int8|int16|int32|int64|rune|string|uint|uint8|uint16|uint32|'
                      r'uint64|uintptr)\b', self._kw2)
            self._add(r'\b(true|false|nil|iota)\b', self._kw3)
            self._add(r'\b(make|new|len|cap|append|copy|delete|close|panic|recover|'
                      r'print|println|real|imag|complex)\b', self._fn)
            self._add(r'`[^`]*`', self._str)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b(0x[0-9a-fA-F_]+|\d[\d_]*\.?[\d_]*([eE][+-]?[\d_]+)?)\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'(?<=func\s)(\w+)', self._fn)
            self._add(r'(?<=type\s)(\w+)', self._cls)

        elif lang == 'bash':
            self._add(r'\b(if|then|else|elif|fi|for|while|until|do|done|case|esac|in|'
                      r'function|return|local|export|source|declare|typeset|readonly|'
                      r'echo|printf|read|exit|break|continue|shift|set|unset|trap|'
                      r'exec|eval|getopts|select|time|coproc)\b', self._kw)
            self._add(r'\b(true|false|null)\b', self._kw3)
            self._add(r'\$\{[^}]+\}|\$[\w@#?$!*0-9-]+', self._var)
            self._add(r'\$\([^)]+\)', self._kw3)
            self._add(r'"[^"]*"', self._str)
            self._add(r"'[^']*'", self._str)
            self._add(r'`[^`]*`', self._fn)
            self._add(r'#.*$', self._com)
            self._add(r'\b\d+\b', self._num)
            self._add(r'(?m)^\s*([\w-]+)\s*\(\)', self._fn)
            self._add(r'\[\[.*?\]\]|\[.*?\]', self._kw2)

        elif lang == 'sql':
            kws = (r'\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|'
                   r'GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|INSERT|INTO|VALUES|UPDATE|SET|'
                   r'DELETE|CREATE|TABLE|INDEX|VIEW|DATABASE|SCHEMA|DROP|ALTER|ADD|'
                   r'COLUMN|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|NOT|NULL|DEFAULT|'
                   r'AUTO_INCREMENT|IDENTITY|CONSTRAINT|CHECK|CASCADE|RESTRICT|'
                   r'TRANSACTION|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|GRANT|REVOKE|'
                   r'UNION|INTERSECT|EXCEPT|ALL|DISTINCT|AS|IN|EXISTS|ANY|SOME|'
                   r'BETWEEN|LIKE|IS|AND|OR|CASE|WHEN|THEN|ELSE|END|WITH|RECURSIVE|'
                   r'RETURNING|EXPLAIN|ANALYZE|VACUUM|TRUNCATE|IF)\b')
            fns = (r'\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|NULLIF|IFNULL|NVL|CAST|CONVERT|'
                   r'CONCAT|SUBSTRING|LENGTH|UPPER|LOWER|TRIM|REPLACE|ROUND|FLOOR|'
                   r'CEILING|ABS|MOD|NOW|CURRENT_DATE|CURRENT_TIME|CURRENT_TIMESTAMP|'
                   r'DATE|TIME|YEAR|MONTH|DAY|HOUR|MINUTE|SECOND|DATEDIFF|DATEADD|'
                   r'ROW_NUMBER|RANK|DENSE_RANK|NTILE|LAG|LEAD|FIRST_VALUE|LAST_VALUE)\b')
            self._add(kws, self._kw)
            self._add(fns, self._fn)
            self._add(r"'[^']*'", self._str)
            self._add(r'\b\d+\.?\d*\b', self._num)
            self._add(r'--.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'\b[A-Z][A-Z0-9_]+\b', self._cls)

        elif lang == 'json':
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"\s*(?=:)', self._attr)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r'\b(true|false|null)\b', self._kw3)
            self._add(r'-?\d+\.?\d*([eE][+-]?\d+)?\b', self._num)
            self._add(r'//.*$', self._com)

        elif lang == 'toml':
            self._add(r'#.*$', self._com)
            self._add(r'^\s*\[+[\w.\s-]+\]+', self._cls)
            self._add(r'^\s*[\w-]+\s*(?==)', self._attr)
            self._add(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', self._str)
            self._add(r'"[^"]*"|\'[^\']*\'', self._str)
            self._add(r'\b(true|false)\b', self._kw3)
            self._add(r'\b\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?\b', self._num)
            self._add(r'-?\d+\.?\d*([eE][+-]?\d+)?\b', self._num)

        elif lang == 'yaml':
            self._add(r'#.*$', self._com)
            self._add(r'^---$|^\.\.\.$', self._kw)
            self._add(r'^\s*[\w-]+\s*(?=:)', self._attr)
            self._add(r'(?<=:\s)&\w+|(?<=:\s)\*\w+', self._kw3)
            self._add(r'![\w/]+', self._deco)
            self._add(r'"[^"]*"|\'[^\']*\'', self._str)
            self._add(r'\b(true|false|null|yes|no|on|off)\b', self._kw3)
            self._add(r'-?\d+\.?\d*([eE][+-]?\d+)?\b', self._num)

        elif lang == 'markdown':
            self._add(r'^#{1,6}\s.+$', self._fmt(VSCode.BLUE, bold=True))
            self._add(r'\*\*\*[^*]+\*\*\*|___[^_]+___',
                      self._fmt(VSCode.FG, bold=True, italic=True))
            self._add(r'\*\*[^*]+\*\*|__[^_]+__', self._fmt(VSCode.FG, bold=True))
            self._add(r'\*[^*]+\*|_[^_]+_', self._fmt(VSCode.FG, italic=True))
            self._add(r'`[^`]+`', self._fmt(VSCode.STRING))
            self._add(r'```[\s\S]*?```', self._fmt(VSCode.FG_DIM))
            self._add(r'^\s*[-*+]\s', self._fmt(VSCode.BLUE))
            self._add(r'^\s*\d+\.\s', self._fmt(VSCode.BLUE))
            self._add(r'\[([^\]]+)\]\(([^)]+)\)', self._fmt(VSCode.BLUE_LIGHT))
            self._add(r'!\[([^\]]*)\]\(([^)]+)\)', self._fmt(VSCode.CYAN))
            self._add(r'^>.*$', self._fmt(VSCode.FG_DIM, italic=True))
            self._add(r'^---+$|^\*\*\*+$', self._fmt(VSCode.FG_DIM))
            self._add(r'\[\[.*?\]\]|\[.*?\]\[.*?\]', self._fmt(VSCode.BLUE_LIGHT))

        elif lang == 'ruby':
            self._add(r'\b(BEGIN|END|alias|and|begin|break|case|class|def|defined\?|'
                      r'do|else|elsif|end|ensure|false|for|if|in|module|next|nil|not|'
                      r'or|redo|rescue|retry|return|self|super|then|true|undef|unless|'
                      r'until|when|while|yield)\b', self._kw)
            self._add(r':[a-zA-Z_]\w*', self._kw3)
            self._add(r'@{1,2}[\w]+', self._var)
            self._add(r'\$[\w]+', self._kw3)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'#\{[^}]*\}', self._fn)
            self._add(r'#.*$', self._com)
            self._add(r'=begin[\s\S]*?=end', self._com)
            self._add(r'\b\d+\.?\d*\b', self._num)
            self._add(r'(?<=def\s)(\w+[?!]?)', self._fn)
            self._add(r'(?<=class\s|module\s)(\w+)', self._cls)

        elif lang == 'php':
            self._add(r'<\?php|\?>', self._kw)
            self._add(r'\b(abstract|and|array|as|break|callable|case|catch|class|clone|'
                      r'const|continue|declare|default|die|do|echo|else|elseif|empty|'
                      r'enddeclare|endfor|endforeach|endif|endswitch|endwhile|eval|exit|'
                      r'extends|final|finally|fn|for|foreach|function|global|goto|if|'
                      r'implements|include|include_once|instanceof|insteadof|interface|'
                      r'isset|list|match|namespace|new|or|print|private|protected|public|'
                      r'readonly|require|require_once|return|static|switch|throw|trait|'
                      r'try|unset|use|var|while|xor|yield)\b', self._kw)
            self._add(r'\$[a-zA-Z_]\w*', self._var)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b\d+\.?\d*\b', self._num)
            self._add(r'//.*$|#.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)

        elif lang == 'kotlin':
            self._add(r'\b(abstract|actual|as|break|by|catch|class|companion|const|'
                      r'constructor|continue|crossinline|data|delegate|do|dynamic|else|'
                      r'enum|expect|external|false|field|file|final|finally|for|fun|get|'
                      r'if|import|in|infix|init|inline|inner|interface|internal|is|'
                      r'lateinit|noinline|null|object|open|operator|out|override|package|'
                      r'param|private|property|protected|public|receiver|reified|return|'
                      r'sealed|set|setparam|super|suspend|tailrec|this|throw|true|try|'
                      r'typealias|typeof|val|value|var|vararg|when|where|while)\b', self._kw)
            self._add(r'\b(Boolean|Byte|Char|Double|Float|Int|Long|Nothing|Short|String|'
                      r'Unit|Any|Array|List|Map|Set|MutableList|MutableMap|MutableSet|'
                      r'Sequence|Pair|Triple)\b', self._cls)
            self._add(r'"""[\s\S]*?"""', self._str)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b\d+\.?\d*[fFdDlL]?\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'@\w+', self._deco)
            self._add(r'(?<=fun\s)(\w+)', self._fn)
            self._add(r'(?<=class\s|object\s|interface\s)(\w+)', self._cls)

        elif lang == 'swift':
            self._add(r'\b(associatedtype|class|deinit|enum|extension|fileprivate|func|'
                      r'import|init|inout|internal|let|open|operator|precedencegroup|'
                      r'private|protocol|public|rethrows|static|struct|subscript|typealias|'
                      r'var|break|case|catch|continue|default|defer|do|else|fallthrough|'
                      r'for|guard|if|in|repeat|return|throw|switch|where|while|'
                      r'Any|AnyObject|Type|Self|self|super|nil|true|false|'
                      r'async|await|actor|nonisolated|isolated)\b', self._kw)
            self._add(r'\b(Int|Int8|Int16|Int32|Int64|UInt|UInt8|UInt16|UInt32|UInt64|'
                      r'Float|Float16|Float80|Double|Bool|String|Character|Unicode|'
                      r'Optional|Array|Dictionary|Set|Result|Never|Void)\b', self._cls)
            self._add(r'"""[\s\S]*?"""', self._str)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r'\b\d+\.?\d*\b', self._num)
            self._add(r'//.*$', self._com)
            self._add(r'/\*[\s\S]*?\*/', self._com)
            self._add(r'@\w+', self._deco)
            self._add(r'#\w+', self._deco)

        elif lang == 'lua':
            self._add(r'\b(and|break|do|else|elseif|end|false|for|function|goto|if|in|'
                      r'local|nil|not|or|repeat|return|then|true|until|while)\b', self._kw)
            self._add(r'\b(print|tostring|tonumber|type|pairs|ipairs|next|select|'
                      r'unpack|table\.unpack|require|pcall|xpcall|error|assert|'
                      r'setmetatable|getmetatable|rawget|rawset|rawequal|rawlen|'
                      r'string\.\w+|table\.\w+|math\.\w+|io\.\w+|os\.\w+|'
                      r'coroutine\.\w+)\b', self._fn)
            self._add(r'\[\[[\s\S]*?\]\]', self._str)
            self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"', self._str)
            self._add(r"'[^'\\]*(?:\\.[^'\\]*)*'", self._str)
            self._add(r'\b\d+\.?\d*([eE][+-]?\d+)?\b|0x[0-9a-fA-F]+\b', self._num)
            self._add(r'--\[\[[\s\S]*?\]\]', self._com)
            self._add(r'--.*$', self._com)
            self._add(r'(?<=function\s)(\w[\w.]*)', self._fn)

        elif lang == 'xml':
            self._add(r'<!--[\s\S]*?-->', self._com)
            self._add(r'<!\w+[^>]*>', self._kw)
            self._add(r'<\?[\s\S]*?\?>', self._deco)
            self._add(r'</?\s*[\w:]+', self._tag)
            self._add(r'/?\s*>', self._tag)
            self._add(r'\b[\w:]+(?=\s*=)', self._attr)
            self._add(r'"[^"]*"', self._str)
            self._add(r"'[^']*'", self._str)
            self._add(r'&\w+;|&#\d+;|&#x[0-9a-fA-F]+;', self._kw3)

        elif lang == 'ini':
            self._add(r'^\s*;.*$|^\s*#.*$', self._com)
            self._add(r'^\s*\[.*\]\s*$', self._cls)
            self._add(r'^\s*[\w-]+\s*(?==)', self._attr)
            self._add(r'(?<==\s*).*$', self._str)

    def highlightBlock(self, text):
        for rx, fmt in self._rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

    def set_language(self, language):
        self.language = language
        self._build_rules()
        self.rehighlight()

    @staticmethod
    def detect_language(filepath):
        if not filepath:
            return 'text'
        ext = Path(filepath).suffix.lower()
        name = Path(filepath).name.lower()

        special = {
            'makefile': 'bash', 'dockerfile': 'bash',
            '.gitignore': 'ini', '.env': 'ini',
            'gemfile': 'ruby', 'rakefile': 'ruby',
        }
        if name in special:
            return special[name]
        for lang, exts in SyntaxHighlighter.LANG_EXTENSIONS.items():
            if ext in exts:
                return lang
        return 'text'
