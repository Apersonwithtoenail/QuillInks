#!/usr/bin/env python3
"""Quillinks GUI — Tkinter editor with tabs, splits, path completion."""

import json
import os
import platform
import re
import sys
import syntax_highlight
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


# ==================== config ====================

def _config_dir():
    # Portable: env var OR a portable.flag file next to the script
    if os.environ.get("QUILLINKS_PORTABLE") == "1":
        return Path(__file__).parent / "config"
    if (Path(__file__).parent / "portable.flag").exists():
        return Path(__file__).parent / "config"

    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Quillinks"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Quillinks"
    return Path.home() / ".config" / "quillinks"


def _default_font():
    system = platform.system()
    if system == "Windows":
        return "Consolas"
    if system == "Darwin":
        return "Menlo"
    return "Monospace"


def _font_candidates():
    system = platform.system()
    if system == "Windows":
        priority = ["Consolas", "Cascadia Code", "Courier New"]
    elif system == "Darwin":
        priority = ["Menlo", "Monaco", "Courier"]
    else:
        priority = ["Monospace", "DejaVu Sans Mono", "Ubuntu Mono"]
    common = ["Monospace", "DejaVu Sans Mono", "Liberation Mono", "Fira Code",
              "JetBrains Mono", "Cascadia Code", "Source Code Pro",
              "Consolas", "Courier New", "Menlo", "Monaco", "Courier",
              "Sans", "Serif", "Helvetica", "Arial"]
    out = []
    for name in priority + common:
        if name not in out:
            out.append(name)
    return out


def _open_folder(path):
    system = platform.system()
    try:
        import subprocess
        if system == "Windows":
            os.startfile(str(path))  # noqa: S606
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


_CONFIG_DIR = _config_dir()
_RECENT_FILE = _CONFIG_DIR / "recent.json"
_SEARCH_HISTORY = _CONFIG_DIR / "search_history.json"
_SETTINGS_FILE = _CONFIG_DIR / "settings.json"
_MAX_RECENT = 10
_MAX_HISTORY = 20

DEFAULT_SETTINGS = {
    "font_family": None,  # resolved to _default_font() below "font_size": 11,
    "tab_width": 4, "use_spaces": True, "theme": "dark",
    "auto_indent": True, "bracket_match": True, "autopair": True,
    "show_ws": False, "wrap": False,
    "geometry": "1050x720", "ruler_col": 80, "show_ruler": False,
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
    s = dict(DEFAULT_SETTINGS); s.update(_load_json(_SETTINGS_FILE, {}))
    if not s.get("font_family"):
        s["font_family"] = _default_font()
    return s


def _save_settings(s): _save_json(_SETTINGS_FILE, s)


def _load_recent(): return _load_json(_RECENT_FILE, [])[:_MAX_RECENT]
def _save_recent(paths): _save_json(_RECENT_FILE, paths[:_MAX_RECENT])


def _push_recent(path):
    if not path: return
    s = str(Path(path).expanduser().resolve())
    items = _load_recent()
    if s in items: items.remove(s)
    items.insert(0, s); _save_recent(items)


def _load_search_history(): return _load_json(_SEARCH_HISTORY, [])[:_MAX_HISTORY]
def _save_search_history(items): _save_json(_SEARCH_HISTORY, items[:_MAX_HISTORY])


def _push_search(term):
    if not term: return
    items = _load_search_history()
    if term in items: items.remove(term)
    items.insert(0, term); _save_search_history(items)


THEMES = {
    "dark":          ("#1e1e1e", "#d4d4d4", "#d4d4d4", "#264f78", "#252526", "#6a6a6a", "#2d2d2d", "#d4d4d4"),
    "light":         ("#ffffff", "#1e1e1e", "#1e1e1e", "#add6ff", "#f0f0f0", "#909090", "#e8e8e8", "#1e1e1e"),
    "high-contrast": ("#000000", "#ffff00", "#ffff00", "#005f00", "#1a1a00", "#ffff00", "#000000", "#ffff00"),
    "gruvbox":       ("#282828", "#ebdbb2", "#ebdbb2", "#458588", "#1d2021", "#928374", "#3c3836", "#ebdbb2"),
    "nord":          ("#2e3440", "#d8dee9", "#d8dee9", "#5e81ac", "#3b4252", "#7a8599", "#3b4252", "#d8dee9"),
    "solarized":     ("#002b36", "#839496", "#839496", "#073642", "#073642", "#586e75", "#073642", "#93a1a1"),    "monokai":         ("#272822", "#f8f8f2", "#f8f8f2", "#49483e", "#1e1f1c", "#75715e", "#1e1f1c", "#f8f8f2"),
    "dracula":         ("#282a36", "#f8f8f2", "#f8f8f2", "#44475a", "#21222c", "#6272a4", "#21222c", "#f8f8f2"),
    "one-dark":        ("#282c34", "#abb2bf", "#abb2bf", "#3e4451", "#21252b", "#5c6370", "#21252b", "#abb2bf"),
    "tokyo-night":     ("#1a1b26", "#c0caf5", "#c0caf5", "#33467c", "#16161e", "#565f89", "#16161e", "#c0caf5"),
    "catppuccin":      ("#1e1e2e", "#cdd6f4", "#cdd6f4", "#585b70", "#181825", "#7f849c", "#181825", "#cdd6f4"),
    "catppuccin-latte":("#eff1f5", "#4c4f69", "#4c4f69", "#bcc0cc", "#e6e9ef", "#9ca0b0", "#e6e9ef", "#4c4f69"),
    "github-dark":     ("#0d1117", "#c9d1d9", "#c9d1d9", "#264f78", "#010409", "#6e7681", "#010409", "#c9d1d9"),
    "github-light":    ("#ffffff", "#24292f", "#24292f", "#b6d7ff", "#f6f8fa", "#8c959f", "#f6f8fa", "#24292f"),
    "ayu-dark":        ("#0d1017", "#bfbdb6", "#bfbdb6", "#334155", "#0b0e14", "#565b66", "#0b0e14", "#bfbdb6"),
    "night-owl":       ("#011627", "#d6deeb", "#d6deeb", "#1d3b53", "#01111d", "#637777", "#01111d", "#d6deeb"),
    "material":        ("#263238", "#eeffff", "#eeffff", "#314549", "#1e272c", "#546e7a", "#1e272c", "#eeffff"),
    "solarized-light": ("#fdf6e3", "#657b83", "#657b83", "#eee8d5", "#f5efdc", "#93a1a1", "#f5efdc", "#657b83"),
    "everforest":      ("#2d353b", "#d3c6aa", "#d3c6aa", "#475258", "#232a2e", "#7a8478", "#232a2e", "#d3c6aa"),
    "rose-pine":       ("#191724", "#e0def4", "#e0def4", "#403d52", "#1f1d2e", "#6e6a86", "#1f1d2e", "#e0def4"),
    "monokai":         ("#272822", "#f8f8f2", "#f8f8f2", "#49483e", "#1e1f1c", "#75715e", "#1e1f1c", "#f8f8f2"),
    "dracula":         ("#282a36", "#f8f8f2", "#f8f8f2", "#44475a", "#21222c", "#6272a4", "#21222c", "#f8f8f2"),
    "one-dark":        ("#282c34", "#abb2bf", "#abb2bf", "#3e4451", "#21252b", "#5c6370", "#21252b", "#abb2bf"),
    "tokyo-night":     ("#1a1b26", "#c0caf5", "#c0caf5", "#33467c", "#16161e", "#565f89", "#16161e", "#c0caf5"),
    "catppuccin":      ("#1e1e2e", "#cdd6f4", "#cdd6f4", "#585b70", "#181825", "#7f849c", "#181825", "#cdd6f4"),
    "catppuccin-latte":("#eff1f5", "#4c4f69", "#4c4f69", "#bcc0cc", "#e6e9ef", "#9ca0b0", "#e6e9ef", "#4c4f69"),
    "github-dark":     ("#0d1117", "#c9d1d9", "#c9d1d9", "#264f78", "#010409", "#6e7681", "#010409", "#c9d1d9"),
    "github-light":    ("#ffffff", "#24292f", "#24292f", "#b6d7ff", "#f6f8fa", "#8c959f", "#f6f8fa", "#24292f"),
    "ayu-dark":        ("#0d1017", "#bfbdb6", "#bfbdb6", "#334155", "#0b0e14", "#565b66", "#0b0e14", "#bfbdb6"),
    "night-owl":       ("#011627", "#d6deeb", "#d6deeb", "#1d3b53", "#01111d", "#637777", "#01111d", "#d6deeb"),
    "material":        ("#263238", "#eeffff", "#eeffff", "#314549", "#1e272c", "#546e7a", "#1e272c", "#eeffff"),
    "solarized-light": ("#fdf6e3", "#657b83", "#657b83", "#eee8d5", "#f5efdc", "#93a1a1", "#f5efdc", "#657b83"),
    "everforest":      ("#2d353b", "#d3c6aa", "#d3c6aa", "#475258", "#232a2e", "#7a8478", "#232a2e", "#d3c6aa"),
    "rose-pine":       ("#191724", "#e0def4", "#e0def4", "#403d52", "#1f1d2e", "#6e6a86", "#1f1d2e", "#e0def4"),

    "vintage-brown":   ("#2b2118", "#e8d5b7", "#d4a373", "#6b4423", "#1f1810", "#8b7355", "#3d2b1f", "#e8d5b7"),
}

SYNTAX_COLORS = {
    "dark":           ("#c586c0", "#ce9178", "#6a9955", "#b5cea8", "#dcdcaa"),
    "light":          ("#af00db", "#a31515", "#008000", "#098658", "#795e26"),
    "high-contrast":  ("#ff00ff", "#00ffff", "#00ff00", "#ffff00", "#ff8000"),
    "gruvbox":        ("#fb4934", "#b8bb26", "#928374", "#d3869b", "#fabd2f"),
    "nord":           ("#81a1c1", "#a3be8c", "#616e88", "#b48ead", "#ebcb8b"),
    "solarized":      ("#859900", "#2aa198", "#586e75", "#d33682", "#b58900"),    "monokai":         ("#f92672", "#e6db74", "#75715e", "#ae81ff", "#a6e22e"),
    "dracula":         ("#ff79c6", "#f1fa8c", "#6272a4", "#bd93f9", "#50fa7b"),
    "one-dark":        ("#c678dd", "#98c379", "#5c6370", "#d19a66", "#61afef"),
    "tokyo-night":     ("#bb9af7", "#9ece6a", "#565f89", "#ff9e64", "#7aa2f7"),
    "catppuccin":      ("#cba6f7", "#a6e3a1", "#6c7086", "#fab387", "#89b4fa"),
    "catppuccin-latte":("#8839ef", "#40a02b", "#9ca0b0", "#fe640b", "#1e66f5"),
    "github-dark":     ("#ff7b72", "#a5d6ff", "#8b949e", "#79c0ff", "#d2a8ff"),
    "github-light":    ("#cf222e", "#0a3069", "#6e7781", "#0550ae", "#8250df"),
    "ayu-dark":        ("#ff8f40", "#aad94c", "#acb6bf", "#d2a6ff", "#59c2ff"),
    "night-owl":       ("#c792ea", "#ecc48d", "#637777", "#f78c6c", "#82aaff"),
    "material":        ("#c792ea", "#c3e88d", "#546e7a", "#f78c6c", "#82aaff"),
    "solarized-light": ("#859900", "#2aa198", "#93a1a1", "#d33682", "#b58900"),
    "everforest":      ("#e67e80", "#a7c080", "#7a8478", "#d699b6", "#dbbc7f"),
    "rose-pine":       ("#c4a7e7", "#f6c177", "#6e6a86", "#eb6f92", "#9ccfd8"),

    "vintage-brown":   ("#d4a373", "#9b7653", "#7a6a55", "#b8956a", "#c9a961"),
}

# Extra UI styling for themes that change the whole mood.
# Only "vintage-brown" is customized; everything else uses defaults.
UI_EXTRAS = {
    "vintage-brown": {
        "toolbar_bg":     "#3d2b1f",
        "menubar_bg":     "#3d2b1f",
        "menubar_fg":     "#e8d5b7",
        "menubar_hover":  "#5a3d29",
        "menubar_active": "#6b4423",
        "menu_bg":        "#2b2118",
        "menu_fg":        "#e8d5b7",
        "menu_active_bg": "#6b4423",
        "menu_active_fg": "#f4e4c1",
        "simple_btn_bg":  "#8b4513",
        "simple_btn_fg":  "#f4e4c1",
        "simple_btn_hover": "#a0551f",
        "status_bg":      "#3d2b1f",
        "status_fg":      "#d4a373",
        "font_hint":      "serif",  # used for menubar button font
    },
}



SYNTAX_COLORS = {
    "dark":           ("#c586c0", "#ce9178", "#6a9955", "#b5cea8", "#dcdcaa"),
    "light":          ("#af00db", "#a31515", "#008000", "#098658", "#795e26"),
    "high-contrast":  ("#ff00ff", "#00ffff", "#00ff00", "#ffff00", "#ff8000"),
    "gruvbox":        ("#fb4934", "#b8bb26", "#928374", "#d3869b", "#fabd2f"),
    "nord":           ("#81a1c1", "#a3be8c", "#616e88", "#b48ead", "#ebcb8b"),
    "solarized":      ("#859900", "#2aa198", "#586e75", "#d33682", "#b58900"),    "monokai":         ("#f92672", "#e6db74", "#75715e", "#ae81ff", "#a6e22e"),
    "dracula":         ("#ff79c6", "#f1fa8c", "#6272a4", "#bd93f9", "#50fa7b"),
    "one-dark":        ("#c678dd", "#98c379", "#5c6370", "#d19a66", "#61afef"),
    "tokyo-night":     ("#bb9af7", "#9ece6a", "#565f89", "#ff9e64", "#7aa2f7"),
    "catppuccin":      ("#cba6f7", "#a6e3a1", "#6c7086", "#fab387", "#89b4fa"),
    "catppuccin-latte":("#8839ef", "#40a02b", "#9ca0b0", "#fe640b", "#1e66f5"),
    "github-dark":     ("#ff7b72", "#a5d6ff", "#8b949e", "#79c0ff", "#d2a8ff"),
    "github-light":    ("#cf222e", "#0a3069", "#6e7781", "#0550ae", "#8250df"),
    "ayu-dark":        ("#ff8f40", "#aad94c", "#acb6bf", "#d2a6ff", "#59c2ff"),
    "night-owl":       ("#c792ea", "#ecc48d", "#637777", "#f78c6c", "#82aaff"),
    "material":        ("#c792ea", "#c3e88d", "#546e7a", "#f78c6c", "#82aaff"),
    "solarized-light": ("#859900", "#2aa198", "#93a1a1", "#d33682", "#b58900"),
    "everforest":      ("#e67e80", "#a7c080", "#7a8478", "#d699b6", "#dbbc7f"),
    "rose-pine":       ("#c4a7e7", "#f6c177", "#6e6a86", "#eb6f92", "#9ccfd8"),

}



# ==================== Path completion dialog ====================

class PathDialog(tk.Toplevel):
    """File open/save dialog with tab-completion."""

    def __init__(self, parent, mode, initial="", on_ok=None):
        super().__init__(parent)
        self.mode = mode  # "open" or "save"
        self.on_ok = on_ok
        self.title("Open File" if mode == "open" else "Save As")
        self.geometry("560x420")
        self.transient(parent)
        self.configure(bg="#1e1e1e")

        initial = initial or str(Path.home()) + "/"
        self.var = tk.StringVar(value=initial)

        tk.Label(self, text="Path:", bg="#1e1e1e", fg="#d4d4d4").pack(anchor="w", padx=12, pady=(12, 4))
        self.entry = tk.Entry(self, textvariable=self.var, bg="#252526", fg="#d4d4d4",
                              insertbackground="#d4d4d4", font=("Monospace", 11))
        self.entry.pack(fill="x", padx=12)
        self.entry.focus_set()

        tk.Label(self, text="Matches (Tab/↑↓ to select, Enter to open):",
                 bg="#1e1e1e", fg="#888", font=("Sans", 9)).pack(anchor="w", padx=12, pady=(10, 4))

        listframe = tk.Frame(self, bg="#1e1e1e")
        listframe.pack(fill="both", expand=True, padx=12)
        self.listbox = tk.Listbox(listframe, bg="#252526", fg="#d4d4d4",
                                    selectbackground="#264f78", selectforeground="#fff",
                                    font=("Monospace", 10), borderwidth=0, highlightthickness=0)
        sb = tk.Scrollbar(listframe, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        btns = tk.Frame(self, bg="#1e1e1e")
        btns.pack(pady=10)
        tk.Button(btns, text="OK", width=10, command=self._accept).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=6)

        self.listbox.bind("<Double-Button-1>", lambda e: self._accept())
        self.entry.bind("<Tab>", self._tab_complete)
        self.entry.bind("<Return>", lambda e: self._accept())
        self.entry.bind("<Down>", self._focus_list)
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self.listbox.bind("<Return>", lambda e: self._accept())
        self.listbox.bind("<Escape>", lambda e: self.entry.focus_set())
        self.bind("<Escape>", lambda e: self.destroy())

        self._refresh()

    def _focus_list(self, event=None):
        if self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        return "break"

    def _current_path(self):
        return Path(self.var.get()).expanduser()

    def _refresh(self):
        self.listbox.delete(0, "end")
        raw = self.var.get()
        try:
            p = Path(raw).expanduser()
        except Exception:
            return

        if raw.endswith("/"):
            parent = p
            prefix = ""
        else:
            parent = p.parent
            prefix = p.name

        if not parent.exists() or not parent.is_dir():
            parent = Path.home()
            prefix = ""

        try:
            entries = sorted(parent.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return

        self._completions = []
        for e in entries:
            if e.name.startswith("."):
                continue
            if prefix and not e.name.lower().startswith(prefix.lower()):
                continue
            tag = "/" if e.is_dir() else ""
            self.listbox.insert("end", e.name + tag)
            self._completions.append(e)

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
        self._refresh()

    def _tab_complete(self, event=None):
        # Complete to common prefix of all current matches
        raw = self.var.get()
        try:
            p = Path(raw).expanduser()
        except Exception:
            return "break"

        if raw.endswith("/"):
            parent = p
            prefix = ""
        else:
            parent = p.parent
            prefix = p.name

        if not parent.exists():
            return "break"

        try:
            names = [e.name for e in parent.iterdir() if not e.name.startswith(".")]
        except PermissionError:
            return "break"

        matches = [n for n in names if n.startswith(prefix)]
        if not matches:
            return "break"

        # If exactly one match and it's a dir, enter it
        if len(matches) == 1:
            full = parent / matches[0]
            if full.is_dir():
                self.var.set(str(full) + "/")
            else:
                self.var.set(str(full))
            self._refresh()
            self.entry.icursor("end")
            return "break"

        # Find longest common prefix
        common = os.path.commonprefix(matches)
        if len(common) > len(prefix):
            self.var.set(str(parent / common))
            self.entry.icursor("end")
            self._refresh()
        return "break"

    def _accept(self):
        sel = self.listbox.curselection()
        if sel and self.listbox.focus_get() == self.listbox:
            name = self._completions[sel[0]].name
            full = self._completions[sel[0]]
            if full.is_dir():
                self.var.set(str(full) + "/")
                self._refresh()
                self.entry.focus_set()
                return
            self.var.set(str(full))

        path = self.var.get().strip()
        if not path:
            self.destroy(); return

        p = Path(path).expanduser()

        if self.mode == "open":
            if not p.exists():
                messagebox.showwarning("Not found", f"No such file:\n{p}", parent=self)
                return
            if p.is_dir():
                self.var.set(str(p) + "/")
                self._refresh()
                return
        else:  # save
            if p.exists():
                if not messagebox.askyesno("Overwrite?", f"{p.name} exists. Overwrite?", parent=self):
                    return
            p.parent.mkdir(parents=True, exist_ok=True)

        self.destroy()
        if self.on_ok:
            self.on_ok(p)


# ==================== Pane (buffer + widgets) ====================

class Pane:
    def __init__(self, container, app, initial_path=None):
        self.app = app
        self.frame = tk.Frame(container)

        self.gutter = tk.Text(self.frame, width=4, padx=4, takefocus=0,
                              border=0, highlightthickness=0, state="disabled", wrap="none")
        self.gutter.pack(side="left", fill="y")

        self.text = tk.Text(self.frame, wrap="none", undo=True,
                            font=(app._font_family, app._font_size),
                            tabs=(app._tab_width * 8,), padx=6,
                            border=0, highlightthickness=0)
        self.text.pack(side="left", fill="both", expand=True)

        self.scroll = tk.Scrollbar(self.frame, command=self._on_scroll)
        self.scroll.pack(side="right", fill="y")
        self.text.config(yscrollcommand=self._on_text_scroll)

        # buffer state
        self.path = None
        self.dirty = False
        self.line_ending = "LF"
        self.has_bom = False
        self.syncing = False

        self.text.bind("<KeyPress>", app._on_keypress, add="+")
        self.text.bind("<Return>", app._on_return, add="+")
        self.text.bind("<KeyRelease>", app._on_keyrelease_brackets, add="+")
        self.text.bind("<<Modified>>", self._on_modified, add="+")
        self.text.bind("<KeyRelease>", app._post_edit, add="+")
        self.text.bind("<ButtonRelease>", app._post_edit, add="+")
        self.text.bind("<Tab>", app._on_tab, add="+")
        self.text.bind("<Control-a>", app.select_all)
        self.text.bind("<Control-d>", app.duplicate_line)
        self.text.bind("<Control-slash>", app.toggle_comment)
        self.text.bind("<FocusIn>", self._on_focus, add="+")

        if initial_path:
            app._load_path_into_pane(self, initial_path)

    def _on_focus(self, event=None):
        self.app.update_status()

    def _on_scroll(self, *args):
        self.text.yview(*args)
        self.gutter.yview(*args)

    def _on_text_scroll(self, first, last):
        self.scroll.set(first, last)
        self.gutter.yview_moveto(first)

    def _on_modified(self, event=None):
        if self.text.edit_modified():
            self.dirty = True
            self.app._refresh_tab_title_for_pane(self)

    def _post_edit(self, event=None):
        self.app._update_gutter_for_pane(self)
        self.app.update_status()
        self.app._schedule_syntax(self)
        if self.app._show_ws:
            self.app._paint_ws_for(self)


# ==================== Tab (holds 1 or 2 panes) ====================

class Tab:
    def __init__(self, notebook, app):
        self.app = app
        self.frame = tk.Frame(notebook)
        self.paned = tk.PanedWindow(self.frame, orient="horizontal",
                                     sashwidth=6, sashrelief="flat",
                                     bg=app.settings.get("_sash_bg", "#2d2d2d"))
        self.paned.pack(fill="both", expand=True)
        self.panes = []
        self.add_pane()

    def add_pane(self, initial_path=None):
        pane = Pane(self.paned, self.app, initial_path)
        self.paned.add(pane.frame, stretch="always")
        self.panes.append(pane)
        return pane

    def remove_pane(self, pane):
        if len(self.panes) <= 1:
            return False
        self.paned.forget(pane.frame)
        self.panes.remove(pane)
        return True

    def active_pane(self):
        focus = self.frame.focus_get()
        for p in self.panes:
            if focus is p.text or focus is p.gutter:
                return p
        # try tk's focus_get globally
        try:
            focus = self.frame.winfo_toplevel().focus_get()
        except Exception:
            focus = None
        for p in self.panes:
            if focus is p.text or focus is p.gutter:
                return p
        return self.panes[0]

    def title(self):
        names = []
        for p in self.panes:
            n = p.path.name if p.path else "untitled"
            if p.dirty:
                n = "● " + n
            names.append(n)
        return " | ".join(names) if len(names) > 1 else names[0]

    def any_dirty(self):
        return any(p.dirty for p in self.panes)


# ==================== Main app ====================

class AerogelButton(tk.Canvas):
    """Windows-Vista-style Aero glass button. Multi-band gradient, rim light,
    drop-shadow text, animated hover fade."""

    def __init__(self, parent, text, command,
                 base_color="#6C4AB6", hover_color="#7a5cc6",
                 fg_color="#ffffff", width=150, height=30):
        bg_of_parent = parent.cget("bg") if hasattr(parent, "cget") else "#2d2d2d"
        super().__init__(parent, width=width, height=height,
                          bg=bg_of_parent, highlightthickness=0, borderwidth=0,
                          cursor="hand2")
        self.text = text
        self.command = command
        self.base_color = base_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.w = width
        self.h = height
        self._current = base_color
        self._anim = None
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    # ---- public ----
    def set_text(self, text):
        self.text = text
        self._draw()

    def set_colors(self, base=None, hover=None, fg=None, parent_bg=None):
        if base is not None: self.base_color = base
        if hover is not None: self.hover_color = hover
        if fg is not None: self.fg_color = fg
        if parent_bg is not None:
            try: self.config(bg=parent_bg)
            except Exception: pass
        if not self._hover:
            self._current = self.base_color
        self._draw()

    # ---- helpers ----
    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _mix(self, color, target_rgb, amount):
        r, g, b = self._hex_to_rgb(color)
        r = int(r + (target_rgb[0] - r) * amount)
        g = int(g + (target_rgb[1] - g) * amount)
        b = int(b + (target_rgb[2] - b) * amount)
        return self._rgb_to_hex((r, g, b))

    def _lighten(self, color, amount):
        return self._mix(color, (255, 255, 255), amount)

    def _darken(self, color, amount):
        return self._mix(color, (0, 0, 0), amount)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1,
            x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2,
            x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2,
            x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kwargs)

    # ---- drawing ----
    def _draw(self):
        self.delete("all")
        w, h = self.w, self.h
        r = h // 2
        base = self._current

        # 1. Base pill — solid color
        self._round_rect(0, 0, w, h, r, fill=base, outline="")

        # 2. Vertical gradient — 6 bands from light top to dark bottom
        #    Splits the pill into horizontal slices. Each slice is a rounded
        #    rect only on the edges that need to curve.
        bands = 8
        for i in range(bands):
            t = i / (bands - 1)  # 0 top → 1 bottom
            # interpolate: top is light, middle is base, bottom is dark
            if t < 0.5:
                band_color = self._mix(base, (255, 255, 255), (0.5 - t) * 0.65)
            else:
                band_color = self._mix(base, (0, 0, 0), (t - 0.5) * 0.45)
            y1 = int(h * i / bands)
            y2 = int(h * (i + 1) / bands) + 1
            # top band → curve the top corners
            if i == 0:
                self._round_rect(1, 0, w - 1, y2, r, fill=band_color, outline="")
            # bottom band → curve the bottom corners
            elif i == bands - 1:
                self._round_rect(1, y1, w - 1, h, r, fill=band_color, outline="")
            else:
                self.create_rectangle(1, y1, w - 1, y2,
                                       fill=band_color, outline="")

        # 3. Top rim light — thin bright arc
        rim_top = self._lighten(base, 0.55)
        self._round_rect(2, 1, w - 2, int(h * 0.35), r - 2,
                          fill="", outline=rim_top, width=1)

        # 4. Bottom shadow — thin dark arc
        rim_bot = self._darken(base, 0.35)
        self._round_rect(1, int(h * 0.55), w - 1, h - 1, r - 1,
                          fill="", outline=rim_bot, width=1)

        # 5. Outer border — subtle dark edge
        outer = self._darken(base, 0.5)
        self._round_rect(0, 0, w - 1, h - 1, r,
                          fill="", outline=outer, width=1)

        # 6. Text with drop shadow (1px below)
        cx, cy = w // 2, h // 2
        shadow = "#000000"
        self.create_text(cx + 1, cy + 1, text=self.text, fill=shadow,
                          font=("Sans", 10, "bold"))
        self.create_text(cx, cy, text=self.text, fill=self.fg_color,
                          font=("Sans", 10, "bold"))

    # ---- events ----
    def _on_enter(self, _e):
        self._hover = True
        self._animate_to(self.hover_color)

    def _on_leave(self, _e):
        self._hover = False
        self._animate_to(self.base_color)

    def _on_click(self, _e):
        if self.command:
            self.command()

    def _animate_to(self, target_hex):
        if self._anim:
            try: self.after_cancel(self._anim)
            except Exception: pass
        steps = 12
        start = self._hex_to_rgb(self._current)
        end = self._hex_to_rgb(target_hex)

        def step(i):
            if i > steps:
                self._current = target_hex
                self._draw()
                return
            t = i / steps
            # ease-out for a snappier feel
            t = 1 - (1 - t) ** 2
            r = int(start[0] + (end[0] - start[0]) * t)
            g = int(start[1] + (end[1] - start[1]) * t)
            b = int(start[2] + (end[2] - start[2]) * t)
            self._current = self._rgb_to_hex((r, g, b))
            self._draw()
            self._anim = self.after(12, lambda: step(i + 1))

        step(0)



class QuillinksGUI:
    def __init__(self, path=None):
        self.settings = _load_settings()
        self.root = tk.Tk()
        self.root.title("Quillinks")
        self.root.geometry(self.settings.get("geometry", "1050x720"))

        self.tabs = []
        self.recent_menu = None
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
        self._syntax = bool(self.settings.get("syntax_highlight", True))
        self._hl_jobs = {}
        self._syntax = bool(self.settings.get("syntax_highlight", True))
        self._hl_jobs = {}
        self._simple_mode = bool(self.settings.get("simple_mode", False))

        self._topbar = tk.Frame(self.root, bg="#2d2d2d", height=32)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)

        self.simple_btn = AerogelButton(
            self._topbar,
            text="◀ Simple Mode",
            command=self.toggle_simple_mode,
            base_color="#6C4AB6",
            hover_color="#7a5cc6",
            fg_color="#ffffff",
            width=150, height=26,
        )
        self.simple_btn.pack(side="right", padx=8, pady=4)

        self._build_menu()

        outer = tk.Frame(self.root)
        outer.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_switch)

        self.status = tk.Label(self.root, anchor="w", padx=6)
        self.status.pack(fill="x", side="bottom")

        # Global bindings
        self.root.bind("<Control-n>", lambda e: self.new_tab())
        self.root.bind("<Control-t>", lambda e: self.new_tab())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-w>", lambda e: self.close_tab())
        self.root.bind("<Control-Shift-W>", lambda e: self.close_pane())
        self.root.bind("<Control-q>", lambda e: self.on_close())
        self.root.bind("<Control-backslash>", lambda e: self.toggle_split())
        self.root.bind("<Control-f>", lambda e: self.open_find())
        self.root.bind("<Control-h>", lambda e: self.open_find())
        self.root.bind("<Control-g>", self.goto_line)
        self.root.bind("<Control-r>", lambda e: self.open_find_regex())
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

        if path:
            self._open_path(Path(path))
        else:
            self.new_tab()

        self._apply_theme()
        self.toggle_wrap()
        self._apply_font()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(300, self._autosave_tick)

    # ==================== active tab / pane ====================

    def _active_tab(self):
        idx = self.notebook.index(self.notebook.select())
        return self.tabs[idx]

    def _active_pane(self):
        return self._active_tab().active_pane()

    @property
    def text(self):
        return self._active_pane().text

    @property
    def gutter(self):
        return self._active_pane().gutter

    @property
    def path(self):
        return self._active_pane().path

    @path.setter
    def path(self, v):
        self._active_pane().path = v

    @property
    def dirty(self):
        return self._active_pane().dirty

    @dirty.setter
    def dirty(self, v):
        self._active_pane().dirty = v

    @property
    def _line_ending(self):
        return self._active_pane().line_ending

    @_line_ending.setter
    def _line_ending(self, v):
        self._active_pane().line_ending = v

    @property
    def _has_bom(self):
        return self._active_pane().has_bom

    @_has_bom.setter
    def _has_bom(self, v):
        self._active_pane().has_bom = v

    def _post_edit(self, event=None):
        self._update_gutter_for_pane(self._active_pane())
        self.update_status()
        if self._show_ws:
            self._paint_ws_for(self._active_pane())

    def _refresh_tab_title_for_pane(self, pane):
        for i, tab in enumerate(self.tabs):
            if pane in tab.panes:
                self.notebook.tab(i, text=tab.title())
                return

    # ==================== menu ====================

    def _apply_syntax_to(self, pane):
        if not getattr(self, "_syntax", True):
            return
        lang = syntax_highlight.detect_language(pane.path)
        if not lang:
            return
        cols = SYNTAX_COLORS.get(self._theme, SYNTAX_COLORS["dark"])
        kw, st, cm, nu, fu = cols
        tag_colors = {
            "sh_keyword": {"foreground": kw},
            "sh_string": {"foreground": st},
            "sh_comment": {"foreground": cm, "font": (self._font_family, self._font_size, "italic")},
            "sh_number": {"foreground": nu},
            "sh_func": {"foreground": fu},
        }
        try:
            syntax_highlight.highlight(pane.text, lang, tag_colors)
        except Exception:
            pass

    def _schedule_syntax(self, pane):
        if not getattr(self, "_syntax", True):
            return
        prev = self._hl_jobs.get(id(pane))
        if prev is not None:
            try:
                pane.text.after_cancel(prev)
            except Exception:
                pass
        self._hl_jobs[id(pane)] = pane.text.after(120, lambda: self._apply_syntax_to(pane))

    def toggle_syntax(self):
        self._syntax = not self._syntax
        self.settings["syntax_highlight"] = self._syntax
        for tab in self.tabs:
            for pane in tab.panes:
                if self._syntax:
                    self._apply_syntax_to(pane)
                else:
                    for tag in ("sh_keyword", "sh_string", "sh_comment", "sh_number", "sh_func"):
                        pane.text.tag_remove(tag, "1.0", "end")

    def open_find_regex(self):
        win = tk.Toplevel(self.root)
        win.title("Find & Replace (Regex)")
        win.geometry("540x340")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")

        tk.Label(win, text="Pattern (Python regex):", bg="#1e1e1e", fg="#d4d4d4").grid(
            row=0, column=0, sticky="e", padx=8, pady=6)
        pat_var = tk.StringVar()
        tk.Entry(win, textvariable=pat_var, width=40,
                 bg="#252526", fg="#d4d4d4", insertbackground="#d4d4d4").grid(
            row=0, column=1, columnspan=2, padx=4, pady=6, sticky="we")

        tk.Label(win, text="Replace (\\1 for group 1):", bg="#1e1e1e", fg="#d4d4d4").grid(
            row=1, column=0, sticky="e", padx=8, pady=6)
        repl_var = tk.StringVar()
        tk.Entry(win, textvariable=repl_var, width=40,
                 bg="#252526", fg="#d4d4d4", insertbackground="#d4d4d4").grid(
            row=1, column=1, columnspan=2, padx=4, pady=6, sticky="we")

        case_var = tk.BooleanVar(value=False)
        dotall_var = tk.BooleanVar(value=False)
        opts = tk.Frame(win, bg="#1e1e1e")
        opts.grid(row=2, column=0, columnspan=3, pady=4, sticky="w", padx=8)
        tk.Checkbutton(opts, text="Case sensitive", variable=case_var,
                        bg="#1e1e1e", fg="#d4d4d4", selectcolor="#2d2d30",
                        activebackground="#1e1e1e", activeforeground="#d4d4d4").pack(side="left", padx=6)
        tk.Checkbutton(opts, text=". matches newline", variable=dotall_var,
                        bg="#1e1e1e", fg="#d4d4d4", selectcolor="#2d2d30",
                        activebackground="#1e1e1e", activeforeground="#d4d4d4").pack(side="left", padx=6)

        info = tk.Label(win, text="", bg="#1e1e1e", fg="#4ec9b0", font=("Sans", 9))
        info.grid(row=3, column=0, columnspan=3, pady=(4, 8))

        def get_flags():
            f = 0
            if not case_var.get(): f |= re.IGNORECASE
            if dotall_var.get(): f |= re.DOTALL
            return f

        def compile_pat():
            try:
                return re.compile(pat_var.get(), get_flags())
            except re.error as e:
                info.config(text=f"Bad regex: {e}")
                return None

        def find_all():
            rx = compile_pat()
            if rx is None: return
            self._clear_highlights()
            content = self.text.get("1.0", "end-1c")
            n = 0
            for m in rx.finditer(content):
                s = self._char_to_index(content, m.start())
                e = self._char_to_index(content, m.end())
                self.text.tag_add("hl", s, e)
                n += 1
            self.text.tag_config("hl", background="#5a4a1a")
            info.config(text=f"{n} match{'es' if n != 1 else ''}")

        def replace_all():
            rx = compile_pat()
            if rx is None: return
            content = self.text.get("1.0", "end-1c")
            repl = repl_var.get()
            try:
                count = len(rx.findall(content))
                new_content = rx.sub(repl, content)
            except re.error as e:
                info.config(text=f"Sub error: {e}")
                return
            if count == 0:
                info.config(text="No matches")
                return
            self.text.delete("1.0", "end")
            self.text.insert("1.0", new_content)
            info.config(text=f"Replaced {count}")

        btns = tk.Frame(win, bg="#1e1e1e")
        btns.grid(row=4, column=0, columnspan=3, pady=8)
        tk.Button(btns, text="Highlight All", command=find_all, width=14).pack(side="left", padx=6)
        tk.Button(btns, text="Replace All", command=replace_all, width=14).pack(side="left", padx=6)
        tk.Button(btns, text="Close",
                   command=lambda: (self._clear_highlights(), win.destroy()),
                   width=10).pack(side="left", padx=6)

    def toggle_simple_mode(self):
        self._simple_mode = not self._simple_mode
        self.settings["simple_mode"] = self._simple_mode
        self._update_simple_button()
        self._build_menu()
        self.status.config(text=f" Simple mode: {'ON' if self._simple_mode else 'OFF'}")

    def _update_simple_button(self):
        if not hasattr(self, "simple_btn"):
            return
        extras = UI_EXTRAS.get(self._theme)
        if self._simple_mode:
            self.simple_btn.set_text("▶ Full Mode")
            if extras is None:
                self.simple_btn.set_colors("#2E7D5B", "#3a9670", "#ffffff")
            else:
                self.simple_btn.set_colors("#4a6741", "#5a7a4d", extras["simple_btn_fg"])
        else:
            self.simple_btn.set_text("◀ Simple Mode")
            if extras is None:
                self.simple_btn.set_colors("#6C4AB6", "#7a5cc6", "#ffffff")
            else:
                self.simple_btn.set_colors(
                    extras["simple_btn_bg"],
                    extras["simple_btn_hover"],
                    extras["simple_btn_fg"],
                )

    def _build_menu(self):
        """Rebuild the custom menu bar on the top toolbar."""
        # Destroy existing menu widgets (keep the simple_btn)
        for child in list(self._topbar.winfo_children()):
            if child is not self.simple_btn:
                child.destroy()

        self._menus = {}

        def add_menu(name, build_fn):
            btn = tk.Menubutton(
                self._topbar, text=name, relief="flat", borderwidth=0,
                bg="#2d2d2d", fg="#d4d4d4",
                activebackground="#3d3d3d", activeforeground="#ffffff",
                padx=10, pady=4, font=("Sans", 10),
            )
            m = tk.Menu(btn, tearoff=0)
            btn.config(menu=m)
            build_fn(m)
            btn.pack(side="left", padx=0, pady=0)
            self._menus[name] = (btn, m)

        # ---- File ----
        def build_file(m):
            m.add_command(label="New", accelerator="Ctrl+T", command=self.new_tab)
            m.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
            m.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
            m.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_as)
            m.add_separator()
            m.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)

        def build_file_full(m):
            m.add_command(label="New Tab", accelerator="Ctrl+T", command=self.new_tab)
            m.add_command(label="New File", accelerator="Ctrl+N", command=self.new_tab)
            m.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
            m.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
            m.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_as)
            m.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_tab)
            m.add_command(label="Close Pane", accelerator="Ctrl+Shift+W", command=self.close_pane)
            m.add_separator()
            self.recent_menu = tk.Menu(m, tearoff=0)
            m.add_cascade(label="Open Recent", menu=self.recent_menu)
            self._rebuild_recent_menu()
            m.add_separator()
            m.add_command(label="Revert", command=self.revert_file)
            m.add_separator()
            le = tk.Menu(m, tearoff=0)
            for eol in ["LF", "CRLF", "CR"]:
                le.add_command(label=eol, command=lambda x=eol: self.set_line_ending(x))
            m.add_cascade(label="Line Endings", menu=le)
            m.add_separator()
            m.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)

        # ---- Edit ----
        def build_edit(m):
            m.add_command(label="Undo", accelerator="Ctrl+Z",
                          command=lambda: self.text.event_generate("<<Undo>>"))
            m.add_command(label="Redo", accelerator="Ctrl+Y",
                          command=lambda: self.text.event_generate("<<Redo>>"))
            m.add_separator()
            m.add_command(label="Cut", command=lambda: self.text.event_generate("<<Cut>>"))
            m.add_command(label="Copy", command=lambda: self.text.event_generate("<<Copy>>"))
            m.add_command(label="Paste", command=lambda: self.text.event_generate("<<Paste>>"))
            m.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
            m.add_separator()
            m.add_command(label="Find & Replace…", accelerator="Ctrl+F", command=self.open_find)
            m.add_command(label="Find with Regex…", accelerator="Ctrl+R", command=self.open_find_regex)
            m.add_command(label="Go to line…", accelerator="Ctrl+G", command=self.goto_line)

        def build_edit_full(m):
            build_edit(m)
            m.add_separator()
            m.add_command(label="Duplicate Line", command=self.duplicate_line)
            m.add_command(label="Delete Line", command=self.delete_line)
            m.add_command(label="Toggle Comment", command=self.toggle_comment)
            m.add_separator()
            m.add_command(label="UPPERCASE", command=self.uppercase_sel)
            m.add_command(label="lowercase", command=self.lowercase_sel)
            m.add_command(label="Trim trailing whitespace", command=self.trim_ws)
            m.add_command(label="Sort lines", command=self.sort_lines)
            m.add_separator()
            m.add_command(label="Tabs → Spaces", command=self.convert_tabs_to_spaces)
            m.add_command(label="Spaces → Tabs", command=self.convert_spaces_to_tabs)
            m.add_separator()
            m.add_command(label="Insert Date/Time", accelerator="F5", command=self.insert_datetime)

        # ---- View ----
        def build_view(m):
            self.wrap_var = tk.BooleanVar(value=bool(self.settings.get("wrap", False)))
            m.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_wrap)
            m.add_separator()
            m.add_command(label="Zoom In", command=lambda: self.zoom(1))
            m.add_command(label="Zoom Out", command=lambda: self.zoom(-1))
            m.add_command(label="Reset Zoom", command=self.zoom_reset)

        def build_view_full(m):
            build_view(m)
            m.add_separator()
            self.ws_var = tk.BooleanVar(value=self._show_ws)
            m.add_checkbutton(label="Show Whitespace", variable=self.ws_var, command=self.toggle_whitespace)
            self.autopair_var = tk.BooleanVar(value=self._autopair)
            m.add_checkbutton(label="Auto-pair brackets", variable=self.autopair_var, command=self.toggle_autopair)
            self.ai_var = tk.BooleanVar(value=self._auto_indent)
            m.add_checkbutton(label="Auto-indent", variable=self.ai_var, command=self.toggle_auto_indent)
            self.bm_var = tk.BooleanVar(value=self._bracket_match)
            m.add_checkbutton(label="Bracket matching", variable=self.bm_var, command=self.toggle_bracket_match)
            self.eol_var = tk.BooleanVar(value=False)
            m.add_checkbutton(label="Show EOL markers", variable=self.eol_var, command=self.toggle_eol_markers)
            self.ruler_var = tk.BooleanVar(value=self._show_ruler)
            m.add_checkbutton(label="Column Ruler", variable=self.ruler_var, command=self.toggle_ruler)
            self.syntax_var = tk.BooleanVar(value=self._syntax)
            m.add_checkbutton(label="Syntax Highlighting", variable=self.syntax_var,
                              command=self.toggle_syntax)
            m.add_separator()
            m.add_command(label="Split Vertical", accelerator="Ctrl+\\", command=self.toggle_split)
            m.add_separator()
            tw = tk.Menu(m, tearoff=0)
            for w in [2, 4, 8]:
                tw.add_command(label=f"{w} spaces", command=lambda x=w: self.set_tab_width(x))
            m.add_cascade(label="Tab width", menu=tw)
            self.us_var = tk.BooleanVar(value=self._use_spaces)
            m.add_checkbutton(label="Use spaces for Tab", variable=self.us_var,
                              command=lambda: self.set_use_spaces(self.us_var.get()))
            m.add_separator()
            fm2 = tk.Menu(m, tearoff=0)
            fm2.add_command(label="Change Font Family…", command=self.open_font_picker)
            m.add_cascade(label="Font", menu=fm2)

        # ---- Tools ----
        def build_tools(m):
            m.add_command(label="Simple Mode Toggle", command=self.toggle_simple_mode)

        def build_tools_full(m):
            m.add_command(label="Simple Mode Toggle", command=self.toggle_simple_mode)
            m.add_separator()
            m.add_command(label="Plugin Manager…", command=self.open_plugin_manager)
            m.add_command(label="Save Settings Now", command=self.save_settings)
            m.add_command(label="Open Config Folder", command=self._open_config_folder)

        # ---- Settings ----
        def build_settings(m):
            th = tk.Menu(m, tearoff=0)
            for t in THEMES.keys():
                th.add_command(label=t, command=lambda x=t: self.set_theme(x))
            m.add_cascade(label="Theme", menu=th)

        # ---- Help ----
        def build_help(m):
            m.add_command(label="Keyboard Shortcuts", accelerator="F1", command=self.show_shortcuts)
            m.add_command(label="About", command=self.show_about)

        if self._simple_mode:
            add_menu("File", build_file)
            add_menu("Edit", build_edit)
            add_menu("View", build_view)
            add_menu("Tools", build_tools)
            add_menu("Help", build_help)
        else:
            add_menu("File", build_file_full)
            add_menu("Edit", build_edit_full)
            add_menu("View", build_view_full)
            add_menu("Tab", lambda m: (
                m.add_command(label="New Tab", accelerator="Ctrl+T", command=self.new_tab),
                m.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_tab),
                m.add_separator(),
                m.add_command(label="Next Tab", command=self._next_tab),
                m.add_command(label="Prev Tab", command=self._prev_tab),
            ))
            add_menu("Tools", build_tools_full)
            add_menu("Settings", build_settings)
            add_menu("Help", build_help)

    def new_tab(self):
        tab = Tab(self.notebook, self)
        self.tabs.append(tab)
        self.notebook.add(tab.frame, text=tab.title())
        self.notebook.select(tab.frame)
        tab.panes[0].text.focus_set()
        self._apply_theme_to_tab(tab)
        self._update_gutter_for_pane(tab.panes[0])

    def close_tab(self):
        idx = self.notebook.index(self.notebook.select())
        tab = self.tabs[idx]
        if tab.any_dirty():
            ans = messagebox.askyesnocancel("Unsaved changes",
                                             f"Save changes to {tab.title()}?")
            if ans is None:
                return
            if ans:
                self.notebook.select(tab.frame)
                # Save every dirty pane
                for p in tab.panes:
                    if p.dirty:
                        self._save_pane(p)
        self.tabs.pop(idx)
        self.notebook.forget(tab.frame)
        if not self.tabs:
            self.new_tab()
        self.update_title()

    def close_pane(self):
        tab = self._active_tab()
        if len(tab.panes) <= 1:
            return
        pane = tab.active_pane()
        if pane.dirty:
            ans = messagebox.askyesnocancel("Unsaved changes",
                                             f"Save changes to {pane.path.name if pane.path else 'untitled'}?")
            if ans is None:
                return
            if ans:
                self._save_pane(pane)
        tab.remove_pane(pane)
        self._refresh_tab_title_for_pane(tab.panes[0])
        self.update_title()

    def toggle_split(self):
        tab = self._active_tab()
        if len(tab.panes) >= 2:
            # collapse to one
            pane = tab.panes[1]
            if pane.dirty:
                self.notebook.select(tab.frame)
                ans = messagebox.askyesnocancel("Unsaved changes",
                                                 f"Save changes to {pane.path.name if pane.path else 'untitled'}?")
                if ans is None:
                    return
                if ans:
                    self._save_pane(pane)
            tab.remove_pane(pane)
        else:
            tab.add_pane()
            self._apply_theme_to_tab(tab)
            self._apply_font()
            self._apply_ruler()
        self._refresh_tab_title_for_pane(tab.panes[0])

    def _next_tab(self):
        if len(self.tabs) < 2: return
        idx = self.notebook.index(self.notebook.select())
        self.notebook.select(self.tabs[(idx + 1) % len(self.tabs)].frame)

    def _prev_tab(self):
        if len(self.tabs) < 2: return
        idx = self.notebook.index(self.notebook.select())
        self.notebook.select(self.tabs[(idx - 1) % len(self.tabs)].frame)

    def _goto_tab(self, n):
        idx = n - 1
        if 0 <= idx < len(self.tabs):
            self.notebook.select(self.tabs[idx].frame)

    def _on_tab_switch(self, event=None):
        self.update_title()
        self.update_status()
        for pane in self._active_tab().panes:
            self._update_gutter_for_pane(pane)
        if self._show_ws:
            self._paint_ws_for(self._active_pane())
        if self._show_eol:
            self.toggle_eol_markers()
        self._apply_ruler()

    # ==================== gutter / ruler ====================

    def _update_gutter_for_pane(self, pane):
        if pane.syncing:
            return
        pane.syncing = True
        try:
            content = pane.text.get("1.0", "end-1c")
            n = content.count("\n") + 1
            width = max(3, len(str(n)))
            lines = "\n".join(str(i).rjust(width) for i in range(1, n + 1))
            pane.gutter.config(state="normal")
            pane.gutter.delete("1.0", "end")
            pane.gutter.insert("1.0", lines)
            pane.gutter.config(state="disabled", width=width + 1)
            pane.gutter.yview_moveto(pane.text.yview()[0])
        finally:
            pane.syncing = False

    def toggle_ruler(self):
        self._show_ruler = self.ruler_var.get()
        self.settings["show_ruler"] = self._show_ruler
        self._apply_ruler()

    def _apply_ruler(self):
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.tag_remove("ruler", "1.0", "end")
        if not self._show_ruler:
            return
        col = self._ruler_col
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.tag_configure("ruler", background="#3a2a2a")
                idx = "1.0"
                for _ in range(10000):
                    if pane.text.compare(idx, ">=", "end-1c"):
                        break
                    line_end = pane.text.index(f"{idx} lineend")
                    mark = f"{idx} +{col}c"
                    try:
                        if pane.text.compare(mark, "<", line_end):
                            pane.text.tag_add("ruler", mark, f"{mark}+1c")
                    except tk.TclError:
                        pass
                    try:
                        nxt = pane.text.index(f"{line_end}+1c")
                    except tk.TclError:
                        break
                    if nxt == line_end:
                        break
                    idx = nxt

    # ==================== theme ====================

    def _style_ui(self):
        """Apply theme-specific chrome styling: toolbar, menubar, buttons, menus."""
        extras = UI_EXTRAS.get(self._theme)
        bg, fg, ins, sel, gbg, gfg, sbg, sfg = THEMES.get(self._theme, THEMES["dark"])

        if extras is None:
            # default chrome
            if hasattr(self, "_toolbar"):
                try: self._toolbar.config(bg="#2d2d2d")
                except Exception: pass
            if hasattr(self, "simple_btn"):
                self._update_simple_button()
            if hasattr(self, "_menus"):
                for name, (btn, menu) in self._menus.items():
                    btn.config(bg="#2d2d2d", fg="#d4d4d4",
                               activebackground="#3d3d3d", activeforeground="#ffffff",
                               font=("Sans", 10))
                    menu.config(bg="#2b2b2b", fg="#d4d4d4",
                                activebackground="#264f78", activeforeground="#ffffff")
            return

        # ---- vintage-brown chrome ----
        if hasattr(self, "_toolbar"):
            try: self._toolbar.config(bg=extras["toolbar_bg"])
            except Exception: pass

        if hasattr(self, "simple_btn"):
            self._update_simple_button()

        if hasattr(self, "_menus"):
            for name, (btn, menu) in self._menus.items():
                btn.config(bg=extras["menubar_bg"], fg=extras["menubar_fg"],
                           activebackground=extras["menubar_hover"],
                           activeforeground=extras["menubar_active"],
                           font=(extras["font_hint"], 10))
                menu.config(bg=extras["menu_bg"], fg=extras["menu_fg"],
                            activebackground=extras["menu_active_bg"],
                            activeforeground=extras["menu_active_fg"],
                            font=(extras["font_hint"], 10))

    def _apply_theme(self):
        for tab in self.tabs:
            self._apply_theme_to_tab(tab)
        bg, fg, ins, sel, gbg, gfg, sbg, sfg = THEMES.get(self._theme, THEMES["dark"])
        self.status.config(bg=sbg, fg=sfg)
        self._style_ui()

    def _apply_theme_to_tab(self, tab):
        bg, fg, ins, sel, gbg, gfg, sbg, sfg = THEMES.get(self._theme, THEMES["dark"])
        for pane in tab.panes:
            pane.text.config(bg=bg, fg=fg, insertbackground=ins, selectbackground=sel)
            pane.gutter.config(bg=gbg, fg=gfg)
        try:
            tab.paned.config(bg=sbg)
        except Exception:
            pass

    def set_theme(self, name):
        if name not in THEMES: return
        self._theme = name
        self.settings["theme"] = name
        self._apply_theme()
        for tab in self.tabs:
            for pane in tab.panes:
                self._apply_syntax_to(pane)
        self.status.config(text=f" Theme: {name}")

    # ==================== tab/space ====================

    def set_tab_width(self, w):
        self._tab_width = int(w)
        self.settings["tab_width"] = self._tab_width
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.config(tabs=(self._tab_width * 8,))
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
        self._update_gutter_for_pane(self._active_pane())
        self.update_status()

    # ==================== line endings / bom / eof ====================

    def set_line_ending(self, ending):
        if ending not in ("LF", "CRLF", "CR"): return
        self._line_ending = ending
        self.update_status()
        self.status.config(text=f" Line ending: {ending}")

    def toggle_read_only(self, flag):
        self._read_only = bool(flag)
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.config(state="disabled" if self._read_only else "normal")
        if not self._read_only:
            self.text.focus_set()
        self.update_title()
        self.update_status()

    def toggle_eol_markers(self):
        self._show_eol = self.eol_var.get()
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.tag_remove("eol", "1.0", "end")
        if not self._show_eol:
            return
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.tag_configure("eol", foreground="#6a6a6a")
                idx = "1.0"
                while True:
                    nxt = pane.text.search("\n", idx, stopindex="end")
                    if not nxt: break
                    pane.text.tag_add("eol", nxt, f"{nxt}+1c")
                    idx = f"{nxt}+1c"

    def _encode_with_ending(self, text, line_ending=None, has_bom=None):
        le = line_ending or self._line_ending
        bom = has_bom if has_bom is not None else self._has_bom
        if le == "CRLF":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        elif le == "CR":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
        else:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        if self._ensure_eof_newline and not text.endswith(("\n", "\r")):
            text += {"CRLF": "\r\n", "CR": "\r", "LF": "\n"}[le]
        raw = text.encode("utf-8")
        if bom:
            raw = b"\xef\xbb\xbf" + raw
        return raw

    def _detect_bom(self, raw):
        if raw.startswith(b"\xef\xbb\xbf"):
            return True, raw[3:].decode("utf-8", errors="replace")
        return False, raw.decode("utf-8", errors="replace")

    # ==================== file ops ====================

    def open_file(self):
        PathDialog(self.root, "open", initial=str(Path.home()) + os.sep,
                    on_ok=self._open_path)

    def _load_path_into_pane(self, pane, path):
        pane.path = Path(path).expanduser().resolve()
        raw = pane.path.read_bytes()
        if b"\r\n" in raw:
            pane.line_ending = "CRLF"
        elif b"\r" in raw and b"\n" not in raw:
            pane.line_ending = "CR"
        else:
            pane.line_ending = "LF"
        pane.has_bom, text = self._detect_bom(raw)
        pane.text.delete("1.0", "end")
        pane.text.insert("1.0", text)
        pane.dirty = False
        pane.text.edit_modified(False)
        self._update_gutter_for_pane(pane)
        self._apply_syntax_to(pane)

    def _open_path(self, path):
        # reuse active pane if blank
        pane = self._active_pane()
        if pane.path is None and not pane.text.get("1.0", "end-1c").strip():
            self._load_path_into_pane(pane, path)
            self._refresh_tab_title_for_pane(pane)
        else:
            self.new_tab()
            tab = self._active_tab()
            self._load_path_into_pane(tab.panes[0], path)
            self._refresh_tab_title_for_pane(tab.panes[0])
        _push_recent(path)
        self._rebuild_recent_menu()
        self.update_title()
        self.update_status()

    def _save_pane(self, pane):
        if pane.path is None:
            def _on_ok(p):
                pane.path = p
                self._save_pane(pane)
            PathDialog(self.root, "save", initial=str(Path.home() / "notes.md"),
                        on_ok=_on_ok)
            return False
        if self._read_only:
            messagebox.showinfo("Read-only", "File is read-only.")
            return False
        try:
            raw = self._encode_with_ending(pane.text.get("1.0", "end-1c"),
                                            pane.line_ending, pane.has_bom)
            pane.path.write_bytes(raw)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return False
        pane.dirty = False
        pane.text.edit_modified(False)
        self._refresh_tab_title_for_pane(pane)
        _push_recent(pane.path)
        self._rebuild_recent_menu()
        return True

    def save_file(self):
        return self._save_pane(self._active_pane())

    def save_as(self):
        pane = self._active_pane()
        def _on_ok(p):
            pane.path = p
            self._save_pane(pane)
        PathDialog(self.root, "save",
                    initial=str(pane.path) if pane.path else str(Path.home() / "notes.md"),
                    on_ok=_on_ok)

    def revert_file(self):
        pane = self._active_pane()
        if not pane.path or not pane.path.exists(): return
        if not messagebox.askyesno("Revert", f"Discard changes and reload {pane.path.name}?"):
            return
        self._load_path_into_pane(pane, pane.path)
        self._refresh_tab_title_for_pane(pane)
        self.update_title()

    def on_close(self):
        for tab in self.tabs:
            for pane in tab.panes:
                if pane.dirty:
                    self.notebook.select(tab.frame)
                    name = pane.path.name if pane.path else "untitled"
                    ans = messagebox.askyesnocancel("Unsaved changes",
                                                     f"Save changes to {name}?")
                    if ans is None:
                        return
                    if ans:
                        self._save_pane(pane)
        self.save_settings()
        self.root.destroy()

    # ==================== recent ====================

    def _rebuild_recent_menu(self):
        if self.recent_menu is None:
            return
        self.recent_menu.delete(0, "end")
        items = _load_recent()
        if not items:
            self.recent_menu.add_command(label="(empty)", state="disabled")
            return
        for path in items:
            label = path if len(path) < 60 else "…" + path[-57:]
            self.recent_menu.add_command(label=label,
                                          command=lambda p=path: self._open_from_recent(p))
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Clear Recent", command=self._clear_recent)

    def _open_from_recent(self, path):
        p = Path(path)
        if not p.exists():
            messagebox.showwarning("Missing", f"Not found:\n{path}")
            items = _load_recent()
            if path in items: items.remove(path)
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
        system = platform.system()
        try:
            _open_folder(_CONFIG_DIR)
        except Exception:
            messagebox.showinfo("Config folder", str(_CONFIG_DIR))

    # ==================== edit ops ====================

    def insert_datetime(self):
        self.text.insert("insert", datetime.now().strftime("%Y-%m-%d %H:%M"))

    def toggle_wrap(self):
        mode = "word" if self.wrap_var.get() else "none"
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.config(wrap=mode)

    def select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        return "break"

    def duplicate_line(self, event=None):
        try:
            s = self.text.index("insert linestart")
            e = self.text.index("insert lineend")
            line = self.text.get(s, e)
            self.text.insert(e, "\n" + line)
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
            s = self.text.index("insert linestart")
            e = self.text.index("insert lineend")
            line = self.text.get(s, e)
            if line.lstrip().startswith("#"):
                i = line.find("#")
                self.text.delete(s, e)
                self.text.insert(s, line[:i] + line[i+1:].lstrip(" "))
            else:
                self.text.insert(s, "# ")
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

    def goto_line(self, event=None):
        win = tk.Toplevel(self.root)
        win.title("Go to line")
        win.geometry("260x90")
        win.transient(self.root)
        tk.Label(win, text="Line:").pack(side="left", padx=8)
        entry = tk.Entry(win, width=12); entry.pack(side="left", padx=4); entry.focus()

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

    def update_title(self):
        tab = self._active_tab()
        name = tab.title()
        ro = " [RO]" if self._read_only else ""
        self.root.title(f"{name}{ro} — Quillinks")

    def _has_trailing_newline(self):
        content = self.text.get("1.0", "end-1c")
        if not content: return True
        return content.endswith("\n")

    def update_status(self):
        try:
            row, col = self.text.index("insert").split(".")
        except tk.TclError:
            return
        pane = self._active_pane()
        state = "RO" if self._read_only else ("saved" if not pane.dirty else "modified")
        eol = pane.line_ending
        bom = " · BOM" if pane.has_bom else ""
        eof = "" if self._has_trailing_newline() else " · [no-eol]"
        ws = " · ws" if self._show_ws else ""
        tw = f" · tab={self._tab_width}{'sp' if self._use_spaces else 'tab'}"
        tnum = f" · tab {self.notebook.index(self.notebook.select())+1}/{len(self.tabs)}"
        npanes = f" · {len(self._active_tab().panes)} pane(s)"
        self.status.config(
            text=f" Ln {row}, Col {int(col)+1}  ·  {state}  ·  {eol}{bom}{eof}{ws}{tw}{tnum}{npanes}  ·  {self._theme}"
        )

    # ==================== auto-indent ====================

    def toggle_auto_indent(self):
        self._auto_indent = self.ai_var.get()

    def _on_return(self, event=None):
        if not self._auto_indent or self._read_only:
            return None
        try:
            ls = self.text.index("insert linestart")
            cur = self.text.index("insert")
            line = self.text.get(ls, cur)
            indent = ""
            for ch in line:
                if ch in " \t": indent += ch
                else: break
            self.text.insert("insert", "\n" + indent)
            return "break"
        except tk.TclError:
            return None

    # ==================== bracket matching ====================

    def toggle_bracket_match(self):
        self._bracket_match = self.bm_var.get()
        if not self._bracket_match:
            for tab in self.tabs:
                for pane in tab.panes:
                    pane.text.tag_remove("brk", "1.0", "end")

    def _on_keyrelease_brackets(self, event=None):
        if not self._bracket_match: return
        self.text.tag_remove("brk", "1.0", "end")
        self.text.tag_configure("brk", background="#4a4a20", foreground="#ffffff")
        pairs = {"(": ")", "[": "]", "{": "}"}
        rev = {v: k for k, v in pairs.items()}
        cur = self.text.index("insert")
        prev = self.text.index("insert-1c")
        pc = self.text.get(prev, cur)
        cc = self.text.get(cur, f"{cur}+1c")
        for idx, ch in [(prev, pc), (cur, cc)]:
            if ch in pairs:
                m = self._scan_fwd(f"{idx}+1c", pairs[ch], ch)
                if m:
                    self.text.tag_add("brk", idx, f"{idx}+1c")
                    self.text.tag_add("brk", m, f"{m}+1c")
                    return
            elif ch in rev:
                m = self._scan_bwd(f"{idx}-1c", rev[ch], ch)
                if m:
                    self.text.tag_add("brk", idx, f"{idx}+1c")
                    self.text.tag_add("brk", m, f"{m}+1c")
                    return

    def _scan_fwd(self, start, close_ch, open_ch):
        depth = 1
        idx = start
        for _ in range(10000):
            ch = self.text.get(idx, f"{idx}+1c")
            if not ch: return None
            if ch == open_ch: depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0: return idx
            try: nxt = self.text.index(f"{idx}+1c")
            except tk.TclError: return None
            if nxt == idx: return None
            idx = nxt
        return None

    def _scan_bwd(self, start, open_ch, close_ch):
        depth = 1
        idx = start
        for _ in range(10000):
            ch = self.text.get(idx, f"{idx}+1c")
            if not ch: return None
            if ch == close_ch: depth += 1
            elif ch == open_ch:
                depth -= 1
                if depth == 0: return idx
            try: prev = self.text.index(f"{idx}-1c")
            except tk.TclError: return None
            if prev == idx: return None
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
        if ch not in pairs: return None
        close = pairs[ch]
        nxt = self.text.get("insert", "insert+1c")
        if nxt == close: return None
        try:
            s = self.text.index("sel.first"); e = self.text.index("sel.last")
            sel = self.text.get(s, e)
            self.text.delete(s, e)
            self.text.insert(s, ch + sel + close)
            return "break"
        except tk.TclError:
            pass
        self.text.insert("insert", ch + close)
        self.text.mark_set("insert", "insert-1c")
        return "break"

    # ==================== whitespace ====================

    def toggle_whitespace(self):
        self._show_ws = self.ws_var.get()
        for tab in self.tabs:
            for pane in tab.panes:
                if self._show_ws:
                    pane.text.tag_configure("ws_space", background="#3a3a1a")
                    pane.text.tag_configure("ws_tab", background="#3a1a1a")
                else:
                    pane.text.tag_remove("ws_space", "1.0", "end")
                    pane.text.tag_remove("ws_tab", "1.0", "end")
        if self._show_ws:
            self._paint_ws_for(self._active_pane())

    def _paint_ws_for(self, pane):
        pane.text.tag_remove("ws_space", "1.0", "end")
        pane.text.tag_remove("ws_tab", "1.0", "end")
        if not self._show_ws: return
        content = pane.text.get("1.0", "end-1c")
        idx = "1.0"
        for ch in content:
            if ch == " ":
                pane.text.tag_add("ws_space", idx, f"{idx}+1c")
            elif ch == "\t":
                pane.text.tag_add("ws_tab", idx, f"{idx}+1c")
            idx = f"{idx}+1c"

    # ==================== find ====================

    def open_find(self):
        win = tk.Toplevel(self.root)
        win.title("Find & Replace")
        win.geometry("520x300")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")
        win.protocol("WM_DELETE_WINDOW", lambda: (self._clear_highlights(), win.destroy()))

        tk.Label(win, text="Find:", bg="#1e1e1e", fg="#d4d4d4").grid(row=0, column=0, sticky="e", padx=8, pady=6)
        fv = tk.StringVar()
        fc = ttk.Combobox(win, textvariable=fv, width=34, values=_load_search_history())
        fc.grid(row=0, column=1, columnspan=2, padx=4, pady=6, sticky="we"); fc.focus()

        tk.Label(win, text="Replace:", bg="#1e1e1e", fg="#d4d4d4").grid(row=1, column=0, sticky="e", padx=8, pady=6)
        rv = tk.StringVar()
        tk.Entry(win, textvariable=rv, width=34, bg="#252526", fg="#d4d4d4",
                 insertbackground="#d4d4d4").grid(row=1, column=1, columnspan=2, padx=4, pady=6, sticky="we")

        cv = tk.BooleanVar(value=False); wv = tk.BooleanVar(value=False); hv = tk.BooleanVar(value=True)
        opts = tk.Frame(win, bg="#1e1e1e"); opts.grid(row=2, column=0, columnspan=3, pady=4, sticky="w", padx=8)
        for label, var in [("Case sensitive", cv), ("Whole word", wv), ("Highlight all", hv)]:
            tk.Checkbutton(opts, text=label, variable=var, bg="#1e1e1e", fg="#d4d4d4",
                            selectcolor="#2d2d30", activebackground="#1e1e1e",
                            activeforeground="#d4d4d4").pack(side="left", padx=6)

        cl = tk.Label(win, text="", bg="#1e1e1e", fg="#4ec9b0", font=("Sans", 9))
        cl.grid(row=3, column=0, columnspan=3, pady=(4, 8))

        def dh(*a):
            self._clear_highlights()
            t = fv.get()
            if not t: cl.config(text=""); return
            n = self._highlight(t, cv.get(), wv.get(), hv.get())
            cl.config(text="No matches" if n == 0 else f"{n} match{'es' if n != 1 else ''}")

        def fn():
            t = fv.get()
            if not t: return
            _push_search(t); fc.config(values=_load_search_history())
            self.text.tag_remove("match", "1.0", "end")
            idx = "1.0"; c = cv.get(); w = wv.get()
            while True:
                idx = self.text.search(t, idx, nocase=not c, stopindex="end")
                if not idx: break
                e = f"{idx}+{len(t)}c"
                if w:
                    b = self.text.get(f"{idx}-1c", idx); a = self.text.get(e, f"{e}+1c")
                    if (b and (b.isalnum() or b == "_")) or (a and (a.isalnum() or a == "_")):
                        idx = e; continue
                self.text.tag_add("match", idx, e); idx = e
            self.text.tag_config("match", background="#264f78")
            r = self.text.tag_ranges("match")
            if r:
                self.text.mark_set("insert", r[0]); self.text.see(r[0])

        def ra():
            t = fv.get(); r = rv.get()
            if not t: return
            _push_search(t); fc.config(values=_load_search_history())
            content = self.text.get("1.0", "end-1c")
            if cv.get():
                n = content.count(t); new = content.replace(t, r)
            else:
                pat = re.compile(re.escape(t), re.IGNORECASE)
                n = len(pat.findall(content)); new = pat.sub(r, content)
            if n == 0: cl.config(text="No matches"); return
            self._replace_all_content(new)
            cl.config(text=f"Replaced {n}"); dh()

        bf = tk.Frame(win, bg="#1e1e1e"); bf.grid(row=4, column=0, columnspan=3, pady=8)
        tk.Button(bf, text="Find Next", command=fn, width=12).pack(side="left", padx=6)
        tk.Button(bf, text="Replace All", command=ra, width=12).pack(side="left", padx=6)
        tk.Button(bf, text="Close", command=lambda: (self._clear_highlights(), win.destroy()),
                  width=12).pack(side="left", padx=6)
        fv.trace_add("write", dh); cv.trace_add("write", dh); wv.trace_add("write", dh)

    def _clear_highlights(self):
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.tag_remove("hl", "1.0", "end")

    def _highlight(self, term, case, whole, enabled=True):
        self._clear_highlights()
        if not enabled or not term: return 0
        n = 0; idx = "1.0"
        while True:
            idx = self.text.search(term, idx, nocase=not case, stopindex="end")
            if not idx: break
            e = f"{idx}+{len(term)}c"; ok = True
            if whole:
                b = self.text.get(f"{idx}-1c", idx); a = self.text.get(e, f"{e}+1c")
                if b and (b.isalnum() or b == "_"): ok = False
                if a and (a.isalnum() or a == "_"): ok = False
            if ok:
                self.text.tag_add("hl", idx, e); n += 1
            idx = e
        self.text.tag_config("hl", background="#5a4a1a")
        return n

    # ==================== zoom / font ====================

    def _apply_font(self):
        for tab in self.tabs:
            for pane in tab.panes:
                pane.text.config(font=(self._font_family, self._font_size))
                pane.gutter.config(font=(self._font_family, self._font_size))

    def zoom(self, delta):
        self._font_size = max(7, min(28, self._font_size + delta))
        self._apply_font()
        self.status.config(text=f" Font: {self._font_family} {self._font_size}pt")

    def zoom_reset(self):
        self._font_size = 11; self._apply_font()

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
            messagebox.showinfo("Font picker", "plugins/font_picker.py not found.")

    def open_plugin_manager(self):
        try:
            from plugins.plugin_manager import open_plugin_manager
            open_plugin_manager(self.root, on_change=self._on_plugins_changed)
        except ImportError as e:
            messagebox.showerror("Plugin Manager", f"Not available: {e}")

    def _on_plugins_changed(self):
        pass

    # ==================== help ====================

    def show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.geometry("560x720")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")
        tk.Label(win, text="Keyboard Shortcuts", bg="#1e1e1e", fg="#d4d4d4",
                 font=("Sans", 13, "bold")).pack(pady=(12, 8))
        frame = tk.Frame(win, bg="#1e1e1e"); frame.pack(fill="both", expand=True, padx=20)

        rows = [
            ("Tabs / Splits", ""),
            ("Ctrl+T", "New tab"),
            ("Ctrl+W", "Close tab"),
            ("Ctrl+\\", "Toggle split"),
            ("Ctrl+Shift+W", "Close pane"),
            ("Ctrl+PgUp/PgDn", "Prev / next tab"),
            ("", ""),
            ("File", ""),
            ("Ctrl+O", "Open file (path completion)"),
            ("Ctrl+S", "Save"),
            ("Ctrl+Shift+S", "Save As"),
            ("Ctrl+Q", "Quit"),
            ("", ""),
            ("Edit", ""),
            ("Ctrl+A", "Select all"),
            ("Ctrl+Z / Y", "Undo / Redo"),
            ("Ctrl+D", "Duplicate line"),
            ("Ctrl+Shift+K", "Delete line"),
            ("Ctrl+/", "Toggle comment"),
            ("", ""),
            ("Find", ""),
            ("Ctrl+F / H", "Find & Replace"),
            ("Ctrl+G", "Go to line"),
            ("", ""),
            ("View", ""),
            ("Ctrl++ / Ctrl+-", "Zoom"),
            ("Ctrl+0", "Reset zoom"),
            ("Ctrl+Shift+F", "Font picker"),
            ("F11", "Fullscreen"),
            ("", ""),
            ("Path Dialog", ""),
            ("Tab", "Auto-complete path"),
            ("↑ / ↓", "Browse matches"),
            ("Enter", "Accept"),
        ]
        for k, d in rows:
            if not k and not d:
                tk.Frame(frame, height=6, bg="#1e1e1e").pack(); continue
            if not d:
                tk.Label(frame, text=k, bg="#1e1e1e", fg="#4ec9b0",
                         font=("Sans", 11, "bold"), anchor="w").pack(fill="x", pady=(6, 2))
                continue
            row = tk.Frame(frame, bg="#1e1e1e"); row.pack(fill="x")
            tk.Label(row, text=k, bg="#1e1e1e", fg="#dcdcaa",
                     font=("Monospace", 10), width=20, anchor="w").pack(side="left")
            tk.Label(row, text=d, bg="#1e1e1e", fg="#d4d4d4",
                     font=("Sans", 10), anchor="w").pack(side="left")
        tk.Button(win, text="Close", command=win.destroy).pack(pady=12)

    def show_about(self):
        messagebox.showinfo("About Quillinks",
                            "Quillinks — a modern terminal + GUI text editor.\n\n"
                            "Built with Python, Textual, and Tkinter.\n"
                            "github.com/Apersonwithtoenail/QuillInks")

    # ==================== autosave ====================

    def _autosave_tick(self):
        for tab in self.tabs:
            for pane in tab.panes:
                if pane.dirty and pane.path is not None and not self._read_only:
                    try:
                        raw = self._encode_with_ending(pane.text.get("1.0", "end-1c"),
                                                        pane.line_ending, pane.has_bom)
                        pane.path.write_bytes(raw)
                        pane.dirty = False
                        pane.text.edit_modified(False)
                        self._refresh_tab_title_for_pane(pane)
                    except Exception:
                        pass
        self.update_title()
        self.root.after(5000, self._autosave_tick)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    app = QuillinksGUI(arg)
    app.root.mainloop()
