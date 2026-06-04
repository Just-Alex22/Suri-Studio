
import re
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore    import Qt, QTimer, QPoint, QSize
from PySide6.QtGui     import QColor, QFont

from core.theme import VSCode

_LANG_WORDS: dict[str, list[str]] = {
    'python': [

        'False','None','True','and','as','assert','async','await','break',
        'class','continue','def','del','elif','else','except','finally',
        'for','from','global','if','import','in','is','lambda','nonlocal',
        'not','or','pass','raise','return','try','while','with','yield',

        'abs','all','any','bin','bool','breakpoint','bytes','callable','chr',
        'compile','complex','copyright','credits','delattr','dict','dir',
        'divmod','enumerate','eval','exec','exit','filter','float','format',
        'frozenset','getattr','globals','hasattr','hash','help','hex','id',
        'input','int','isinstance','issubclass','iter','len','license','list',
        'locals','map','max','memoryview','min','next','object','oct','open',
        'ord','pow','print','property','quit','range','repr','reversed',
        'round','set','setattr','slice','sorted','staticmethod','str','sum',
        'super','tuple','type','vars','zip',

        '__init__','__name__','__main__','__file__','__doc__','__class__',
        '__all__','__slots__','__repr__','__str__','__len__','__iter__',
        '__next__','__enter__','__exit__','__call__','__getitem__',
        'self','cls',

        'os','sys','re','json','math','time','datetime','pathlib','Path',
        'subprocess','threading','collections','itertools','functools',
        'argparse','logging','unittest','dataclasses','dataclass','field',
        'typing','Optional','List','Dict','Tuple','Set','Any','Union',
        'Callable','Generator','Iterator','Type','ClassVar','Final',
    ],
    'javascript': [
        'async','await','break','case','catch','class','const','continue',
        'debugger','default','delete','do','else','export','extends',
        'finally','for','from','function','if','import','in','instanceof',
        'let','new','null','of','return','static','super','switch','this',
        'throw','true','false','try','typeof','undefined','var','void',
        'while','with','yield',
        'console','document','window','navigator','location','history',
        'Math','JSON','Promise','Array','Object','String','Number',
        'Boolean','Symbol','Map','Set','WeakMap','WeakSet','Error',
        'TypeError','RangeError','SyntaxError','ReferenceError',
        'setTimeout','setInterval','clearTimeout','clearInterval',
        'fetch','XMLHttpRequest','EventTarget','addEventListener',
        'removeEventListener','querySelector','querySelectorAll',
        'parseInt','parseFloat','isNaN','isFinite','encodeURI','decodeURI',
        'encodeURIComponent','decodeURIComponent',
        'constructor','prototype','__proto__','hasOwnProperty',
        'toString','valueOf','length','push','pop','shift','unshift',
        'splice','slice','concat','join','map','filter','reduce',
        'find','findIndex','includes','indexOf','forEach','sort','reverse',
        'then','catch','finally','resolve','reject','all','race','any',
    ],
    'typescript': [

        'async','await','break','case','catch','class','const','continue',
        'debugger','default','delete','do','else','export','extends',
        'finally','for','from','function','if','import','in','instanceof',
        'let','new','null','of','return','static','super','switch','this',
        'throw','true','false','try','typeof','undefined','var','void',
        'while','with','yield',

        'abstract','as','declare','enum','implements','interface','module',
        'namespace','never','override','private','protected','public',
        'readonly','require','type','unknown','infer','keyof','typeof',
        'satisfies','using',
        'string','number','boolean','object','symbol','bigint','any','void',
        'never','unknown','Record','Partial','Required','Readonly',
        'Pick','Omit','Exclude','Extract','NonNullable','ReturnType',
        'InstanceType','Parameters','ConstructorParameters',
    ],
    'cpp': [
        'alignas','alignof','and','and_eq','asm','auto','bitand','bitor',
        'bool','break','case','catch','char','char8_t','char16_t','char32_t',
        'class','compl','concept','const','consteval','constexpr','constinit',
        'const_cast','continue','co_await','co_return','co_yield','decltype',
        'default','delete','do','double','dynamic_cast','else','enum',
        'explicit','export','extern','false','float','for','friend','goto',
        'if','inline','int','long','mutable','namespace','new','noexcept',
        'not','not_eq','nullptr','operator','or','or_eq','private',
        'protected','public','register','reinterpret_cast','requires',
        'return','short','signed','sizeof','static','static_assert',
        'static_cast','struct','switch','template','this','thread_local',
        'throw','true','try','typedef','typeid','typename','union',
        'unsigned','using','virtual','void','volatile','wchar_t','while',

        'std','string','vector','map','unordered_map','set','unordered_set',
        'pair','tuple','optional','variant','array','span','queue','stack',
        'deque','list','forward_list','bitset','iostream','fstream',
        'sstream','algorithm','numeric','functional','memory','utility',
        'cassert','cmath','cstring','cstdio','cstdlib','ctime',
        'shared_ptr','unique_ptr','weak_ptr','make_shared','make_unique',
        'cout','cin','cerr','endl','printf','scanf','malloc','free',
        'nullptr_t','size_t','ptrdiff_t','int8_t','int16_t','int32_t',
        'int64_t','uint8_t','uint16_t','uint32_t','uint64_t',
    ],
    'java': [
        'abstract','assert','boolean','break','byte','case','catch','char',
        'class','const','continue','default','do','double','else','enum',
        'extends','final','finally','float','for','goto','if','implements',
        'import','instanceof','int','interface','long','native','new',
        'package','private','protected','public','return','short','static',
        'strictfp','super','switch','synchronized','this','throw','throws',
        'transient','try','var','void','volatile','while','true','false','null',
        'String','Integer','Long','Double','Float','Boolean','Character',
        'Byte','Short','Object','Class','System','Math','Arrays','Collections',
        'List','ArrayList','LinkedList','Map','HashMap','TreeMap','Set',
        'HashSet','TreeSet','Optional','Stream','Iterator','Iterable',
        'Comparable','Comparator','Runnable','Thread','Exception',
        'RuntimeException','NullPointerException','IOException',
        'StringBuilder','StringBuffer','Scanner','Random','File','Path',
        'Paths','Files','Override','SuppressWarnings','FunctionalInterface',
        'println','print','format','length','size','isEmpty','contains',
        'get','set','add','remove','put','keySet','values','entrySet',
    ],
    'rust': [
        'as','async','await','break','const','continue','crate','dyn',
        'else','enum','extern','false','fn','for','if','impl','in','let',
        'loop','match','mod','move','mut','pub','ref','return','self',
        'Self','static','struct','super','trait','true','type','union',
        'unsafe','use','where','while',
        'bool','char','f32','f64','i8','i16','i32','i64','i128','isize',
        'u8','u16','u32','u64','u128','usize','str','String','Vec','Box',
        'Option','Result','HashMap','HashSet','Arc','Rc','Mutex','RwLock',
        'Cell','RefCell','Cow','Ordering','Some','None','Ok','Err',
        'println!','print!','eprintln!','eprint!','format!','vec!',
        'assert!','assert_eq!','assert_ne!','panic!','todo!','unimplemented!',
        'dbg!','include!','include_str!','env!','cfg!','derive',
        'Clone','Copy','Debug','Default','Display','PartialEq','Eq',
        'PartialOrd','Ord','Hash','From','Into','TryFrom','TryInto',
        'Iterator','IntoIterator','Fn','FnMut','FnOnce','Send','Sync',
        'unwrap','expect','map','filter','collect','iter','iter_mut',
        'into_iter','len','is_empty','push','pop','contains','insert',
        'remove','get','entry','or_insert','and_then','or_else',
    ],
    'go': [
        'break','case','chan','const','continue','default','defer','else',
        'fallthrough','for','func','go','goto','if','import','interface',
        'map','package','range','return','select','struct','switch','type',
        'var','true','false','nil','iota',
        'bool','byte','complex64','complex128','error','float32','float64',
        'int','int8','int16','int32','int64','rune','string','uint',
        'uint8','uint16','uint32','uint64','uintptr',
        'make','new','len','cap','append','copy','delete','close',
        'panic','recover','print','println','real','imag','complex',
        'fmt','os','io','bufio','strings','strconv','math','sort',
        'sync','time','context','net','http','json','errors','log',
        'reflect','regexp','unicode','bytes','path','filepath',
        'Println','Printf','Sprintf','Fprintf','Errorf','Scanf',
        'goroutine','channel','WaitGroup','Mutex','RWMutex','Once',
    ],
    'bash': [
        'if','then','else','elif','fi','for','while','until','do','done',
        'case','esac','in','function','return','local','export','source',
        'declare','typeset','readonly','echo','printf','read','exit',
        'break','continue','shift','set','unset','trap','exec','eval',
        'getopts','select','time','coproc','true','false',
        'ls','cd','pwd','mkdir','rmdir','rm','cp','mv','touch','cat',
        'grep','sed','awk','find','sort','uniq','wc','head','tail',
        'cut','tr','diff','patch','tar','gzip','zip','curl','wget',
        'chmod','chown','sudo','su','ps','kill','killall','top','htop',
        'df','du','free','uname','hostname','whoami','date','which',
        'basename','dirname','realpath','readlink',
        '$?','$!','$$','$0','$1','$2','$@','$*','$#',
        'PATH','HOME','USER','SHELL','PWD','OLDPWD','IFS',
    ],
    'html': [
        'html','head','body','title','meta','link','script','style',
        'div','span','p','a','img','ul','ol','li','table','tr','td','th',
        'form','input','button','select','option','textarea','label',
        'h1','h2','h3','h4','h5','h6','header','footer','nav','main',
        'section','article','aside','figure','figcaption','blockquote',
        'pre','code','em','strong','b','i','u','br','hr','canvas','svg',
        'video','audio','source','iframe','template','slot',
        'class','id','href','src','alt','type','name','value','placeholder',
        'disabled','required','checked','selected','multiple','for','action',
        'method','enctype','target','rel','charset','content','viewport',
        'async','defer','crossorigin','integrity','data-',
        'charset=UTF-8','viewport','width=device-width',
        'text/css','text/javascript','application/json',
    ],
    'css': [
        'display','position','flex','grid','block','inline','absolute',
        'relative','fixed','sticky','static','float','clear',
        'width','height','max-width','max-height','min-width','min-height',
        'margin','padding','border','outline','box-shadow','border-radius',
        'background','background-color','background-image','background-size',
        'color','font-family','font-size','font-weight','font-style',
        'line-height','letter-spacing','text-align','text-decoration',
        'text-transform','vertical-align','white-space','overflow',
        'opacity','visibility','z-index','cursor','pointer-events',
        'transition','animation','transform','filter',
        'flex-direction','flex-wrap','justify-content','align-items',
        'align-content','flex-grow','flex-shrink','flex-basis',
        'grid-template-columns','grid-template-rows','grid-column',
        'grid-row','gap','row-gap','column-gap',
        'content','box-sizing','list-style','outline-offset',
        'auto','none','inherit','initial','unset','revert',
        'px','em','rem','vh','vw','%','fr','deg','ms','s',
        ':hover',':focus',':active',':visited',':first-child',':last-child',
        ':nth-child',':not',':before',':after','::placeholder',
        '@media','@keyframes','@import','@font-face','@supports',
    ],
    'sql': [
        'SELECT','FROM','WHERE','JOIN','LEFT','RIGHT','INNER','OUTER',
        'FULL','CROSS','ON','GROUP','BY','ORDER','HAVING','LIMIT',
        'OFFSET','INSERT','INTO','VALUES','UPDATE','SET','DELETE',
        'CREATE','TABLE','INDEX','VIEW','DATABASE','SCHEMA','DROP',
        'ALTER','ADD','COLUMN','PRIMARY','KEY','FOREIGN','REFERENCES',
        'UNIQUE','NOT','NULL','DEFAULT','AUTO_INCREMENT','CONSTRAINT',
        'CHECK','CASCADE','RESTRICT','TRANSACTION','BEGIN','COMMIT',
        'ROLLBACK','SAVEPOINT','GRANT','REVOKE','UNION','INTERSECT',
        'EXCEPT','ALL','DISTINCT','AS','IN','EXISTS','ANY','BETWEEN',
        'LIKE','IS','AND','OR','CASE','WHEN','THEN','ELSE','END',
        'WITH','RECURSIVE','RETURNING','EXPLAIN','ANALYZE',
        'COUNT','SUM','AVG','MIN','MAX','COALESCE','NULLIF','CAST',
        'CONCAT','SUBSTRING','LENGTH','UPPER','LOWER','TRIM','REPLACE',
        'ROUND','FLOOR','CEILING','ABS','MOD','NOW','CURRENT_DATE',
    ],
    'markdown': [
        '# ','## ','### ','#### ','##### ','###### ',
        '**bold**','*italic*','~~strikethrough~~','`code`',
        '```python','```javascript','```bash','```',
        '- ','* ','1. ','> ','---','***',
        '[text](url)','![alt](url)','[ref][id]',
        '| col1 | col2 |','|------|------|',
    ],
    'json': [
        'true','false','null',
    ],
    'yaml': [
        'true','false','null','yes','no','on','off',
        '---','...','!!str','!!int','!!float','!!bool','!!null',
        '!!seq','!!map',
    ],
}

_SNIPPETS: dict[str, dict[str, str]] = {
    'python': {
        'def':   'def ():\n    ',
        'class': 'class ():\n    def __init__(self):\n        ',
        'if':    'if :\n    ',
        'elif':  'elif :\n    ',
        'else':  'else:\n    ',
        'for':   'for  in :\n    ',
        'while': 'while :\n    ',
        'try':   'try:\n    \nexcept Exception as e:\n    ',
        'with':  'with  as :\n    ',
        'import':'import ',
        'from':  'from  import ',
        'print': 'print()',
        'main':  'if __name__ == "__main__":\n    main()',
        'lc':    '[ for  in ]',
        'dc':    '{ :  for  in }',
    },
    'javascript': {
        'fn':       'function () {\n    \n}',
        'arrow':    '() => {\n    \n}',
        'const':    'const  = ',
        'let':      'let  = ',
        'class':    'class  {\n    constructor() {\n        \n    }\n}',
        'if':       'if () {\n    \n}',
        'for':      'for (let i = 0; i < ; i++) {\n    \n}',
        'forof':    'for (const  of ) {\n    \n}',
        'forin':    'for (const  in ) {\n    \n}',
        'while':    'while () {\n    \n}',
        'try':      'try {\n    \n} catch (e) {\n    \n}',
        'promise':  'new Promise((resolve, reject) => {\n    \n})',
        'async':    'async function () {\n    \n}',
        'await':    'await ',
        'console':  'console.log()',
        'import':   "import  from ''",
        'export':   'export default ',
    },
    'cpp': {
        'main':   'int main() {\n    \n    return 0;\n}',
        'cout':   'std::cout << "" << std::endl;',
        'cin':    'std::cin >> ;',
        'for':    'for (int i = 0; i < ; i++) {\n    \n}',
        'rfor':   'for (int i =  - 1; i >= 0; i--) {\n    \n}',
        'while':  'while () {\n    \n}',
        'if':     'if () {\n    \n}',
        'struct':  'struct  {\n    \n};',
        'class':  'class  {\npublic:\n    \n};',
        'include':'#include <>\n',
        'vector': 'std::vector<> ;',
        'map':    'std::map<, > ;',
        'auto':   'auto  = ',
        'lambda': '[](auto ) { return ; }',
    },
    'rust': {
        'fn':     'fn () -> () {\n    \n}',
        'struct': 'struct  {\n    \n}',
        'impl':   'impl  {\n    \n}',
        'enum':   'enum  {\n    \n}',
        'trait':  'trait  {\n    \n}',
        'match':  'match  {\n     => ,\n    _ => ,\n}',
        'if':     'if  {\n    \n}',
        'for':    'for  in  {\n    \n}',
        'while':  'while  {\n    \n}',
        'let':    'let  = ;',
        'letmut': 'let mut  = ;',
        'println':'println!("{}",);',
        'main':   'fn main() {\n    \n}',
        'option': 'Option<>',
        'result': 'Result<, >',
    },
    'go': {
        'func':  'func () {\n    \n}',
        'main':  'func main() {\n    \n}',
        'if':    'if  {\n    \n}',
        'iferr': 'if err != nil {\n    return err\n}',
        'for':   'for  {\n    \n}',
        'range': 'for ,  := range  {\n    \n}',
        'goroutine':'go func() {\n    \n}()',
        'chan':  'make(chan , )',
        'struct':'type  struct {\n    \n}',
        'defer': 'defer ()',
        'fmt':   'fmt.Println()',
        'err':   'if err != nil {\n    log.Fatal(err)\n}',
    },
    'bash': {
        'if':    'if [[ ]]; then\n    \nfi',
        'for':   'for  in ; do\n    \ndone',
        'while': 'while [[ ]]; do\n    \ndone',
        'func':  ' () {\n    \n}',
        'case':  'case  in\n    )\n        ;;\nesac',
        'echo':  'echo ""',
        'read':  'read -p "" ',
        'main':  'main() {\n    \n}\nmain "$@"',
    },
}

def get_lang_words(lang: str) -> list[str]:
    return _LANG_WORDS.get(lang, [])

def get_snippets(lang: str) -> dict[str, str]:
    return _SNIPPETS.get(lang, {})

POPUP_QSS = f"""
QListWidget {{
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #007acc;
    border-radius: 4px;
    padding: 2px;
    outline: none;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
}}
QListWidget::item {{
    padding: 3px 10px;
    border-radius: 2px;
}}
QListWidget::item:selected {{
    background-color: #094771;
    color: #ffffff;
}}
QListWidget::item:hover {{
    background-color: #2d2d30;
}}
QScrollBar:vertical {{
    background: #1e1e1e;
    width: 6px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #424242;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

_KIND_ICON = {
    'keyword':  ('kw',  '#c586c0'),
    'builtin':  ('fn',  '#dcdcaa'),
    'snippet':  ('⬡',  '#4ec9b0'),
    'word':     ('w',   '#858585'),
}

class CompletionPopup(QListWidget):

    MAX_ITEMS   = 12
    MIN_PREFIX  = 2

    def __init__(self, editor):
        super().__init__(editor.viewport())
        self.editor = editor
        self.setStyleSheet(POPUP_QSS)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.hide()

        self.itemActivated.connect(self._on_activated)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._refresh)

    def schedule_update(self):

        self._timer.start()

    def is_visible(self) -> bool:
        return self.isVisible()

    def handle_key(self, event) -> bool:

        if not self.isVisible():
            return False
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            n = self.count()
            if n == 0:
                return False
            cur = self.currentRow()
            if key == Qt.Key.Key_Down:
                self.setCurrentRow(min(cur + 1, n - 1))
            else:
                self.setCurrentRow(max(cur - 1, 0))
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Tab):
            self._accept_current()
            return True
        if key == Qt.Key.Key_Escape:
            self.hide()
            return True
        return False

    def _refresh(self):
        prefix = self._current_prefix()
        if len(prefix) < self.MIN_PREFIX:
            self.hide()
            return

        lang      = self.editor._current_lang()
        lang_kws  = set(get_lang_words(lang))
        snippets  = get_snippets(lang)
        doc_words = self._extract_doc_words()

        try:
            from core.user_snippets import get_snippets_for_lang
            user_snips = get_snippets_for_lang(lang)
        except Exception:
            user_snips = {}

        candidates: list[tuple[str, str, str]] = []
        pl = prefix.lower()

        for key in user_snips:
            if key.lower().startswith(pl) and key != prefix:
                candidates.append((key, user_snips[key], 'snippet'))

        for key in snippets:
            if key.startswith(pl) and key != prefix and key not in user_snips:
                candidates.append((key, snippets[key], 'snippet'))

        for word in sorted(lang_kws):
            wl = word.lower()
            if wl.startswith(pl) and word != prefix:
                kind = 'keyword' if word.islower() else 'builtin'
                candidates.append((word, word, kind))

        for word in sorted(doc_words):
            wl = word.lower()
            if wl.startswith(pl) and word != prefix and word not in lang_kws:
                candidates.append((word, word, 'word'))

        seen   = set()
        unique = []
        for item in candidates:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)

        if not unique:
            self.hide()
            return

        self._populate(unique[:self.MAX_ITEMS])
        self._reposition()
        self.show()
        if self.count() > 0:
            self.setCurrentRow(0)

    def _populate(self, items: list[tuple[str, str, str]]):
        self.clear()
        for label, insert, kind in items:
            icon_text, icon_color = _KIND_ICON.get(kind, ('·', '#858585'))

            li = QListWidgetItem(f"  {label}")
            li.setData(Qt.ItemDataRole.UserRole, insert)
            li.setToolTip(
                f"[{kind}]  {label}"
                + (f"\n→ {insert[:60]}…" if len(insert) > 60 else f"\n→ {insert}"
                   if kind == 'snippet' else "")
            )
            self.addItem(li)

    def _reposition(self):

        cursor = self.editor.textCursor()
        rect   = self.editor.cursorRect(cursor)

        gpos   = self.editor.viewport().mapToGlobal(
            QPoint(rect.left(), rect.bottom() + 2)
        )

        n      = min(self.count(), self.MAX_ITEMS)
        item_h = 24
        w      = 280
        h      = n * item_h + 8

        screen = self.editor.screen().geometry()
        x      = min(gpos.x(), screen.right()  - w - 10)
        y      = gpos.y()
        if y + h > screen.bottom() - 10:
            y = gpos.y() - rect.height() - h - 4
        self.move(x, y)
        self.setFixedSize(w, h)

    def _extract_doc_words(self) -> set[str]:
        text   = self.editor.toPlainText()
        words  = re.findall(r'\b[A-Za-z_]\w{2,}\b', text)
        return set(words)

    def _current_prefix(self) -> str:
        cursor = self.editor.textCursor()

        block_text = cursor.block().text()
        col        = cursor.positionInBlock()
        text_left  = block_text[:col]
        m = re.search(r'[\w_]+$', text_left)
        return m.group(0) if m else ''

    def _on_activated(self, item: QListWidgetItem):
        self._accept_current()

    def _accept_current(self):
        item = self.currentItem()
        if not item:
            self.hide()
            return
        insert = item.data(Qt.ItemDataRole.UserRole)
        prefix = self._current_prefix()
        self._insert(prefix, insert)
        self.hide()

    def _insert(self, prefix: str, completion: str):

        cursor = self.editor.textCursor()

        for _ in range(len(prefix)):
            cursor.deletePreviousChar()
        cursor.insertText(completion)
        self.editor.setTextCursor(cursor)
