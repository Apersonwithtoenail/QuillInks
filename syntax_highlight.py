"""Lightweight syntax highlighter for Quillinks. Regex-based per language."""

# Token color tags per theme will be looked up from the app at apply time.
# Each language: list of (tag_name, compiled_regex)

import re


def _kw(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b")


PYTHON_KW = [
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "match", "case", "self", "cls",
]
JS_KW = [
    "break", "case", "catch", "class", "const", "continue", "debugger",
    "default", "delete", "do", "else", "export", "extends", "finally", "for",
    "function", "if", "import", "in", "instanceof", "let", "new", "of",
    "return", "super", "switch", "this", "throw", "try", "typeof", "var",
    "void", "while", "with", "yield", "async", "await", "true", "false",
    "null", "undefined",
]
SH_KW = [
    "if", "then", "else", "elif", "fi", "for", "while", "do", "done", "case",
    "esac", "in", "function", "return", "export", "local", "readonly",
    "declare", "alias", "unalias", "source", "set", "unset", "echo", "printf",
    "cd", "ls", "rm", "cp", "mv", "mkdir", "cat", "grep", "sed", "awk",
]
C_KW = [
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if", "int",
    "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile",
    "while", "class", "namespace", "public", "private", "protected",
    "template", "typename", "using", "new", "delete", "this", "nullptr",
    "true", "false",
]
CSS_KW = [
    "color", "background", "margin", "padding", "border", "display", "position",
    "width", "height", "font", "font-size", "font-weight", "flex", "grid",
    "block", "inline", "none", "absolute", "relative", "fixed", "auto",
]


def _make_patterns(keywords, comment_pattern, string_patterns, number=True):
    pats = [
        ("sh_comment", re.compile(comment_pattern)),
    ]
    for i, sp in enumerate(string_patterns):
        pats.append((f"sh_string", re.compile(sp)))
    pats.append(("sh_keyword", _kw(keywords)))
    if number:
        pats.append(("sh_number", re.compile(r"\b\d+(\.\d+)?\b")))
    return pats


LANGUAGES = {
    "python": _make_patterns(
        PYTHON_KW,
        r"#[^\n]*",
        [r'"""[\s\S]*?"""', r"'''[\s\S]*?'''", r'"[^"\n]*"', r"'[^'\n]*'"],
    ),
    "javascript": _make_patterns(
        JS_KW,
        r"//[^\n]*|/\*[\s\S]*?\*/",
        [r'"[^"\n]*"', r"'[^'\n]*'", r"`[^`]*`"],
    ),
    "json": [
        ("sh_string", re.compile(r'"[^"\n]*"')),
        ("sh_number", re.compile(r"\b-?\d+(\.\d+)?([eE][+-]?\d+)?\b")),
        ("sh_keyword", re.compile(r"\b(true|false|null)\b")),
    ],
    "markdown": [
        ("sh_comment", re.compile(r"<!--[\s\S]*?-->")),
        ("sh_keyword", re.compile(r"^#{1,6} .*$", re.MULTILINE)),
        ("sh_string", re.compile(r"`[^`\n]*`")),
        ("sh_number", re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")),
        ("sh_func", re.compile(r"\[[^\]]+\]\([^\)]+\)")),
    ],
    "html": [
        ("sh_comment", re.compile(r"<!--[\s\S]*?-->")),
        ("sh_keyword", re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*")),
        ("sh_string", re.compile(r'"[^"]*"')),
        ("sh_number", re.compile(r"&[a-z]+;|&#\d+;")),
    ],
    "css": _make_patterns(
        CSS_KW, r"/\*[\s\S]*?\*/", [r'"[^"\n]*"', r"'[^'\n]*'"], number=True
    ),
    "shell": _make_patterns(
        SH_KW, r"#[^\n]*", [r'"[^"\n]*"', r"'[^'\n]*'"]
    ),
    "c": _make_patterns(
        C_KW, r"//[^\n]*|/\*[\s\S]*?\*/", [r'"[^"\n]*"', r"'[^'\n]*'"]
    ),
}


EXT_MAP = {
    ".py": "python", ".pyw": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".ts": "javascript", ".tsx": "javascript",
    ".json": "json",
    ".md": "markdown", ".markdown": "markdown",
    ".html": "html", ".htm": "html", ".xml": "html", ".svg": "html",
    ".css": "css", ".scss": "css", ".sass": "css",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "shell",
    ".c": "c", ".h": "c", ".cpp": "c", ".hpp": "c", ".cc": "c", ".cxx": "c",
    ".java": "c", ".kt": "c", ".kts": "c", ".cs": "c",
}


def detect_language(path):
    if path is None:
        return None
    ext = path.suffix.lower()
    return EXT_MAP.get(ext)


def highlight(text_widget, language, colors):
    """
    Apply syntax tags to a Tk Text widget.

    colors: dict of tag_name -> dict of options (foreground, font, etc.)
    """
    for tag in ("sh_keyword", "sh_string", "sh_comment", "sh_number", "sh_func"):
        text_widget.tag_remove(tag, "1.0", "end")

    if not language or language not in LANGUAGES:
        return

    # Configure tags first
    for tag, opts in colors.items():
        text_widget.tag_configure(tag, **opts)

    content = text_widget.get("1.0", "end-1c")
    if not content:
        return

    patterns = LANGUAGES[language]
    # Track character ranges already claimed to avoid overlap
    claimed = []

    def overlaps(start, end):
        for s, e in claimed:
            if start < e and end > s:
                return True
        return False

    for tag, pat in patterns:
        for m in pat.finditer(content):
            start, end = m.start(), m.end()
            if overlaps(start, end):
                continue
            claimed.append((start, end))
            # Convert char offset to line.col index
            line_start = content.count("\n", 0, start)
            col_start = start - (content.rfind("\n", 0, start) + 1)
            line_end = content.count("\n", 0, end)
            col_end = end - (content.rfind("\n", 0, end) + 1)
            text_widget.tag_add(tag, f"{line_start + 1}.{col_start}",
                                f"{line_end + 1}.{col_end}")
