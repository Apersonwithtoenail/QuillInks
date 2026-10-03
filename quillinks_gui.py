#!/usr/bin/env python3
"""Quillinks GUI — Tkinter-based editor with tabs."""

import json
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


# ==================== config ====================

def _config_dir():
    if os.environ.get("QUILLINKS_PORTABLE") == "1":
        return Path(__file__).parent / "config"
    return Path.home() / ".config" / "quillinks"


_CONFIG_DIR = _config_dir()
_RECENT_FILE = _CONFIG_DIR / "recent.json"
_SEARCH_HISTORY = _CONFIG_DIR / "search_history.json"
_SETTINGS_FILE = _CONFIG_DIR / "settings.json"
_MAX_RECENT = 10
_MAX_HISTORY = 20

DEFAULT_SETTINGS = {
    "font_family": "Monospace",
    "font_size": 11,
    "tab_width": 4,
    "use_spaces": True,
    "theme": "dark",
    "auto_indent": True,
    "bracket_match": True,
    "autopair": True,
    "show_ws": False,
    "wrap": False,
    "geometry": "1000x700",
    "ruler_col": 80,
    "show_ruler": False,
}


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path, obj):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2))
    except Exception:
        pass


def _load_settings():
    s = dict(DEFAULT_SETTINGS)
    s.update(_load_json(_SETTINGS_FILE, {}))
    return s


def _save_settings(s):
    _save_json(_SETTINGS_FILE, s)


def _load_recent():
    return _load_json(_RECENT_FILE, [])[:_MAX_RECENT]


def _save_recent(paths):
    _save_json(_RECENT_FILE, paths[:_MAX_RECENT])


def _push_recent(path):
    if not path:
        return
    s = str(Path(path).expanduser().resolve())
    items = _load_recent()
    if s in items:
        items.remove(s)
    items.insert(0, s)
    _save_recent(items)


def _load_search_history():
    return _load_json(_SEARCH_HISTORY, [])[:_MAX_HISTORY]


def _save_search_history(items):
    _save_json(_SEARCH_HISTORY, items[:_MAX_HISTORY])


def _push_search(term):
    if not term:
        return
    items = _load_search_history()
    if term in items:
        items.remove(term)
    items.insert(0, term)
    _save_search_history(items)


THEMES = {
    "dark":          ("#1e1e1e", "#d4d4d4", "#d4d4d4", "#264f78", "#252526", "#6a6a6a", "#2d2d2d", "#d4d4d4"),
    "light":         ("#ffffff", "#1e1e1e", "#1e1e1e", "#add6ff", "#f0f0f0", "#909090", "#e8e8e8", "#1e1e1e"),
    "high-contrast": ("#000000", "#ffff00", "#ffff00", "#005f00", "#1a1a00", "#ffff00", "#000000", "#ffff00"),
    "gruvbox":       ("#282828", "#ebdbb2", "#ebdbb2", "#458588", "#1d2021", "#928374", "#3c3836", "#ebdbb2"),
    "nord":          ("#2e3440", "#d8dee9", "#d8dee9", "#5e81ac", "#3b4252", "#7a8599", "#3b4252", "#d8dee9"),
    "solarized":     ("#002b36", "#839496", "#839496", "#073642", "#073642", "#586e75", "#073642", "#93a1a1"),
}


# ==================== Tab (buffer + widgets) ====================

class Tab:
    _counter = 0

    def __init__(self, notebook, app):
        Tab._counter += 1
        self.id = Tab._counter
        self.app = app
        self.path = None
        self.dirty = False
        self.line_ending = "LF"
        self.has_bom = False
        self.syncing = False

        self.frame = tk.Frame(notebook)
        self.gutter = tk.Text(
            self.frame, width=4, padx=4, takefocus=0, border=0,
            highlightthickness=0, state="disabled", wrap="none",
        )
        self.gutter.pack(side="left", fill="y")
        self.text = tk.Text(
            self.frame, wrap="none", undo=True,
            font=(app._font_family, app._font_size),
            tabs=(app._tab_width * 8,), padx=6,
            border=0, highlightthickness=0,
        )
        self.text.pack(side="left", fill="both", expand=True)

        # event wiring
        self.text.bind("<KeyPress>", app._on_keypress, add="+")
        self.text.bind("<Return>", app._on_return, add="+")
        self.text.bind("<KeyRelease>", app._on_keyrelease_brackets, add="+")
        self.text.bind("<<Modified>>", app._on_modified_for_tab, add="+")
        self.text.bind("<KeyRelease>", app._post_edit, add="+")
        self.text.bind("<ButtonRelease>", app._post_edit, add="+")
        self.text.bind("<Tab>", app._on_tab, add="+")
        self.text.bind("<Control-a>", app.select_all)
        self.text.bind("<Control-d>", app.duplicate_line)
        self.text.bind("<Control-slash>", app.toggle_comment)
        self.text.bind("<Tab>", app._on_tab, add="+")

    def title(self):
        name = self.path.name if self.path else "untitled"
        if self.dirty:
            name = "● " + name
        return name


# ==================== Main app ====================

class QuillinksGUI:
    def __init__(self, path=None):
        self.settings = _load_settings()

        self.root = tk.Tk()
        self.root.title("Quillinks")
        self.root.geometry(self.settings.get("geometry", "1000x700"))

        self.tabs = []
        self._font_size = int(self.settings.get("font_size", 11))
        self._font_family = self.settings.get("font_family", "Monospace")
        self._show_ws = bool(self.settings.get("show_ws", False))
        self._autopair = bool(self.settings.get("autopair", True))
        self._auto_indent = bool(self.settings.get("auto_indent", True))
        self._bracket_match = bool(self.settings.get("bracket_match", True))
        self._tab_width = int(self.settings.get("tab_width", 4))
        self._use_spaces = bool(self.settings.get("use_spaces", True))
        self._theme = self.settings.get("theme", "dark")
        self._read_only = False
        self._show_eol = False
        self._ensure_eof_newline = False
        self._show_ruler = bool(self.settings.get("show_ruler", False))
        self._ruler_col = int(self.settings.get("ruler_col", 80))

        self._build_menu()

        # Container
        outer = tk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_switch)

        self.status = tk.Label(self.root, anchor="w", padx=6)
        self.status.pack(fill="x", side="bottom")

        # Global binds
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-t>", lambda e: self.new_tab())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-w>", lambda e: self.close_tab())
        self.root.bind("<Control-q>", lambda e: self.on_close())
        self.root.bind("<Control-f>", lambda e: self.open_find())
        self.root.bind("<Control-h>", lambda e: self.open_find())
        self.root.bind("<Control-g>", self.goto_line)
        self.root.bind("<Control-equal>", lambda e: self.zoom(1))
        self.root.bind("<Control-plus>", lambda e: self.zoom(1))
        self.root.bind("<Control-minus>", lambda e: self.zoom(-1))
        self.root.bind("<Control-0>", lambda e: self.zoom_reset())
        self.root.bind("<Control-Shift-F>", lambda e: self.open_font_picker())
        self.root.bind("<Control-Shift-K>", self.delete_line)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<F5>", lambda e: self.insert_datetime())
        self.root.bind("<F1>", lambda e: self.show_shortcuts())
        self.root.bind("<Control-Prior>", lambda e: self._prev_tab())
        self.root.bind("<Control-Next>", lambda e: self._next_tab())

        # Open initial file or blank
        if path:
            self._open_path(Path(path))
        else:
            self.new_tab()

        self._apply_theme()
        self.toggle_wrap()
        self._apply_font()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(300, self._autosave_tick)

    # ==================== active tab helpers ====================

    def _active(self):
        idx = self.notebook.index(self.notebook.select())
        return self.tabs[idx]

    @property
    def text(self):
        return self._active().text

    @property
    def gutter(self):
        return self._active().gutter

    @property
    def path(self):
        return self._active().path

    @path.setter
    def path(self, val):
        self._active().path = val

    @property
    def dirty(self):
        return self._active().dirty

    @dirty.setter
    def dirty(self, val):
        self._active().dirty = val

    @property
    def _line_ending(self):
        return self._active().line_ending

    @_line_ending.setter
    def _line_ending(self, val):
        self._active().line_ending = val

    @property
    def _has_bom(self):
        return self._active().has_bom

    @_has_bom.setter
    def _has_bom(self, val):
        self._active().has_bom = val

    def _post_edit(self, event=None):
        self._update_gutter()
        self.update_status()
        if self._show_ws:
            self._paint_whitespace()

    # ==================== menu ====================

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Tab", accelerator="Ctrl+T", command=self.new_tab)
        file_menu.add_command(label="New File", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_tab)
        file_menu.add_separator()
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Revert", command=self.revert_file)
        file_menu.add_separator()
        le_menu = tk.Menu(file_menu, tearoff=0)
        for eol in ["LF", "CRLF", "CR"]:
            le_menu.add_command(label=eol, command=lambda x=eol: self.set_line_ending(x))
        file_menu.add_cascade(label="Line Endings", menu=le_menu)
        file_menu.add_checkbutton(label="Preserve BOM on save",
                                   variable=(bom_var := tk.BooleanVar(value=True)))
        file_menu.add_checkbutton(label="Ensure trailing newline at EOF",
                                   variable=(eof_var := tk.BooleanVar(value=False)),
                                   command=lambda: setattr(self, "_ensure_eof_newline", eof_var.get()))
        file_menu.add_checkbutton(label="Read-Only",
                                   variable=(ro_var := tk.BooleanVar(value=False)),
                                   command=lambda: self.toggle_read_only(ro_var.get()))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                              command=lambda: self.text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                              command=lambda: self.text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.text.event_generate("<<Paste>>"))
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="Duplicate Line", command=self.duplicate_line)
        edit_menu.add_command(label="Delete Line", command=self.delete_line)
        edit_menu.add_command(label="Toggle Comment", command=self.toggle_comment)
        edit_menu.add_separator()
        edit_menu.add_command(label="UPPERCASE", command=self.uppercase_sel)
        edit_menu.add_command(label="lowercase", command=self.lowercase_sel)
        edit_menu.add_command(label="Trim trailing whitespace", command=self.trim_ws)
        edit_menu.add_command(label="Sort lines", command=self.sort_lines)
        edit_menu.add_separator()
        edit_menu.add_command(label="Tabs → Spaces", command=self.convert_tabs_to_spaces)
        edit_menu.add_command(label="Spaces → Tabs", command=self.convert_spaces_to_tabs)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find & Replace…", accelerator="Ctrl+F", command=self.open_find)
        edit_menu.add_command(label="Go to line…", accelerator="Ctrl+G", command=self.goto_line)
        edit_menu.add_command(label="Insert Date/Time", accelerator="F5", command=self.insert_datetime)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        self.wrap_var = tk.BooleanVar(value=bool(self.settings.get("wrap", False)))
        view_menu.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_wrap)
        self.ws_var = tk.BooleanVar(value=self._show_ws)
        view_menu.add_checkbutton(label="Show Whitespace", variable=self.ws_var, command=self.toggle_whitespace)
        self.autopair_var = tk.BooleanVar(value=self._autopair)
        view_menu.add_checkbutton(label="Auto-pair brackets", variable=self.autopair_var, command=self.toggle_autopair)
        self.ai_var = tk.BooleanVar(value=self._auto_indent)
        view_menu.add_checkbutton(label="Auto-indent", variable=self.ai_var, command=self.toggle_auto_indent)
        self.bm_var = tk.BooleanVar(value=self._bracket_match)
        view_menu.add_checkbutton(label="Bracket matching", variable=self.bm_var, command=self.toggle_bracket_match)
        self.eol_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Show EOL markers", variable=self.eol_var, command=self.toggle_eol_markers)
        self.ruler_var = tk.BooleanVar(value=self._show_ruler)
        view_menu.add_checkbutton(label="Column Ruler", variable=self.ruler_var, command=self.toggle_ruler)
        view_menu.add_separator()
        tw_menu = tk.Menu(view_menu, tearoff=0)
        for w in [2, 4, 8]:
            tw_menu.add_command(label=f"{w} spaces", command=lambda x=w: self.set_tab_width(x))
        view_menu.add_cascade(label="Tab width", menu=tw_menu)
        view_menu.add_checkbutton(label="Use spaces for Tab",
                                   variable=(us_var := tk.BooleanVar(value=self._use_spaces)),
                                   command=lambda: self.set_use_spaces(us_var.get()))
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=lambda: self.zoom(1))
        view_menu.add_command(label="Zoom Out", command=lambda: self.zoom(-1))
        view_menu.add_command(label="Reset Zoom", command=self.zoom_reset)
        view_menu.add_separator()
        font_menu = tk.Menu(view_menu, tearoff=0)
        font_menu.add_command(label="Change Font Family…", command=self.open_font_picker)
        font_menu.add_separator()
        for name in ["Monospace", "DejaVu Sans Mono", "Courier New", "Liberation Mono",
                     "Ubuntu Mono", "Fira Code", "JetBrains Mono", "Cascadia Code",
                     "Menlo", "Consolas", "Source Code Pro", "Sans", "Serif"]:
            font_menu.add_command(label=name, command=lambda n=name: self.set_font_family(n))
        view_menu.add_cascade(label="Font", menu=font_menu)
        menubar.add_cascade(label="View", menu=view_menu)

        tab_menu = tk.Menu(menubar, tearoff=0)
        tab_menu.add_command(label="New Tab", accelerator="Ctrl+T", command=self.new_tab)
        tab_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_tab)
        tab_menu.add_separator()
        tab_menu.add_command(label="Next Tab", accelerator="Ctrl+PgDn", command=self._next_tab)
        tab_menu.add_command(label="Prev Tab", accelerator="Ctrl+PgUp", command=self._prev_tab)
        tab_menu.add_separator()
        for i in range(1, 10):
            tab_menu.add_command(label=f"Tab {i}", command=lambda n=i: self._goto_tab(n))
        menubar.add_cascade(label="Tab", menu=tab_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Plugin Manager…", command=self.open_plugin_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="Save Settings Now", command=self.save_settings)
        tools_menu.add_command(label="Open Config Folder", command=self._open_config_folder)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        theme_menu = tk.Menu(settings_menu, tearoff=0)
        for t in THEMES.keys():
            theme_menu.add_command(label=t, command=lambda x=t: self.set_theme(x))
        settings_menu.add_cascade(label="Theme", menu=theme_menu)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard Shortcuts", accelerator="F1", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self._rebuild_recent_menu()

    # ==================== tab management ====================

    def new_tab(self, path=None, focus=True):
        tab = Tab(self.notebook, self)
        self.tabs.append(tab)
        self.notebook.add(tab.frame, text=tab.title())
        if focus:
            self.notebook.select(tab.frame)
            tab.text.focus_set()
        if path:
            self._load_path_into(tab, path)
        self._apply_theme_to_tab(tab)
        self._update_gutter_for(tab)
        if not focus:
            self._refresh_tab_title(tab)

    def new_file(self):
        # Blank tab
        self.new_tab()

    def close_tab(self):
        idx = self.notebook.index(self.notebook.select())
        tab = self.tabs[idx]
        if tab.dirty:
            ans = messagebox.askyesnocancel("Unsaved changes",
                                              f"Save changes to {tab.title()}?")
            if ans is None:
                return
            if ans:
                self.notebook.select(tab.frame)
                if not self.save_file():
                    return
        self.tabs.pop(idx)
        self.notebook.forget(tab.frame)
        if not self.tabs:
            self.new_tab()
        self.update_title()
        self.update_status()

    def _next_tab(self):
        if len(self.tabs) < 2:
            return
        idx = self.notebook.index(self.notebook.select())
        self.notebook.select(self.tabs[(idx + 1) % len(self.tabs)].frame)

    def _prev_tab(self):
        if len(self.tabs) < 2:
            return
        idx = self.notebook.index(self.notebook.select())
        self.notebook.select(self.tabs[(idx - 1) % len(self.tabs)].frame)

    def _goto_tab(self, n):
        idx = n - 1
        if 0 <= idx < len(self.tabs):
            self.notebook.select(self.tabs[idx].frame)

    def _on_tab_switch(self, event=None):
        self.update_title()
        self.update_status()
        self._update_gutter()
        if self._show_ws:
            self._paint_whitespace()
        if self._show_eol:
            self.toggle_eol_markers()
        self._apply_ruler()

    def _refresh_tab_title(self, tab):
        try:
            idx = self.tabs.index(tab)
            self.notebook.tab(idx, text=tab.title())
        except ValueError:
            pass

    # ==================== gutter / ruler ====================

    def _update_gutter(self):
        tab = self._active()
        self._update_gutter_for(tab)

    def _update_gutter_for(self, tab):
        if tab.syncing:
            return
        tab.syncing = True
        try:
            content = tab.text.get("1.0", "end-1c")
            n = content.count("\n") + 1
            width = max(3, len(str(n)))
            lines = "\n".join(str(i).rjust(width) for i in range(1, n + 1))
            tab.gutter.config(state="normal")
            tab.gutter.delete("1.0", "end")
            tab.gutter.insert("1.0", lines)
            tab.gutter.config(state="disabled", width=width + 1)
            tab.gutter.yview_moveto(tab.text.yview()[0])
        finally:
            tab.syncing = False

    def toggle_ruler(self):
        self._show_ruler = self.ruler_var.get()
        self.settings["show_ruler"] = self._show_ruler
        self._apply_ruler()

    def _apply_ruler(self):
        tab = self._active()
        tab.text.tag_remove("ruler", "1.0", "end")
        if not self._show_ruler:
            return
        # A vertical line at column `_ruler_col`
        col = self._ruler_col
        tab.text.tag_configure("ruler", background="#3a2a2a")
        idx = "1.0"
        while True:
            line_end = tab.text.index(f"{idx} lineend")
            try:
                mark = f"{idx} +{col}c"
                if tab.text.compare(mark, "<", line_end):
                    tab.text.tag_add("ruler", mark, f"{mark}+1c")
            except tk.TclError:
                pass
            try:
                nxt = tab.text.index(f"{line_end}+1c")
            except tk.TclError:
                break
            if nxt == line_end:
                break
            idx = nxt
            if tab.text.compare(idx, ">=", "end-1c"):
                break

    def _on_text_scroll(self, first, last):
        tab = self._active()
        tab.gutter.yview_moveto(first)

    # ==================== theme ====================

    def _apply_theme(self):
        for tab in self.tabs:
            self._apply_theme_to_tab(tab)
        bg, fg, ins, sel, gbg, gfg, sbg, sfg = THEMES.get(self._theme, THEMES["dark"])
        self.status.config(bg=sbg, fg=sfg)

    def _apply_theme_to_tab(self, tab):
        bg, fg, ins, sel, gbg, gfg, sbg, sfg = THEMES.get(self._theme, THEMES["dark"])
        tab.text.config(bg=bg, fg=fg, insertbackground=ins, selectbackground=sel)
        tab.gutter.config(bg=gbg, fg=gfg)

    def set_theme(self, name):
        if name not in THEMES:
            return
        self._theme = name
        self.settings["theme"] = name
        self._apply_theme()
        self.status.config(text=f" Theme: {name}")

    # ==================== tab/space ====================

    def set_tab_width(self, w):
        self._tab_width = int(w)
        self.settings["tab_width"] = self._tab_width
        for tab in self.tabs:
            tab.text.config(tabs=(self._tab_width * 8,))
        self.status.config(text=f" Tab width: {self._tab_width}")

    def set_use_spaces(self, use):
        self._use_spaces = bool(use)
        self.settings["use_spaces"] = self._use_spaces

    def _on_tab(self, event=None):
        if self._read_only:
            return "break"
        if self._use_spaces:
            self.text.insert("insert", " " * self._tab_width)
        else:
            self.text.insert("insert", "\t")
        return "break"

    def convert_tabs_to_spaces(self):
        content = self.text.get("1.0", "end-1c")
        new = "\n".join(line.replace("\t", " " * self._tab_width) for line in content.split("\n"))
        self._replace_all_content(new)
        self.status.config(text=" Converted tabs → spaces")

    def convert_spaces_to_tabs(self):
        content = self.text.get("1.0", "end-1c")
        pat = re.compile(" " * self._tab_width)
        new = "\n".join(pat.sub("\t", line) for line in content.split("\n"))
        self._replace_all_content(new)
        self.status.config(text=" Converted spaces → tabs")

    def _replace_all_content(self, text):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.dirty = True
        self._update_gutter()
        self.update_status()

    # ==================== line endings / bom / eof ====================

    def set_line_ending(self, ending):
        if ending not in ("LF", "CRLF", "CR"):
            return
        self._line_ending = ending
        self.update_status()
        self.status.config(text=f" Line ending: {ending}")

    def toggle_read_only(self, flag):
        self._read_only = bool(flag)
        for tab in self.tabs:
            tab.text.config(state="disabled" if self._read_only else "normal")
        if not self._read_only:
            self.text.focus_set()
        self.update_title()
        self.update_status()

    def toggle_eol_markers(self):
        self._show_eol = self.eol_var.get()
        tab = self._active()
        tab.text.tag_remove("eol", "1.0", "end")
        if not self._show_eol:
            return
        tab.text.tag_configure("eol", foreground="#6a6a6a")
        idx = "1.0"
        while True:
            nxt = tab.text.search("\n", idx, stopindex="end")
            if not nxt:
                break
            tab.text.tag_add("eol", nxt, f"{nxt}+1c")
            idx = f"{nxt}+1c"

    def _encode_with_ending(self, text):
        if self._line_ending == "CRLF":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        elif self._line_ending == "CR":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
        else:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        if self._ensure_eof_newline and not text.endswith(("\n", "\r")):
            text += {"CRLF": "\r\n", "CR": "\r", "LF": "\n"}[self._line_ending]
        raw = text.encode("utf-8")
        if self._has_bom:
            raw = b"\xef\xbb\xbf" + raw
        return raw

    def _detect_bom(self, raw):
        if raw.startswith(b"\xef\xbb\xbf"):
            return True, raw[3:].decode("utf-8", errors="replace")
        return False, raw.decode("utf-8", errors="replace")

    # ==================== file ops ====================

    def open_file(self):
        p = filedialog.askopenfilename()
        if not p:
            return
        self._open_path(Path(p))

    def _load_path_into(self, tab, path):
        tab.path = Path(path).expanduser().resolve()
        raw = tab.path.read_bytes()
        if b"\r\n" in raw:
            tab.line_ending = "CRLF"
        elif b"\r" in raw and b"\n" not in raw:
            tab.line_ending = "CR"
        else:
            tab.line_ending = "LF"
        tab.has_bom, text = self._detect_bom(raw)
        tab.text.delete("1.0", "end")
        tab.text.insert("1.0", text)
        tab.dirty = False
        tab.text.edit_modified(False)
        self._refresh_tab_title(tab)
        if tab is self._active():
            self.update_title()
            self.update_status()

    def _open_path(self, path):
        # Reuse current tab if it's blank and untitled
        tab = self._active()
        if tab.path is None and not tab.text.get("1.0", "end-1c").strip():
            self._load_path_into(tab, path)
        else:
            self.new_tab(path=path)
        _push_recent(path)
        self._rebuild_recent_menu()

    def save_file(self):
        tab = self._active()
        if tab.path is None:
            return self.save_as()
        if self._read_only:
            messagebox.showinfo("Read-only", "File is read-only. Use Save As.")
            return self.save_as()
        try:
            raw = self._encode_with_ending(tab.text.get("1.0", "end-1c"))
            tab.path.write_bytes(raw)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return False
        tab.dirty = False
        tab.text.edit_modified(False)
        self._refresh_tab_title(tab)
        self.update_title()
        self.update_status()
        _push_recent(tab.path)
        self._rebuild_recent_menu()
        self.status.config(text=f" Saved {tab.path.name}")
        return True

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".md")
        if not p:
            return False
        self._active().path = Path(p)
        return self.save_file()

    def revert_file(self):
        tab = self._active()
        if not tab.path or not tab.path.exists():
            return
        if not messagebox.askyesno("Revert", f"Discard changes and reload {tab.path.name}?"):
            return
        self._load_path_into(tab, tab.path)

    def on_close(self):
        for tab in self.tabs:
            if tab.dirty:
                self.notebook.select(tab.frame)
                ans = messagebox.askyesnocancel("Unsaved changes",
                                                  f"Save changes to {tab.title()}?")
                if ans is None:
                    return
                if ans and not self.save_file():
                    return
        self.save_settings()
        self.root.destroy()

    # ==================== recent ====================

    def _rebuild_recent_menu(self):
        self.recent_menu.delete(0, "end")
        items = _load_recent()
        if not items:
            self.recent_menu.add_command(label="(empty)", state="disabled")
            return
        for path in items:
            label = path if len(path) < 60 else "…" + path[-57:]
            self.recent_menu.add_command(
                label=label, command=lambda p=path: self._open_from_recent(p))
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Clear Recent", command=self._clear_recent)

    def _open_from_recent(self, path):
        p = Path(path)
        if not p.exists():
            messagebox.showwarning("Missing file", f"Not found:\n{path}")
            items = _load_recent()
            if path in items:
                items.remove(path)
                _save_recent(items)
            self._rebuild_recent_menu()
            return
        self._open_path(p)

    def _clear_recent(self):
        _save_recent([])
        self._rebuild_recent_menu()

    # ==================== settings ====================

    def save_settings(self):
        try:
            self.settings["geometry"] = self.root.geometry()
        except tk.TclError:
            pass
        self.settings["font_family"] = self._font_family
        self.settings["font_size"] = self._font_size
        self.settings["tab_width"] = self._tab_width
        self.settings["use_spaces"] = self._use_spaces
        self.settings["theme"] = self._theme
        self.settings["auto_indent"] = self._auto_indent
        self.settings["bracket_match"] = self._bracket_match
        self.settings["autopair"] = self._autopair
        self.settings["show_ws"] = self._show_ws
        self.settings["show_ruler"] = self._show_ruler
        self.settings["wrap"] = bool(self.wrap_var.get()) if hasattr(self, "wrap_var") else False
        _save_settings(self.settings)

    def _open_config_folder(self):
        folder = str(_CONFIG_DIR)
        try:
            import subprocess
            subprocess.Popen(["xdg-open", folder])
        except Exception:
            messagebox.showinfo("Config folder", folder)

    # ==================== edit ops ====================

    def insert_datetime(self):
        self.text.insert("insert", datetime.now().strftime("%Y-%m-%d %H:%M"))

    def toggle_wrap(self):
        wrap_mode = "word" if self.wrap_var.get() else "none"
        for tab in self.tabs:
            tab.text.config(wrap=wrap_mode)

    def select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        return "break"

    def duplicate_line(self, event=None):
        try:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
            line = self.text.get(start, end)
            self.text.insert(end, "\n" + line)
        except tk.TclError:
            pass
        return "break"

    def delete_line(self, event=None):
        try:
            self.text.delete("insert linestart", "insert lineend +1c")
        except tk.TclError:
            pass
        return "break"

    def toggle_comment(self, event=None):
        try:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
            line = self.text.get(start, end)
            if line.lstrip().startswith("#"):
                i = line.find("#")
                new = line[:i] + line[i+1:].lstrip(" ")
                self.text.delete(start, end)
                self.text.insert(start, new)
            else:
                self.text.insert(start, "# ")
        except tk.TclError:
            pass
        return "break"

    def uppercase_sel(self):
        try:
            sel = self.text.get("sel.first", "sel.last")
            self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", sel.upper())
        except tk.TclError:
            pass

    def lowercase_sel(self):
        try:
            sel = self.text.get("sel.first", "sel.last")
            self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", sel.lower())
        except tk.TclError:
            pass

    def trim_ws(self):
        content = self.text.get("1.0", "end-1c")
        new = "\n".join(l.rstrip() for l in content.split("\n"))
        self._replace_all_content(new)
        self.status.config(text=" Trimmed trailing whitespace")

    def sort_lines(self):
        try:
            sel = self.text.get("sel.first", "sel.last")
            has_sel = True
        except tk.TclError:
            sel = self.text.get("1.0", "end-1c")
            has_sel = False
        sorted_text = "\n".join(sorted(sel.split("\n")))
        if has_sel:
            self.text.delete("sel.first", "sel.last")
            self.text.insert("insert", sorted_text)
        else:
            self._replace_all_content(sorted_text)
        self.status.config(text=" Sorted lines")

    def goto_line(self, event=None):
        win = tk.Toplevel(self.root)
        win.title("Go to line")
        win.geometry("260x90")
        win.transient(self.root)
        tk.Label(win, text="Line:").pack(side="left", padx=8)
        entry = tk.Entry(win, width=12)
        entry.pack(side="left", padx=4)
        entry.focus()

        def go():
            try:
                n = int(entry.get())
                self.text.mark_set("insert", f"{n}.0")
                self.text.see(f"{n}.0")
            except ValueError:
                pass
            win.destroy()

        entry.bind("<Return>", lambda e: go())
        tk.Button(win, text="Go", command=go).pack(side="left", padx=4)
        return "break"

    # ==================== state ====================

    def _on_modified_for_tab(self, event):
        tab = self._active()
        if tab.text.edit_modified():
            tab.dirty = True
            self._refresh_tab_title(tab)
            self.update_title()

    def on_modified(self, event=None):
        pass

    def update_title(self):
        tab = self._active()
        name = tab.path.name if tab.path else "untitled"
        star = " ●" if tab.dirty else ""
        ro = " [RO]" if self._read_only else ""
        self.root.title(f"{name}{star}{ro} — Quillinks")

    def _has_trailing_newline(self):
        content = self.text.get("1.0", "end-1c")
        if not content:
            return True
        return content.endswith("\n")

    def update_status(self, event=None):
        try:
            row, col = self.text.index("insert").split(".")
        except tk.TclError:
            return
        tab = self._active()
        state = "RO" if self._read_only else ("saved" if not tab.dirty else "modified")
        eol = tab.line_ending
        bom = " · BOM" if tab.has_bom else ""
        eof = "" if self._has_trailing_newline() else " · [no-eol]"
        ws = " · ws" if self._show_ws else ""
        tw = f" · tab={self._tab_width}{'sp' if self._use_spaces else 'tab'}"
        tnum = f" · tab {self.notebook.index(self.notebook.select())+1}/{len(self.tabs)}"
        self.status.config(
            text=f" Ln {row}, Col {int(col)+1}  ·  {state}  ·  {eol}{bom}{eof}{ws}{tw}{tnum}  ·  {self._theme}"
        )

    # ==================== auto-indent ====================

    def toggle_auto_indent(self):
        self._auto_indent = self.ai_var.get()

    def _on_return(self, event=None):
        if not self._auto_indent or self._read_only:
            return None
        try:
            line_start = self.text.index("insert linestart")
            cursor = self.text.index("insert")
            line = self.text.get(line_start, cursor)
            indent = ""
            for ch in line:
                if ch in " \t":
                    indent += ch
                else:
                    break
            self.text.insert("insert", "\n" + indent)
            return "break"
        except tk.TclError:
            return None

    # ==================== bracket matching ====================

    def toggle_bracket_match(self):
        self._bracket_match = self.bm_var.get()
        if not self._bracket_match:
            for tab in self.tabs:
                tab.text.tag_remove("brk", "1.0", "end")

    def _on_keyrelease_brackets(self, event=None):
        if not self._bracket_match:
            return
        tab = self._active()
        tab.text.tag_remove("brk", "1.0", "end")
        tab.text.tag_configure("brk", background="#4a4a20", foreground="#ffffff")
        pairs = {"(": ")", "[": "]", "{": "}"}
        rev = {v: k for k, v in pairs.items()}
        cur_idx = tab.text.index("insert")
        prev_idx = tab.text.index("insert-1c")
        prev_ch = tab.text.get(prev_idx, cur_idx)
        cur_ch = tab.text.get(cur_idx, f"{cur_idx}+1c")
        for idx, ch in [(prev_idx, prev_ch), (cur_idx, cur_ch)]:
            if ch in pairs:
                match = self._scan_forward(f"{idx}+1c", pairs[ch], ch)
                if match:
                    tab.text.tag_add("brk", idx, f"{idx}+1c")
                    tab.text.tag_add("brk", match, f"{match}+1c")
                    return
            elif ch in rev:
                match = self._scan_backward(f"{idx}-1c", rev[ch], ch)
                if match:
                    tab.text.tag_add("brk", idx, f"{idx}+1c")
                    tab.text.tag_add("brk", match, f"{match}+1c")
                    return

    def _scan_forward(self, start, close_ch, open_ch):
        depth = 1
        idx = start
        for _ in range(10000):
            ch = self.text.get(idx, f"{idx}+1c")
            if not ch:
                return None
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return idx
            try:
                nxt = self.text.index(f"{idx}+1c")
            except tk.TclError:
                return None
            if nxt == idx:
                return None
            idx = nxt
        return None

    def _scan_backward(self, start, open_ch, close_ch):
        depth = 1
        idx = start
        for _ in range(10000):
            ch = self.text.get(idx, f"{idx}+1c")
            if not ch:
                return None
            if ch == close_ch:
                depth += 1
            elif ch == open_ch:
                depth -= 1
                if depth == 0:
                    return idx
            try:
                prev = self.text.index(f"{idx}-1c")
            except tk.TclError:
                return None
            if prev == idx:
                return None
            idx = prev
        return None

    # ==================== auto-pairing ====================

    def toggle_autopair(self):
        self._autopair = self.autopair_var.get()

    def _on_keypress(self, event):
        if not self._autopair or self._read_only:
            return None
        pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        ch = event.char
        if ch not in pairs:
            return None
        closing = pairs[ch]
        next_ch = self.text.get("insert", "insert+1c")
        if next_ch == closing:
            return None
        try:
            sel_start = self.text.index("sel.first")
            sel_end = self.text.index("sel.last")
            selected = self.text.get(sel_start, sel_end)
            self.text.delete(sel_start, sel_end)
            self.text.insert(sel_start, ch + selected + closing)
            return "break"
        except tk.TclError:
            pass
        self.text.insert("insert", ch + closing)
        self.text.mark_set("insert", "insert-1c")
        return "break"

    # ==================== whitespace ====================

    def toggle_whitespace(self):
        self._show_ws = self.ws_var.get()
        for tab in self.tabs:
            if self._show_ws:
                tab.text.tag_configure("ws_space", background="#3a3a1a")
                tab.text.tag_configure("ws_tab", background="#3a1a1a")
            else:
                tab.text.tag_remove("ws_space", "1.0", "end")
                tab.text.tag_remove("ws_tab", "1.0", "end")
        if self._show_ws:
            self._paint_whitespace()

    def _paint_whitespace(self):
        tab = self._active()
        tab.text.tag_remove("ws_space", "1.0", "end")
        tab.text.tag_remove("ws_tab", "1.0", "end")
        if not self._show_ws:
            return
        content = tab.text.get("1.0", "end-1c")
        idx = "1.0"
        for ch in content:
            if ch == " ":
                tab.text.tag_add("ws_space", idx, f"{idx}+1c")
            elif ch == "\t":
                tab.text.tag_add("ws_tab", idx, f"{idx}+1c")
            idx = f"{idx}+1c"

    # ==================== find ====================

    def open_find(self):
        win = tk.Toplevel(self.root)
        win.title("Find & Replace")
        win.geometry("520x300")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")
        win.protocol("WM_DELETE_WINDOW", lambda: (self._clear_highlights(), win.destroy()))

        tk.Label(win, text="Find:", bg="#1e1e1e", fg="#d4d4d4").grid(
            row=0, column=0, sticky="e", padx=8, pady=6)
        find_var = tk.StringVar()
        find_combo = ttk.Combobox(
            win, textvariable=find_var, width=34,
            values=_load_search_history(),
        )
        find_combo.grid(row=0, column=1, columnspan=2, padx=4, pady=6, sticky="we")
        find_combo.focus()

        tk.Label(win, text="Replace:", bg="#1e1e1e", fg="#d4d4d4").grid(
            row=1, column=0, sticky="e", padx=8, pady=6)
        repl_var = tk.StringVar()
        tk.Entry(win, textvariable=repl_var, width=34,
                 bg="#252526", fg="#d4d4d4", insertbackground="#d4d4d4").grid(
            row=1, column=1, columnspan=2, padx=4, pady=6, sticky="we")

        case_var = tk.BooleanVar(value=False)
        whole_var = tk.BooleanVar(value=False)
        highlight_var = tk.BooleanVar(value=True)

        opts = tk.Frame(win, bg="#1e1e1e")
        opts.grid(row=2, column=0, columnspan=3, pady=4, sticky="w", padx=8)
        for label, var in [("Case sensitive", case_var),
                            ("Whole word", whole_var),
                            ("Highlight all", highlight_var)]:
            tk.Checkbutton(
                opts, text=label, variable=var,
                bg="#1e1e1e", fg="#d4d4d4", selectcolor="#2d2d30",
                activebackground="#1e1e1e", activeforeground="#d4d4d4",
            ).pack(side="left", padx=6)

        count_label = tk.Label(win, text="", bg="#1e1e1e", fg="#4ec9b0", font=("Sans", 9))
        count_label.grid(row=3, column=0, columnspan=3, pady=(4, 8))

        def do_highlight(*args):
            self._clear_highlights()
            term = find_var.get()
            if not term:
                count_label.config(text="")
                return
            count = self._highlight_matches(term, case_var.get(), whole_var.get(),
                                             highlight_var.get())
            count_label.config(text="No matches" if count == 0
                               else f"{count} match{'es' if count != 1 else ''}")

        def find_next():
            term = find_var.get()
            if not term:
                return
            _push_search(term)
            find_combo.config(values=_load_search_history())
            self.text.tag_remove("match", "1.0", "end")
            idx = "1.0"
            case = case_var.get()
            whole = whole_var.get()
            while True:
                idx = self.text.search(term, idx, nocase=not case, stopindex="end")
                if not idx:
                    break
                end = f"{idx}+{len(term)}c"
                if whole:
                    before = self.text.get(f"{idx}-1c", idx)
                    after = self.text.get(end, f"{end}+1c")
                    if before and (before.isalnum() or before == "_"):
                        idx = end
                        continue
                    if after and (after.isalnum() or after == "_"):
                        idx = end
                        continue
                self.text.tag_add("match", idx, end)
                idx = end
            self.text.tag_config("match", background="#264f78")
            ranges = self.text.tag_ranges("match")
            if ranges:
                self.text.mark_set("insert", ranges[0])
                self.text.see(ranges[0])

        def replace_all():
            term = find_var.get()
            repl = repl_var.get()
            if not term:
                return
            _push_search(term)
            find_combo.config(values=_load_search_history())
            content = self.text.get("1.0", "end-1c")
            if case_var.get():
                count = content.count(term)
                new_content = content.replace(term, repl)
            else:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                count = len(pattern.findall(content))
                new_content = pattern.sub(repl, content)
            if count == 0:
                count_label.config(text="No matches")
                return
            self._replace_all_content(new_content)
            count_label.config(text=f"Replaced {count}")
            do_highlight()

        btns = tk.Frame(win, bg="#1e1e1e")
        btns.grid(row=4, column=0, columnspan=3, pady=8)
        tk.Button(btns, text="Find Next", command=find_next, width=12).pack(side="left", padx=6)
        tk.Button(btns, text="Replace All", command=replace_all, width=12).pack(side="left", padx=6)
        tk.Button(btns, text="Close",
                  command=lambda: (self._clear_highlights(), win.destroy()),
                  width=12).pack(side="left", padx=6)

        find_var.trace_add("write", do_highlight)
        case_var.trace_add("write", do_highlight)
        whole_var.trace_add("write", do_highlight)

    def _clear_highlights(self):
        for tab in self.tabs:
            tab.text.tag_remove("hl", "1.0", "end")

    def _highlight_matches(self, term, case, whole, enabled=True):
        self._clear_highlights()
        if not enabled or not term:
            return 0
        count = 0
        idx = "1.0"
        while True:
            idx = self.text.search(term, idx, nocase=not case, stopindex="end")
            if not idx:
                break
            end = f"{idx}+{len(term)}c"
            ok = True
            if whole:
                before = self.text.get(f"{idx}-1c", idx)
                after = self.text.get(end, f"{end}+1c")
                if before and (before.isalnum() or before == "_"):
                    ok = False
                if after and (after.isalnum() or after == "_"):
                    ok = False
            if ok:
                self.text.tag_add("hl", idx, end)
                count += 1
            idx = end
        self.text.tag_config("hl", background="#5a4a1a")
        return count

    # ==================== zoom / font ====================

    def _apply_font(self):
        for tab in self.tabs:
            tab.text.config(font=(self._font_family, self._font_size))
            tab.gutter.config(font=(self._font_family, self._font_size))

    def zoom(self, delta):
        self._font_size = max(7, min(28, self._font_size + delta))
        self._apply_font()
        self.status.config(text=f" Font: {self._font_family} {self._font_size}pt")

    def zoom_reset(self):
        self._font_size = 11
        self._apply_font()
        self.status.config(text=" Zoom reset")

    def set_font_family(self, family):
        self._font_family = family
        self._apply_font()
        self.status.config(text=f" Font: {family} {self._font_size}pt")

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))
        return "break"

    def open_font_picker(self):
        try:
            from plugins.font_picker import open_font_picker
            open_font_picker(self.root, self._font_family, self.set_font_family)
        except ImportError:
            messagebox.showinfo(
                "Font picker unavailable",
                "plugins/font_picker.py not found.\nUsing View → Font menu instead."
            )

    # ==================== plugins ====================

    def open_plugin_manager(self):
        try:
            from plugins.plugin_manager import open_plugin_manager
            open_plugin_manager(self.root, on_change=self._on_plugins_changed)
        except ImportError as e:
            messagebox.showerror("Plugin Manager", f"Not available: {e}")

    def _on_plugins_changed(self):
        try:
            from plugins.font_picker import open_font_picker  # noqa
            self.status.config(text=" Font picker plugin ready")
        except ImportError:
            pass

    # ==================== help ====================

    def show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.geometry("540x700")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")

        tk.Label(win, text="Keyboard Shortcuts", bg="#1e1e1e", fg="#d4d4d4",
                 font=("Sans", 13, "bold")).pack(pady=(12, 8))

        frame = tk.Frame(win, bg="#1e1e1e")
        frame.pack(fill="both", expand=True, padx=20)

        rows = [
            ("Tabs", ""),
            ("Ctrl+T", "New tab"),
            ("Ctrl+W", "Close tab"),
            ("Ctrl+PgUp/PgDn", "Prev / next tab"),
            ("", ""),
            ("File", ""),
            ("Ctrl+N", "New tab"),
            ("Ctrl+O", "Open file"),
            ("Ctrl+S", "Save"),
            ("Ctrl+Shift+S", "Save As"),
            ("Ctrl+Q", "Quit"),
            ("", ""),
            ("Edit", ""),
            ("Ctrl+A", "Select all"),
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Ctrl+D", "Duplicate line"),
            ("Ctrl+Shift+K", "Delete line"),
            ("Ctrl+/", "Toggle comment"),
            ("Tab", "Insert tab/spaces"),
            ("", ""),
            ("Find", ""),
            ("Ctrl+F or Ctrl+H", "Find & Replace"),
            ("Ctrl+G", "Go to line"),
            ("", ""),
            ("View", ""),
            ("Ctrl++ / Ctrl+-", "Zoom in / out"),
            ("Ctrl+0", "Reset zoom"),
            ("F11", "Fullscreen"),
            ("Ctrl+Shift+F", "Font picker"),
            ("View → Show Whitespace", "Highlight spaces/tabs"),
            ("View → Show EOL", "Show line endings"),
            ("View → Column Ruler", "Vertical line at col 80"),
            ("", ""),
            ("Settings", ""),
            ("Settings → Theme", "Change theme"),
            ("File → Line Endings", "Convert LF/CRLF/CR"),
            ("File → Read-Only", "Toggle read-only"),
            ("", ""),
            ("Misc", ""),
            ("F5", "Insert date/time"),
            ("F1", "This dialog"),
        ]
        for key, desc in rows:
            if not key and not desc:
                tk.Frame(frame, height=6, bg="#1e1e1e").pack()
                continue
            if not desc:
                tk.Label(frame, text=key, bg="#1e1e1e", fg="#4ec9b0",
                         font=("Sans", 11, "bold"), anchor="w").pack(fill="x", pady=(6, 2))
                continue
            row = tk.Frame(frame, bg="#1e1e1e")
            row.pack(fill="x")
            tk.Label(row, text=key, bg="#1e1e1e", fg="#dcdcaa",
                     font=("Monospace", 10), width=24, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg="#1e1e1e", fg="#d4d4d4",
                     font=("Sans", 10), anchor="w").pack(side="left")

        tk.Button(win, text="Close", command=win.destroy).pack(pady=12)

    def show_about(self):
        messagebox.showinfo(
            "About Quillinks",
            "Quillinks — a modern terminal + GUI text editor.\n\n"
            "Built with Python, Textual, and Tkinter.\n"
            "github.com/Apersonwithtoenail/QuillInks"
        )

    # ==================== autosave ====================

    def _autosave_tick(self):
        for tab in self.tabs:
            if tab.dirty and tab.path is not None and not self._read_only:
                try:
                    raw = self._encode_with_ending(tab.text.get("1.0", "end-1c"))
                    tab.path.write_bytes(raw)
                    tab.dirty = False
                    tab.text.edit_modified(False)
                    self._refresh_tab_title(tab)
                except Exception:
                    pass
        self.update_title()
        self.update_status()
        self.root.after(5000, self._autosave_tick)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    app = QuillinksGUI(arg)
    app.root.mainloop()
