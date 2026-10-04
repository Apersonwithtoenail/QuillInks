#!/usr/bin/env python3
"""Quillinks GTK — modern GTK4 editor shell."""
import os
import sys
from pathlib import Path

# Software rendering for old Intel GPUs (Pentium-era)
if "GSK_RENDERER" not in os.environ:
    os.environ["GSK_RENDERER"] = "cairo"

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Gdk, Gio, GLib, Adw, GtkSource, Pango, PangoCairo  # noqa: E402


# Singleton managers for language/style lookup
_LANG_MGR = GtkSource.LanguageManager.get_default()
_STYLE_MGR = GtkSource.StyleSchemeManager.get_default()


# ══════════════════════════════════════════════════════════════
#  THEME — vintage-brown for the first look
# ══════════════════════════════════════════════════════════════

DARK = {
    "bg":           "#1e1e1e",
    "fg":           "#d4d4d4",
    "accent":       "#6C4AB6",
    "accent2":      "#5a3d99",
    "toolbar_bg":   "#2d2d2d",
    "toolbar_fg":   "#e0e0e0",
    "tab_bg":       "#252526",
    "tab_active":   "#1e1e1e",
    "tab_fg":       "#a0a0a0",
    "status_bg":    "#2d2d2d",
    "status_fg":    "#a0a0a0",
    "border":       "#3d3d3d",
    "hover":        "#3d3d3d",
}

VINTAGE = {
    "bg":           "#2b2118",
    "fg":           "#e8d5b7",
    "accent":       "#d4a373",
    "accent2":      "#8b4513",
    "toolbar_bg":   "#3d2b1f",
    "toolbar_fg":   "#f4e4c1",
    "tab_bg":       "#1f1810",
    "tab_active":   "#2b2118",
    "tab_fg":       "#d4a373",
    "status_bg":    "#3d2b1f",
    "status_fg":    "#d4a373",
    "border":       "#6b4423",
    "hover":        "#5a3d29",
}


HIGH_CONTRAST = {
    "bg":           "#000000",
    "fg":           "#ffffff",
    "accent":       "#ffff00",
    "accent2":      "#cccc00",
    "toolbar_bg":   "#000000",
    "toolbar_fg":   "#ffffff",
    "tab_bg":       "#1a1a1a",
    "tab_active":   "#000000",
    "tab_fg":       "#ffff00",
    "status_bg":    "#000000",
    "status_fg":    "#ffffff",
    "border":       "#ffffff",
    "hover":        "#333333",
}


# ══════════════════════════════════════════════════════════════
#  Config (ported from Tkinter version — pure Python, no UI)
# ══════════════════════════════════════════════════════════════

import json
import platform


def _config_dir():
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


_CONFIG_DIR = _config_dir()
_SETTINGS_FILE = _CONFIG_DIR / "settings.json"
_RECENT_FILE = _CONFIG_DIR / "recent.json"
_SESSION_FILE = _CONFIG_DIR / "session.json"
_HISTORY_FILE = _CONFIG_DIR / "search_history.json"
_MAX_RECENT = 10

DEFAULT_SETTINGS = {
    "font_family": None,
    "font_size": 13,
    "theme": "vintage-brown",
    "wrap": False,
    "show_line_numbers": True,
    "show_whitespace": False,
    "show_eol": False,
    "show_right_margin": True,
    "read_only": False,
    "highlight_line": True,
    "bracket_match": True,
    "auto_indent": True,
    "geometry": "1100x720",
    "reopen_session": True,
    "syntax_highlight": True,
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


def _load_history():
    return _load_json(_HISTORY_FILE, [])[:20]


def _save_history(items):
    _save_json(_HISTORY_FILE, items[:20])


def _push_history(text):
    text = (text or "").strip()
    if not text:
        return
    items = _load_history()
    items = [x for x in items if x != text]
    items.insert(0, text)
    _save_history(items)


def _push_recent(path):
    if not path:
        return
    s = str(Path(path).expanduser().resolve())
    items = _load_recent()
    if s in items:
        items.remove(s)
    items.insert(0, s)
    _save_recent(items)


def css(t):
    return f"""
    window, .background {{
        background: {t['bg']};
        color: {t['fg']};
    }}

    headerbar, .toolbar {{
        background: {t['toolbar_bg']};
        color: {t['toolbar_fg']};
        border: none;
        box-shadow: none;
    }}

    /* ---- menu buttons in toolbar ---- */
    menubutton > button {{
        background: transparent;
        color: {t['toolbar_fg']};
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 600;
        transition: all 180ms ease-out;
    }}
    menubutton > button:hover {{
        background: {t['hover']};
        border-color: {t['border']};
        box-shadow: 0 2px 6px rgba(0,0,0,0.35),
                    inset 0 1px 0 rgba(255,255,255,0.08);
    }}
    menubutton > button:active {{
        background: {t['accent2']};
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
    }}

    /* ---- the Aero button (Simple Mode) ---- */
    button.simple-btn {{
        background-image: linear-gradient(to bottom,
            {t['accent']} 0%,
            {t['accent2']} 50%,
            #6b3408 100%);
        color: #fef6e4;
        border: 1px solid {t['border']};
        border-radius: 14px;
        padding: 6px 18px;
        font-weight: 700;
        text-shadow: 0 1px 1px rgba(0,0,0,0.5);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.35),
                    inset 0 -1px 0 rgba(0,0,0,0.3),
                    0 2px 6px rgba(0,0,0,0.4);
        transition: all 160ms ease-out;
    }}
    button.simple-btn:hover {{
        background-image: linear-gradient(to bottom,
            #e4b888 0%,
            {t['accent']} 50%,
            #8b4513 100%);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.5),
                    inset 0 -1px 0 rgba(0,0,0,0.35),
                    0 3px 10px rgba(0,0,0,0.55);
    }}
    button.simple-btn:active {{
        background-image: linear-gradient(to top,
            {t['accent']} 0%,
            {t['accent2']} 100%);
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.5);
    }}

    /* ---- tab bar ---- */
    notebook > header {{
        background: {t['tab_bg']};
        border: none;
        box-shadow: none;
        padding: 0;
        margin: 0;
    }}
    notebook > header > tabs {{
        background: {t['tab_bg']};
        padding: 0 4px;
    }}

    /* Tab itself — kill ALL default styling */
    notebook > header > tabs > tab {{
        background: {t['tab_bg']};
        color: {t['tab_fg']};
        border: none;
        border-radius: 12px 12px 0 0;
        padding: 8px 18px;
        margin: 6px 3px 0 3px;
        min-height: 24px;
        box-shadow: none;
        outline: none;
        transition: all 180ms cubic-bezier(0.2, 0, 0, 1);
    }}
    notebook > header > tabs > tab:hover {{
        background: {t['hover']};
        color: {t['fg']};
    }}
    notebook > header > tabs > tab:checked,
    notebook > header > tabs > tab:selected {{
        background: {t['tab_active']};
        color: {t['fg']};
        border-radius: 12px 12px 0 0;
        box-shadow: inset 0 3px 0 {t['accent']},
                    0 -3px 10px rgba(0,0,0,0.4);
    }}

    /* Kill the Adwaita underline indicator */
    notebook > header > tabs > tab > box > indicator,
    notebook > header > tabs > tab indicator,
    notebook > header > tabs > tab > indicator {{
        background: transparent;
        min-height: 0;
        min-width: 0;
        opacity: 0;
        border: none;
        box-shadow: none;
    }}

    /* Tab label + close button */
    notebook > header > tabs > tab label {{
        color: inherit;
    }}
    notebook > header > tabs > tab button {{
        color: {t['tab_fg']};
        background: transparent;
        border: none;
        border-radius: 10px;
        min-width: 18px;
        min-height: 18px;
        padding: 0;
        margin-left: 6px;
        box-shadow: none;
        transition: background 140ms ease-out;
    }}
    notebook > header > tabs > tab button:hover {{
        background: {t['accent2']};
        color: #fef6e4;
    }}

    /* ---- text area ---- */
    /* Let GtkSource scheme own the editor background/foreground.
       Only set font here. */
    textview, textview text {{
        font-family: "Monospace", "DejaVu Sans Mono", monospace;
        font-size: 13px;
    }}
    textview > text {{
        background: {t['bg']};
        color: {t['fg']};
    }}

    /* ---- status bar ---- */
    .status-bar {{
        background: {t['status_bg']};
        color: {t['status_fg']};
        border-top: 1px solid {t['border']};
        padding: 8px 14px;
        font-size: 12px;
    }}

    /* ---- scrollbars ---- */
    scrollbar slider {{
        background: {t['border']};
        border-radius: 8px;
        min-width: 6px;
        min-height: 30px;
        transition: all 160ms ease-out;
    }}
    scrollbar slider:hover {{
        background: {t['accent']};
        min-width: 10px;
    }}
    scrollbar trough {{
        background: {t['tab_bg']};
        border-radius: 8px;
    }}

    /* ---- find bar ---- */
    .find-bar-wrap {{
        background: {t['toolbar_bg']};
        border-top: 1px solid {t['border']};
    }}
    .find-bar entry,
    .find-bar searchentry {{
        background: {t['tab_bg']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 20px;
        transition: all 160ms ease-out;
    }}
    .find-bar entry:focus,
    .find-bar searchentry:focus {{
        border-color: {t['accent']};
        box-shadow: 0 0 0 2px {t['accent']}33;
    }}
    .find-bar button,
    .find-bar togglebutton {{
        background: {t['tab_bg']};
        color: {t['tab_fg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 4px 10px;
        min-width: 28px;
        transition: all 140ms ease-out;
    }}
    .find-bar button:hover,
    .find-bar togglebutton:hover {{
        background: {t['hover']};
    }}
    .find-bar togglebutton:checked {{
        background: {t['accent2']};
        color: #fef6e4;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);
    }}
    .find-status {{
        color: {t['accent']};
        font-size: 11px;
    }}

    /* ---- popover menus ---- */
    popover > contents {{
        background: {t['tab_bg']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 6px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.55);
    }}
    popover modelbutton {{
        border-radius: 8px;
        padding: 6px 12px;
        transition: background 120ms ease-out;
    }}
    popover modelbutton:hover {{
        background: {t['hover']};
    }}
    """


def apply_css(theme):
    provider = Gtk.CssProvider()
    provider.load_from_string(css(theme))
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


# ══════════════════════════════════════════════════════════════
#  Custom GtkSource style scheme (matches VINTAGE palette)
# ══════════════════════════════════════════════════════════════

SCHEME_ID = "quillinks-vintage"


def _install_source_scheme():
    """Write a matching GtkSource XML style scheme to disk so syntax colors
    follow our VINTAGE theme. Then register its search path."""
    styles_dir = Path.home() / ".local" / "share" / "gtksourceview-5" / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)
    xml_path = styles_dir / f"{SCHEME_ID}.xml"

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<style-scheme id="quillinks-vintage" name="Quillinks Vintage" version="1.0">
  <author>Apersonwithtoenail</author>
  <description>Warm vintage brown — matches the Quillinks UI</description>

  <color name="bg"       value="#2b2118"/>
  <color name="fg"       value="#e8d5b7"/>
  <color name="keyword"  value="#d4a373"/>
  <color name="string"   value="#9b7653"/>
  <color name="comment"  value="#7a6a55"/>
  <color name="number"   value="#b8956a"/>
  <color name="function" value="#c9a961"/>
  <color name="type"     value="#e0b47f"/>
  <color name="variable" value="#e8d5b7"/>
  <color name="constant" value="#c9a961"/>
  <color name="operator" value="#a68a64"/>
  <color name="bracket"  value="#f4e4c1"/>

  <style name="text"              foreground="fg"       background="bg"/>
  <style name="def:keyword"       foreground="keyword"  bold="true"/>
  <style name="def:statement"     foreground="keyword"/>
  <style name="def:type"          foreground="type"/>
  <style name="def:constant"      foreground="constant" bold="true"/>
  <style name="def:number"        foreground="number"/>
  <style name="def:function"      foreground="function"/>
  <style name="def:identifier"    foreground="variable"/>
  <style name="def:string"        foreground="string"/>
  <style name="def:comment"       foreground="comment"  italic="true"/>
  <style name="def:operator"      foreground="operator"/>
  <style name="def:special-char"  foreground="keyword"/>
  <style name="def:preprocessor"  foreground="keyword"  bold="true"/>
  <style name="def:builtin"       foreground="type"/>

  <style name="def:bracket-match"  foreground="#f4e4c1" background="#6b4423" bold="true"/>
  <style name="def:current-line"   background="#1f1810"/>
  <style name="def:selection"      background="#6b4423"/>
  <style name="def:right-margin"   foreground="#4a3828"/>
  <style name="def:line-numbers"   foreground="#8b7355" background="#1f1810"/>
  <style name="def:cursor"         foreground="#d4a373"/>
</style-scheme>
"""
    xml_path.write_text(xml)

    mgr = GtkSource.StyleSchemeManager.get_default()
    mgr.append_search_path(str(styles_dir))
    return mgr.get_scheme(SCHEME_ID)


# ══════════════════════════════════════════════════════════════
#  Editor tab — a text view + scroll
# ══════════════════════════════════════════════════════════════

class EditorTab(Gtk.Box):
    """A single editor tab: GtkSource.View with syntax highlighting, line numbers,
    bracket matching, auto-indent, current-line highlight — all native."""

    def __init__(self, path=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.path = Path(path).expanduser().resolve() if path else None
        self.dirty = False

        # GtkSource.Buffer with our custom vintage scheme
        self.buffer = GtkSource.Buffer()
        scheme = _install_source_scheme() or _STYLE_MGR.get_scheme("oblivion")
        if scheme:
            self.buffer.set_style_scheme(scheme)
        self.buffer.set_highlight_matching_brackets(True)

        # Buffer state
        self.line_ending = "LF"
        self.has_bom = False
        self.encoding = "utf-8"
        self._backed_up = False
        self._last_saved_mtime = 0

        # Load file
        if self.path and self.path.exists():
            self._load_from_disk()

        # Auto-detect language by extension
        self._apply_language()

        # GtkSource.View
        self.view = GtkSource.View(buffer=self.buffer)
        self.view.set_monospace(True)
        self.view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.view.set_show_line_numbers(True)
        self.view.set_highlight_current_line(True)
        self.view.set_auto_indent(True)
        self.view.set_insert_spaces_instead_of_tabs(True)
        self.view.set_tab_width(4)
        self.view.set_left_margin(8)
        self.view.set_right_margin(8)
        self.view.set_show_right_margin(True)
        self.view.set_right_margin_position(80)

        self.view.add_css_class("ql-editor")
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.view)
        self.append(scrolled)

        self.buffer.connect("changed", self._on_changed)

    def _load_from_disk(self):
        raw = self.path.read_bytes()
        if b"\r\n" in raw:
            self.line_ending = "CRLF"
        elif b"\r" in raw and b"\n" not in raw:
            self.line_ending = "CR"
        else:
            self.line_ending = "LF"
        if raw.startswith(b"\xef\xbb\xbf"):
            self.has_bom = True
            raw = raw[3:]
        try:
            text = raw.decode("utf-8")
            self.encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            self.encoding = "latin-1"
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.buffer.set_text(text)
        self.dirty = False

    def save_to_disk(self):
        if not self.path:
            return False, "No path"
        text = self.buffer.get_text(
            self.buffer.get_start_iter(),
            self.buffer.get_end_iter(),
            False)
        if text and not text.endswith("\n"):
            text += "\n"
        if self.line_ending == "CRLF":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        elif self.line_ending == "CR":
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")

        enc = getattr(self, "encoding", "utf-8")
        try:
            raw = text.encode(enc)
        except Exception:
            enc = "utf-8"
            raw = text.encode(enc)
        if self.has_bom and enc == "utf-8":
            raw = b"\xef\xbb\xbf" + raw

        # First-save backup of the original
        if self.path.exists() and not getattr(self, "_backed_up", False):
            try:
                import shutil as _sh
                _sh.copy2(self.path, str(self.path) + ".bak")
                self._backed_up = True
            except Exception:
                pass

        try:
            self.path.write_bytes(raw)
        except OSError as e:
            import errno as _errno
            if e.errno == _errno.ENOSPC:
                return False, f"Disk full: {self.path}"
            return False, str(e)
        self.dirty = False
        try:
            self._last_saved_mtime = self.path.stat().st_mtime
        except Exception:
            self._last_saved_mtime = 0
        return True, ""

    def _apply_language(self):
        if not self.path:
            lang = _LANG_MGR.get_language("markdown")
        else:
            lang = _LANG_MGR.guess_language(self.path.name, None)
            if lang is None:
                lang = _LANG_MGR.get_language("text")
        if lang:
            self.buffer.set_language(lang)

    def _on_changed(self, _buf):
        self.dirty = True

    def title(self):
        name = self.path.name if self.path else "untitled"
        return "● " + name if self.dirty else name


# ══════════════════════════════════════════════════════════════
#  Find / Replace bar (bottom overlay)
# ══════════════════════════════════════════════════════════════

class FindBar(Gtk.Revealer):
    """Bottom find/replace bar. Uses native GtkSource.SearchContext."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(180)

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.add_css_class("find-bar")
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        outer.set_margin_top(8)
        outer.set_margin_bottom(8)

        # --- search row ---
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Find…")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_enter)
        outer.append(self.search_entry)

        self.history_btn = Gtk.MenuButton()
        self.history_btn.set_icon_name("document-open-recent-symbolic")
        self.history_btn.set_tooltip_text("Recent searches")
        self._hist_popover = None
        self._hist_box = None
        self._rebuild_history_menu()
        outer.append(self.history_btn)

        # options
        self.case_btn = self._toggle("Aa", "Case sensitive", self._on_search_changed)
        outer.append(self.case_btn)
        self.word_btn = self._toggle("Ab", "Whole word", self._on_search_changed)
        outer.append(self.word_btn)
        self.regex_btn = self._toggle(".*", "Regex", self._on_search_changed)
        outer.append(self.regex_btn)

        # nav
        prev = Gtk.Button(label="▲")
        prev.set_tooltip_text("Previous")
        prev.connect("clicked", lambda *_: self.find_prev())
        outer.append(prev)

        nxt = Gtk.Button(label="▼")
        nxt.set_tooltip_text("Next")
        nxt.connect("clicked", lambda *_: self.find_next())
        outer.append(nxt)

        close = Gtk.Button(label="✕")
        close.connect("clicked", lambda *_: self.hide_bar())
        outer.append(close)

        # --- replace row ---
        replace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        replace_box.set_margin_start(12)
        replace_box.set_margin_end(12)
        replace_box.set_margin_bottom(8)
        replace_box.add_css_class("find-bar")

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace…")
        self.replace_entry.set_hexpand(True)
        self.replace_entry.connect("activate", lambda *_: self.replace_one())
        replace_box.append(self.replace_entry)

        rep_one = Gtk.Button(label="Replace")
        rep_one.connect("clicked", lambda *_: self.replace_one())
        replace_box.append(rep_one)

        rep_all = Gtk.Button(label="Replace All")
        rep_all.connect("clicked", lambda *_: self.replace_all())
        replace_box.append(rep_all)

        # --- status label ---
        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("find-status")
        self.status_label.set_halign(Gtk.Align.END)
        self.status_label.set_margin_end(16)
        self.status_label.set_margin_bottom(4)

        # --- wrap ---
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrapper.add_css_class("find-bar-wrap")
        wrapper.append(outer)
        wrapper.append(replace_box)
        wrapper.append(self.status_label)
        self.set_child(wrapper)

        self._replace_visible = False

    def _on_enter(self, *_):
        _push_history(self.search_entry.get_text())
        self._rebuild_history_menu()
        self.find_next()

    def _rebuild_history_menu(self):
        if self._hist_popover is None:
            self._hist_popover = Gtk.Popover()
            self._hist_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            self._hist_box.set_margin_start(4)
            self._hist_box.set_margin_end(4)
            self._hist_box.set_margin_top(4)
            self._hist_box.set_margin_bottom(4)
            self._hist_popover.set_child(self._hist_box)
            self.history_btn.set_popover(self._hist_popover)

        child = self._hist_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._hist_box.remove(child)
            child = nxt

        items = _load_history()
        if not items:
            lbl = Gtk.Label(label="No recent searches")
            lbl.set_margin_start(8)
            lbl.set_margin_end(8)
            lbl.set_margin_top(6)
            lbl.set_margin_bottom(6)
            self._hist_box.append(lbl)
            return
        for item in items:
            b = Gtk.Button(label=item)
            b.set_has_frame(False)
            if b.get_child():
                b.get_child().set_xalign(0)
            b.connect("clicked", lambda _b, t=item: self._apply_history(t))
            self._hist_box.append(b)

    def _apply_history(self, text):
        self.search_entry.set_text(text)
        if self._hist_popover:
            self._hist_popover.popdown()
        self._on_search_changed()

    def _toggle(self, label, tooltip, cb):
        b = Gtk.ToggleButton(label=label)
        b.set_tooltip_text(tooltip)
        b.connect("toggled", lambda *_: cb())
        return b

    # ---------- show / hide ----------
    def toggle_bar(self, replace=False):
        # Ctrl+F pressed while already shown → close
        if self.get_reveal_child():
            self.hide_bar()
            return
        self.set_reveal_child(True)
        if replace:
            self._show_replace()
        self.search_entry.grab_focus()
        self._on_search_changed()

    def show_bar(self, replace=False):
        self.set_reveal_child(True)
        if replace:
            self._show_replace()
        self.search_entry.grab_focus()
        self._on_search_changed()

    def hide_bar(self):
        self.set_reveal_child(False)
        tab = self.window._active_tab()
        if tab:
            tab.view.grab_focus()

    def _show_replace(self):
        self._replace_visible = True
        self.replace_entry.set_visible(True)

    # ---------- context helpers ----------
    def _active_context(self):
        tab = self.window._active_tab()
        if not tab:
            return None, None
        settings = tab.buffer.get_search_context().get_settings() \
            if hasattr(tab.buffer, "get_search_context") else None
        # Rebuild fresh each time to pick up settings changes.
        # Use set_property — method names differ across GtkSource versions.
        s = GtkSource.SearchSettings()
        s.set_property("case-sensitive", self.case_btn.get_active())
        s.set_property("whole-word-matches", self.word_btn.get_active())
        s.set_property("regex-enabled", self.regex_btn.get_active())
        s.set_property("search-text", self.search_entry.get_text())
        ctx = GtkSource.SearchContext.new(tab.buffer, s)
        ctx.set_highlight(True)
        return tab, ctx

    # ---------- events ----------
    def _on_search_changed(self, *_):
        tab, ctx = self._active_context()
        if not tab or not self.search_entry.get_text():
            self.status_label.set_text("")
            return
        # Highlight all by wrapping through context
        buf = tab.buffer
        start = buf.get_start_iter()
        count = 0
        while True:
            match = ctx.forward(start)
            if match is None or match[0] is None:
                break
            start = match[1]
            count += 1
            if count > 5000:
                break
        if count == 0:
            self.status_label.set_text("no matches")
        else:
            self.status_label.set_text(f"{count} match{'es' if count != 1 else ''}")

    def find_next(self):
        tab, ctx = self._active_context()
        if not tab: return
        buf = tab.buffer
        insert = buf.get_iter_at_mark(buf.get_insert())
        match = ctx.forward(insert)
        if match is None or match[0] is None:
            # wrap
            match = ctx.forward(buf.get_start_iter())
        if match and match[0]:
            buf.select_range(match[0], match[1])
            tab.view.scroll_to_iter(match[0], 0.0, False, 0.0, 0.0)

    def find_prev(self):
        tab, ctx = self._active_context()
        if not tab: return
        buf = tab.buffer
        insert = buf.get_iter_at_mark(buf.get_insert())
        match = ctx.backward(insert)
        if match is None or match[0] is None:
            match = ctx.backward(buf.get_end_iter())
        if match and match[0]:
            buf.select_range(match[0], match[1])
            tab.view.scroll_to_iter(match[0], 0.0, False, 0.0, 0.0)

    def replace_one(self):
        tab, ctx = self._active_context()
        if not tab: return
        buf = tab.buffer
        match = ctx.get_match()
        if match is None:
            self.find_next()
            return
        # get match location from current selection
        try:
            s = buf.get_iter_at_mark(buf.get_selection_bound())
            e = buf.get_iter_at_mark(buf.get_insert())
            if s.get_offset() > e.get_offset():
                s, e = e, s
            text = self.replace_entry.get_text()
            buf.begin_user_action()
            buf.delete(s, e)
            buf.insert(s, text)
            buf.end_user_action()
        except Exception:
            pass
        self.find_next()

    def replace_all(self):
        tab, ctx = self._active_context()
        if not tab: return
        buf = tab.buffer
        replacement = self.replace_entry.get_text()
        count = 0
        buf.begin_user_action()
        # iterate over all matches, replacing
        start = buf.get_start_iter()
        while True:
            match = ctx.forward(start)
            if match is None or match[0] is None:
                break
            s, e = match
            # insert replacement
            buf.delete(s, e)
            buf.insert(s, replacement)
            # move to end of inserted replacement
            start = s.copy()
            start.forward_chars(len(replacement))
            count += 1
            if count > 5000:
                break
        buf.end_user_action()
        self.status_label.set_text(f"replaced {count}")


# ══════════════════════════════════════════════════════════════
#  Main window
# ══════════════════════════════════════════════════════════════

class QuillinksWindow(Gtk.ApplicationWindow):
    def __init__(self, app, initial_paths=None):
        super().__init__(application=app, title="Quillinks")
        self.settings = _load_settings()
        self._initial_paths = initial_paths or []
        self._install_shortcuts()
        self._hc_provider = None
        self._font_provider = None
        if self.settings.get("theme") == "high-contrast":
            self.toggle_high_contrast(True)
        self._apply_font_css()
        GLib.timeout_add_seconds(30, self._autosave_tick)

        # Restore geometry
        try:
            w, h = self.settings.get("geometry", "1100x720").split("x")
            self.set_default_size(int(w), int(h))
        except Exception:
            self.set_default_size(1100, 720)

        self.status = None  # created below; guarded in _refresh_status
        self._font_size = int(self.settings.get("font_size", 13))
        self._read_only = bool(self.settings.get("read_only", False))

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        # ---- toolbar row ----
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.add_css_class("toolbar")
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)

        # menu bar as menu buttons
        toolbar.append(self._make_menu("File", [
            ("New", self.on_new),
            ("Open…", self.on_open),
            ("Save", self.on_save),
            ("Save As…", self.on_save_as),
            ("Open by Path…", self.on_open_path),
            ("-", None),
            ("Open Recent…", self.on_recent),
            ("-", None),
            ("Revert", self.on_revert),
            ("-", None),
            ("Line Endings: LF",   lambda *_: self.set_line_ending("LF")),
            ("Line Endings: CRLF", lambda *_: self.set_line_ending("CRLF")),
            ("Line Endings: CR",   lambda *_: self.set_line_ending("CR")),
            ("Encoding: UTF-8",    lambda *_: self.set_encoding("utf-8")),
            ("Encoding: Latin-1",  lambda *_: self.set_encoding("latin-1")),
            ("-", None),
            ("Quit", self.on_quit),
        ]))
        toolbar.append(self._make_menu("Edit", [
            ("Undo", lambda *_: self._do("undo")),
            ("Redo", lambda *_: self._do("redo")),
            "-",
            ("Cut", lambda *_: self._do("cut")),
            ("Copy", lambda *_: self._do("copy")),
            ("Paste", lambda *_: self._do("paste")),
            ("Select All", lambda *_: self._do("select_all")),
            "-",
            ("Go to Line…", self.on_goto_line),
            "-",
            ("Duplicate Line", self.duplicate_line),
            ("Delete Line", self.delete_line),
            ("Toggle Comment", self.toggle_comment),
            "-",
            ("UPPERCASE Selection", self.uppercase_selection),
            ("lowercase Selection", self.lowercase_selection),
            ("Sort Lines", self.sort_lines),
            ("Trim Trailing Whitespace", self.trim_trailing),
            "-",
            ("Tabs to Spaces (4)", self.tabs_to_spaces),
            ("Spaces to Tabs", self.spaces_to_tabs),
        ]))
        toolbar.append(self._make_menu("View", [
            ("Line Numbers", self.toggle_line_numbers, True, self.settings.get("show_line_numbers", True)),
            ("Word Wrap", self.toggle_word_wrap, True, self.settings.get("wrap", False)),
            ("Highlight Current Line", self.toggle_highlight_line, True, self.settings.get("highlight_line", True)),
            ("Right Margin (col 80)", self.toggle_right_margin, True, self.settings.get("show_right_margin", True)),
            ("Bracket Matching", self.toggle_bracket_match, True, self.settings.get("bracket_match", True)),
            ("Auto-indent", self.toggle_auto_indent, True, self.settings.get("auto_indent", True)),
            ("Show Whitespace", self.toggle_whitespace, True, self.settings.get("show_whitespace", False)),
            ("Show EOL Markers", self.toggle_eol_markers, True, self.settings.get("show_eol", False)),
            "-",
            ("Read-Only", self.toggle_read_only, True, self.settings.get("read_only", False)),
            "-",
            ("Zoom In", self.zoom_in),
            ("Zoom Out", self.zoom_out),
            ("Reset Zoom", self.zoom_reset),
            "-",
            ("Fullscreen", self.toggle_fullscreen, True, False),
            "-",
            ("Split View", self.toggle_split, True, False),
            "-",
            ("Font…", self.on_font_picker),
            ("High Contrast", self.toggle_high_contrast, True,
             self.settings.get("theme", "vintage-brown") == "high-contrast"),
        ]))
        toolbar.append(self._make_menu("Help", [
            ("Keyboard Shortcuts", self.on_help),
            "-",
            ("About", self.on_about),
        ]))

        # spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Aero-style Simple Mode button
        self.simple_btn = Gtk.Button(label="◀ Simple Mode")
        self.simple_btn.add_css_class("simple-btn")
        self.simple_btn.connect("clicked", self.on_toggle_simple)
        toolbar.append(self.simple_btn)

        root.append(toolbar)

        # ---- notebook (tabs) ----
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        self.notebook.connect("switch-page", self._on_tab_switch)

        self.tabs = []
        # Restore session or open files from CLI args
        to_open = list(self._initial_paths)
        if not to_open and self.settings.get("reopen_session", True):
            session = _load_json(_SESSION_FILE, {})
            raw_items = session.get("open_files", [])
            to_open = []
            for item in raw_items:
                if isinstance(item, dict):
                    path = item.get("path")
                    line = item.get("line", 0)
                    if path and Path(path).exists():
                        to_open.append((path, line))
                elif isinstance(item, str):
                    if Path(item).exists():
                        to_open.append((item, 0))
        if to_open:
            for item in to_open:
                if isinstance(item, (list, tuple)) and len(item) >= 1:
                    path = item[0]
                    line = item[1] if len(item) > 1 else 0
                    tab = self._add_tab(path)
                    if tab and isinstance(line, int) and line > 0:
                        try:
                            tab.buffer.place_cursor(tab.buffer.get_iter_at_line(line))
                        except Exception:
                            pass
                else:
                    self._add_tab(item)
        else:
            self._add_tab()
        root.append(self.notebook)

        # ---- find bar (hidden until Ctrl+F) ----
        self.find_bar = FindBar(self)
        self.find_bar.set_reveal_child(False)
        root.append(self.find_bar)

        # ---- status bar ----
        self.status = Gtk.Label(label=" Ready")
        self.status.add_css_class("status-bar")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_xalign(0)
        root.append(self.status)

        # ---- keyboard shortcuts ----
        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)

        def _bind(keys, cb):
            trigger = Gtk.ShortcutTrigger.parse_string(keys)
            action = Gtk.CallbackAction.new(lambda *a: (cb(), True)[1])
            controller.add_shortcut(Gtk.Shortcut.new(trigger, action))

        _bind("<Control>f", lambda: self.find_bar.toggle_bar(replace=False))
        _bind("<Control>h", lambda: self.find_bar.show_bar(replace=True))
        _bind("<Control>r", lambda: self.find_bar.show_bar(replace=True))
        _bind("Escape", lambda: self.find_bar.hide_bar())
        _bind("<Control>n", self.on_new)
        _bind("<Control>o", self.on_open)
        _bind("<Control>s", self.on_save)
        _bind("<Control>q", self.on_quit)

        self.add_controller(controller)

        self._refresh_status()
        self.connect("close-request", self._on_close)

    # ---------- helpers ----------

    def _make_menu(self, label, items):
        btn = Gtk.MenuButton(label=label)
        popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(4)
        for item in items:
            # support: "label", "-", (label, cb), (label, cb, True, state)
            if item == "-" or (isinstance(item, tuple) and len(item) >= 1 and item[0] == "-"):
                vbox.append(Gtk.Separator())
                continue
            if isinstance(item, str):
                name, cb, is_check, initial = item, None, False, False
            elif len(item) == 2:
                name, cb = item
                is_check, initial = False, False
            else:
                name, cb, is_check, initial = item

            if is_check:
                chk = Gtk.CheckButton(label=name)
                chk.set_active(initial)
                if cb:
                    chk.connect("toggled", lambda b, c=cb: c(b.get_active()))
                vbox.append(chk)
            else:
                b = Gtk.Button(label=name)
                b.set_has_frame(False)
                b.set_halign(Gtk.Align.FILL)
                b.get_child().set_xalign(0)
                if cb:
                    b.connect("clicked", lambda _b, c=cb: (c(None), popover.popdown()))
                else:
                    b.set_sensitive(False)
                vbox.append(b)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_propagate_natural_height(True)
        sw.set_max_content_height(460)
        sw.set_child(vbox)
        popover.set_child(sw)
        btn.set_popover(popover)
        return btn

    def _apply_whitespace(self, view):
        st = GtkSource.SpaceTypeFlags
        types = st.NONE
        if self.settings.get("show_whitespace"):
            types |= st.SPACE | st.TAB | st.NBSP
        if self.settings.get("show_eol"):
            types |= st.NEWLINE
        d = view.get_space_drawer()
        d.set_types_for_locations(GtkSource.SpaceLocationFlags.ALL, types)
        d.set_enable_matrix(int(types) != 0)

    def _apply_settings_to_tab(self, tab):
        s = self.settings
        tab.view.set_show_line_numbers(bool(s.get("show_line_numbers", True)))
        tab.view.set_wrap_mode(Gtk.WrapMode.WORD if s.get("wrap") else Gtk.WrapMode.NONE)
        tab.view.set_highlight_current_line(bool(s.get("highlight_line", True)))
        tab.view.set_show_right_margin(bool(s.get("show_right_margin", True)))
        tab.buffer.set_highlight_matching_brackets(bool(s.get("bracket_match", True)))
        tab.view.set_auto_indent(bool(s.get("auto_indent", True)))
        tab.view.set_editable(not s.get("read_only", False))
        self._apply_whitespace(tab.view)
        fam = s.get("font_family") or "Monospace"
        fd = Pango.FontDescription()
        fd.set_family(fam)
        fd.set_size(int(s.get("font_size", 13)) * Pango.SCALE)
        try:
            tab.view.override_font(fd)
        except Exception:
            pass

    # ---------- View toggles ----------

    def _tabs_iter(self):
        for t in self.tabs:
            yield t

    def toggle_line_numbers(self, on):
        self.settings["show_line_numbers"] = bool(on)
        for t in self._tabs_iter():
            t.view.set_show_line_numbers(bool(on))

    def toggle_word_wrap(self, on):
        self.settings["wrap"] = bool(on)
        mode = Gtk.WrapMode.WORD if on else Gtk.WrapMode.NONE
        for t in self._tabs_iter():
            t.view.set_wrap_mode(mode)

    def toggle_highlight_line(self, on):
        self.settings["highlight_line"] = bool(on)
        for t in self._tabs_iter():
            t.view.set_highlight_current_line(bool(on))

    def toggle_right_margin(self, on):
        self.settings["show_right_margin"] = bool(on)
        for t in self._tabs_iter():
            t.view.set_show_right_margin(bool(on))

    def toggle_bracket_match(self, on):
        self.settings["bracket_match"] = bool(on)
        for t in self._tabs_iter():
            t.buffer.set_highlight_matching_brackets(bool(on))

    def toggle_auto_indent(self, on):
        self.settings["auto_indent"] = bool(on)
        for t in self._tabs_iter():
            t.view.set_auto_indent(bool(on))

    def toggle_whitespace(self, on):
        self.settings["show_whitespace"] = bool(on)
        for t in self._tabs_iter():
            self._apply_whitespace(t.view)

    def toggle_eol_markers(self, on):
        self.settings["show_eol"] = bool(on)
        for t in self._tabs_iter():
            self._apply_whitespace(t.view)

    def toggle_read_only(self, on):
        self.settings["read_only"] = bool(on)
        for t in self._tabs_iter():
            t.view.set_editable(not on)
        self._read_only = bool(on)
        self._refresh_status()

    # ---------- Zoom ----------

    def _apply_font_css(self):
        # Direct override — CSS classes don't cascade into GtkSource.View
        # inner text node reliably on older GTK4 builds.
        family = self.settings.get("font_family") or "Monospace"
        size = getattr(self, "_font_size", 13)
        fd = Pango.FontDescription()
        fd.set_family(family)
        fd.set_size(int(size) * Pango.SCALE)
        for t in getattr(self, "tabs", []) or []:
            try:
                t.view.override_font(fd)
            except Exception:
                pass

    def zoom_in(self, *_):
        self._font_size = min(28, getattr(self, "_font_size", 13) + 1)
        self.settings["font_size"] = self._font_size
        self._apply_font_css()

    def zoom_out(self, *_):
        self._font_size = max(8, getattr(self, "_font_size", 13) - 1)
        self.settings["font_size"] = self._font_size
        self._apply_font_css()

    def zoom_reset(self, *_):
        self._font_size = 13
        self.settings["font_size"] = self._font_size
        self._apply_font_css()

    def toggle_fullscreen(self, on):
        if on:
            self.fullscreen()
        else:
            self.unfullscreen()

    # ---------- Keyboard shortcuts ----------

    def _install_shortcuts(self):
        ctrl = Gtk.ShortcutController()
        ctrl.set_scope(Gtk.ShortcutScope.GLOBAL)

        def _make(keys, cb):
            def _handle(_w, _args, _data):
                try:
                    cb()
                except Exception:
                    pass
                return True
            action = Gtk.CallbackAction.new(_handle, cb)
            trigger = Gtk.ShortcutTrigger.parse_string(keys)
            return Gtk.Shortcut.new(trigger, action)

        bindings = [
            ("<Control>t", self.on_new),
            ("<Control>o", self.on_open),
            ("<Control>s", self.on_save),
            ("<Control><Shift>o", self.on_open_path),
            ("<Control><Shift>s", self.on_save_as),
            ("<Control>q", self.on_quit),
            ("<Control>z", lambda: self._do("undo")),
            ("<Control>y", lambda: self._do("redo")),
            ("<Control><Shift>z", lambda: self._do("redo")),
            ("<Control><Shift>d", self.duplicate_line),
            ("<Control>g", self.on_goto_line),
            ("<Control>backslash", lambda: self.toggle_split(not bool(getattr(self, "_split_paned", None)))),
            ("<Control>w", lambda: self._close_tab(self._active_tab())),
            ("<Control>Tab", lambda: self.notebook.next_page()),
            ("<Control>Page_Down", lambda: self.notebook.next_page()),
            ("<Control><Shift>Tab", lambda: self.notebook.prev_page()),
            ("<Control>Page_Up", lambda: self.notebook.prev_page()),
            ("<Control><Shift>k", self.delete_line),
            ("<Control>slash", self.toggle_comment),
            ("<Control>equal", self.zoom_in),
            ("<Control>plus", self.zoom_in),
            ("<Control>minus", self.zoom_out),
            ("<Control>0", self.zoom_reset),
            ("F11", lambda: self.toggle_fullscreen(not self.is_fullscreen())),
        ]

        # Find / Replace — pick whichever method the window exposes
        find_cb = (getattr(self, "on_find", None)
                   or getattr(self, "show_find", None)
                   or getattr(self, "_toggle_find", None))
        if find_cb:
            bindings.append(("<Control>f", find_cb))

        for keys, cb in bindings:
            ctrl.add_shortcut(_make(keys, cb))

        self.add_controller(ctrl)

    # ---------- Edit utilities ----------

    def on_goto_line(self, *_):
        tab = self._active_tab()
        if not tab:
            return
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Go to line",
            body="Enter line number:",
        )
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("go", "Go")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("go")

        def _resp(d, r):
            if r != "go":
                return
            try:
                n = int(entry.get_text().strip())
                if n < 1:
                    return
                it = tab.buffer.get_iter_at_line(n - 1)
                tab.buffer.place_cursor(it)
                tab.view.scroll_to_iter(it, 0.1, True, 0.0, 0.0)
            except (ValueError, IndexError):
                pass

        dialog.connect("response", _resp)
        dialog.present()

    def _line_bounds(self, tab):
        it = tab.buffer.get_iter_at_mark(tab.buffer.get_insert())
        start = it.copy()
        start.set_line_offset(0)
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        return start, end

    def duplicate_line(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        start, end = self._line_bounds(tab)
        text = b.get_text(start, end, False)
        ins = end.copy()
        if not ins.ends_line():
            ins.forward_to_line_end()
        b.begin_user_action()
        b.insert(ins, "\n" + text)
        b.end_user_action()

    def delete_line(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        start, end = self._line_bounds(tab)
        kill = end.copy()
        kill.forward_char()
        b.begin_user_action()
        b.delete(start, kill)
        b.end_user_action()

    def toggle_comment(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        has_sel, s, e = b.get_selection_bounds()
        if not has_sel:
            s, e = self._line_bounds(tab)
        lstart = s.get_line()
        lend = e.get_line()
        all_commented = True
        for ln in range(lstart, lend + 1):
            it = b.get_iter_at_line(ln)
            line_end = it.copy()
            line_end.forward_to_line_end()
            txt = b.get_text(it, line_end, False)
            if txt.strip() and not txt.lstrip().startswith("#"):
                all_commented = False
                break
        b.begin_user_action()
        for ln in range(lstart, lend + 1):
            it = b.get_iter_at_line(ln)
            line_end = it.copy()
            line_end.forward_to_line_end()
            txt = b.get_text(it, line_end, False)
            if not txt.strip():
                continue
            if all_commented:
                hash_pos = txt.find("#")
                if hash_pos >= 0:
                    s2 = b.get_iter_at_line_offset(ln, hash_pos)
                    e2 = b.get_iter_at_line_offset(ln, hash_pos + 1)
                    b.delete(s2, e2)
            else:
                b.insert(it, "# ")
        b.end_user_action()

    def uppercase_selection(self, *_):
        self._transform_selection(str.upper)

    def lowercase_selection(self, *_):
        self._transform_selection(str.lower)

    def _transform_selection(self, fn):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        has_sel, s, e = b.get_selection_bounds()
        if not has_sel:
            s, e = self._line_bounds(tab)
        txt = b.get_text(s, e, False)
        b.begin_user_action()
        b.delete(s, e)
        b.insert(s, fn(txt))
        b.end_user_action()

    def sort_lines(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        has_sel, s, e = b.get_selection_bounds()
        if not has_sel:
            s = b.get_start_iter()
            e = b.get_end_iter()
        txt = b.get_text(s, e, False)
        lines = txt.split("\n")
        lines.sort(key=lambda x: x.lower())
        b.begin_user_action()
        b.delete(s, e)
        b.insert(s, "\n".join(lines))
        b.end_user_action()

    def trim_trailing(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        txt = b.get_text(b.get_start_iter(), b.get_end_iter(), False)
        out = "\n".join(line.rstrip() for line in txt.split("\n"))
        if out == txt:
            return
        b.begin_user_action()
        b.set_text(out)
        b.end_user_action()

    def tabs_to_spaces(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        txt = b.get_text(b.get_start_iter(), b.get_end_iter(), False)
        out = txt.replace("\t", "    ")
        if out == txt:
            return
        b.begin_user_action()
        b.set_text(out)
        b.end_user_action()

    def spaces_to_tabs(self, *_):
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return
        b = tab.buffer
        txt = b.get_text(b.get_start_iter(), b.get_end_iter(), False)
        out = txt.replace("    ", "\t")
        if out == txt:
            return
        b.begin_user_action()
        b.set_text(out)
        b.end_user_action()

    def _on_auto_pair(self, ctrl, keyval, keycode, state):
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        name = Gdk.keyval_name(keyval)
        pairs = {
            "parenleft": ("(", ")"),
            "bracketleft": ("[", "]"),
            "braceleft": ("{", "}"),
            "quotedbl": ('"', '"'),
            "apostrophe": ("'", "'"),
        }
        if name not in pairs:
            return False
        op, cl = pairs[name]
        tab = self._active_tab()
        if not tab or not tab.view.get_editable():
            return False
        b = tab.buffer
        has_sel, s, e = b.get_selection_bounds()
        b.begin_user_action()
        if has_sel:
            txt = b.get_text(s, e, False)
            b.delete(s, e)
            b.insert(s, op + txt + cl)
        else:
            b.insert_at_cursor(op + cl)
            it = b.get_iter_at_mark(b.get_insert())
            it.backward_char()
            b.place_cursor(it)
        b.end_user_action()
        return True

    def on_help(self, *_):
        text = (
            "Ctrl+N        New file\n"
            "Ctrl+O        Open file\n"
            "Ctrl+S        Save\n"
            "Ctrl+Shift+S  Save As\n"
            "Ctrl+W        Close tab\n"
            "Ctrl+Q        Quit\n\n"
            "Ctrl+Z        Undo\n"
            "Ctrl+Y        Redo\n"
            "Ctrl+X/C/V    Cut / Copy / Paste\n"
            "Ctrl+A        Select all\n"
            "Ctrl+D        Duplicate line\n"
            "Ctrl+/        Toggle comment\n"
            "Ctrl+G        Go to line\n\n"
            "Ctrl++/-      Zoom in / out\n"
            "Ctrl+0        Reset zoom\n"
            "F11           Fullscreen"
        )
        d = Adw.MessageDialog(transient_for=self, heading="Keyboard Shortcuts", body=text)
        d.add_response("ok", "Close")
        d.present()

    def on_font_picker(self, *_):
        # Lightweight popover: searchable list of families, no preview pane.
        # The GTK4 FontDialog re-renders a live preview on every keystroke
        # and crawls on the P6200 with software rendering.
        win = Gtk.Window()
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_title("Choose Font")
        win.set_default_size(300, 420)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(8); box.set_margin_end(8)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_size_request(260, 340)

        entry = Gtk.SearchEntry()
        entry.set_placeholder_text("Filter fonts…")
        box.append(entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled.set_child(listbox)
        box.append(scrolled)

        # Enumerate families once — cheap, no rendering
        try:
            fm = PangoCairo.FontMap.get_default()
            all_fams = sorted({f.get_name() for f in fm.list_families()},
                              key=lambda x: x.lower())
        except Exception:
            all_fams = ["Monospace", "Sans", "Serif"]

        current = self.settings.get("font_family") or "Monospace"

        def _populate(filter_text=""):
            child = listbox.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                listbox.remove(child)
                child = nxt
            ft = filter_text.strip().lower()
            for fam in all_fams:
                if ft and ft not in fam.lower():
                    continue
                row = Gtk.ListBoxRow()
                lbl = Gtk.Label(label=fam)
                lbl.set_xalign(0)
                lbl.set_margin_start(6); lbl.set_margin_end(6)
                lbl.set_margin_top(4); lbl.set_margin_bottom(4)
                # Apply the font to its own label so the user sees a mini-preview
                try:
                    fd = Pango.FontDescription()
                    fd.set_family(fam)
                    fd.set_size(11 * Pango.SCALE)
                    lbl.override_font(fd)
                except Exception:
                    pass
                row.set_child(lbl)
                row._family = fam
                if fam == current:
                    listbox.select_row(row)
                listbox.append(row)

        def _on_row(_lb, row):
            if row is None:
                return
            fam = getattr(row, "_family", None)
            if not fam:
                return
            self.settings["font_family"] = fam
            self._apply_font_css()
            win.close()

        listbox.connect("row-activated", _on_row)
        entry.connect("search-changed", lambda e: _populate(e.get_text()))

        _populate("")

        win.set_child(box)
        win.present()
        entry.grab_focus()

    def toggle_high_contrast(self, on):
        self.settings["theme"] = "high-contrast" if on else "vintage-brown"
        display = Gdk.Display.get_default()
        if getattr(self, "_hc_provider", None) is not None:
            try:
                Gtk.StyleContext.remove_provider_for_display(
                    display, self._hc_provider)
            except Exception:
                pass
            self._hc_provider = None
        if on:
            prov = Gtk.CssProvider()
            prov.load_from_string(css(HIGH_CONTRAST))
            Gtk.StyleContext.add_provider_for_display(
                display, prov,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 5)
            self._hc_provider = prov

    def on_open_path(self, *_):
        win = Gtk.Window()
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_title("Open by path")
        win.set_default_size(520, -1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Path… (Tab to complete, Enter to open)")
        entry.set_hexpand(True)
        box.append(entry)

        status = Gtk.Label(label="")
        status.set_halign(Gtk.Align.START)
        box.append(status)

        def _complete():
            txt = entry.get_text().strip()
            if not txt:
                return
            try:
                p = Path(txt).expanduser()
            except Exception:
                return
            # If path is a dir, list it; else complete the basename
            if p.is_dir():
                try:
                    kids = sorted(p.iterdir(), key=lambda x: x.name.lower())
                except Exception:
                    kids = []
                if kids:
                    entry.set_text(str(kids[0]))
                    entry.set_position(-1)
                    status.set_text(f"{len(kids)} entries")
                return
            parent = p.parent if str(p.parent) else Path(".")
            prefix = p.name
            try:
                cands = sorted(
                    (x for x in parent.iterdir() if x.name.startswith(prefix)),
                    key=lambda x: x.name.lower())
            except Exception:
                cands = []
            if not cands:
                status.set_text("no match")
                return
            entry.set_text(str(cands[0]))
            entry.set_position(-1)
            status.set_text(f"{len(cands)} match{'es' if len(cands) != 1 else ''}")

        def _commit():
            txt = entry.get_text().strip()
            if not txt:
                return
            p = Path(txt).expanduser()
            if not p.exists() or p.is_dir():
                status.set_text("not a file")
                return
            self._add_tab(str(p))
            _push_recent(str(p))
            win.close()

        key_ctrl = Gtk.EventControllerKey()
        def _on_key(_c, keyval, _kc, state):
            name = Gdk.keyval_name(keyval)
            if name == "Tab":
                _complete()
                return True
            if name in ("Return", "KP_Enter"):
                _commit()
                return True
            if name == "Escape":
                win.close()
                return True
            return False
        key_ctrl.connect("key-pressed", _on_key)
        entry.add_controller(key_ctrl)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_row.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: win.close())
        ok = Gtk.Button(label="Open")
        ok.add_css_class("suggested-action")
        ok.connect("clicked", lambda *_: _commit())
        btn_row.append(cancel)
        btn_row.append(ok)
        box.append(btn_row)

        win.set_child(box)
        win.present()
        entry.grab_focus()

    def toggle_split(self, on=None):
        # currently split -> unsplit
        if getattr(self, "_split_paned", None) is not None:
            self._unsplit()
            return
        tab = self._active_tab()
        if not tab:
            return
        parent = self.notebook.get_parent()
        if parent is None:
            return

        second = GtkSource.View()
        second.set_buffer(tab.buffer)
        second.set_show_line_numbers(tab.view.get_show_line_numbers())
        second.set_highlight_current_line(tab.view.get_highlight_current_line())
        second.set_auto_indent(True)
        second.set_monospace(True)
        second.add_css_class("ql-editor")
        try:
            fam = self.settings.get("font_family") or "Monospace"
            fd = Pango.FontDescription()
            fd.set_family(fam)
            fd.set_size(int(self.settings.get("font_size", 13)) * Pango.SCALE)
            second.override_font(fd)
        except Exception:
            pass

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_child(second)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_wide_handle(True)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        # detach notebook from its current parent, then reattach inside the paned
        if isinstance(parent, Gtk.Box):
            parent.remove(self.notebook)
            paned.set_start_child(self.notebook)
            paned.set_end_child(scrolled)
            parent.append(paned)
        elif isinstance(parent, Gtk.Paned):
            return
        elif hasattr(parent, "set_child"):
            parent.set_child(paned)
            paned.set_start_child(self.notebook)
            paned.set_end_child(scrolled)
        else:
            return

        self._split_paned = paned
        self._split_scrolled = scrolled
        self._split_parent = parent
        # Start at 50/50 after layout settles
        def _center():
            try:
                w = paned.get_width()
                if w > 100:
                    paned.set_position(w // 2)
            except Exception:
                pass
            return False
        GLib.timeout_add(80, _center)
        # Start at 50/50 after layout settles
        def _center():
            try:
                w = paned.get_width()
                if w > 100:
                    paned.set_position(w // 2)
            except Exception:
                pass
            return False
        GLib.timeout_add(80, _center)

    def _unsplit(self):
        paned = getattr(self, "_split_paned", None)
        parent = getattr(self, "_split_parent", None)
        if paned is None or parent is None:
            return
        # detach the second view first
        paned.set_end_child(None)
        paned.set_start_child(None)
        if isinstance(parent, Gtk.Box):
            parent.remove(paned)
            parent.append(self.notebook)
        elif hasattr(parent, "set_child"):
            parent.set_child(self.notebook)
        self._split_paned = None
        self._split_scrolled = None
        self._split_parent = None
        tab = self._active_tab()
        if tab:
            tab.view.grab_focus()

    def on_recent(self, *_):
        items = _load_recent()
        win = Gtk.Window()
        win.set_transient_for(self)
        win.set_modal(True)
        win.set_title("Recent Files")
        win.set_default_size(480, 340)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(8); box.set_margin_end(8)
        box.set_margin_top(8); box.set_margin_bottom(8)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled.set_child(lb)
        box.append(scrolled)
        if not items:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label="No recent files"))
            lb.append(row)
            lb.set_sensitive(False)
        def _open(_lb, row):
            path = getattr(row, "_path", None)
            if not path: return
            self._add_tab(path)
            _push_recent(path)
            win.close()
        for path in items:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=path)
            lbl.set_xalign(0); lbl.set_ellipsize(3)
            lbl.set_margin_start(6); lbl.set_margin_end(6)
            lbl.set_margin_top(4); lbl.set_margin_bottom(4)
            row.set_child(lbl)
            row._path = path
            lb.append(row)
        lb.connect("row-activated", _open)
        close = Gtk.Button(label="Close")
        close.set_halign(Gtk.Align.END)
        close.connect("clicked", lambda *_: win.close())
        box.append(close)
        win.set_child(box)
        win.present()

    def set_line_ending(self, mode):
        tab = self._active_tab()
        if not tab: return
        tab.line_ending = mode
        tab.dirty = True
        tab._label.set_text(tab.title())

    def set_encoding(self, enc):
        tab = self._active_tab()
        if not tab: return
        tab.encoding = enc
        if tab.path and tab.path.exists():
            tab._load_from_disk()
            tab.encoding = enc
            tab.dirty = True
            tab._label.set_text(tab.title())

    def _autosave_tick(self):
        for t in getattr(self, "tabs", []) or []:
            if t.dirty and t.path:
                try:
                    t.save_to_disk()
                    t._label.set_text(t.title())
                except Exception:
                    pass
        return True

    def _on_file_changed(self, monitor, file, _other, event):
        if event not in (Gio.FileMonitorEvent.CHANGES_DONE_HINT,
                         Gio.FileMonitorEvent.CREATED):
            return
        try:
            path = file.get_path()
        except Exception:
            return
        for t in self.tabs:
            if not t.path or str(t.path) != path:
                continue
            # Ignore echoes of our own save
            try:
                if abs(t.path.stat().st_mtime - getattr(t, "_last_saved_mtime", 0)) < 0.5:
                    return
            except Exception:
                pass
            if not t.dirty:
                try:
                    t._load_from_disk()
                    t._label.set_text(t.title())
                except Exception:
                    pass

    def _active_tab(self):
        idx = self.notebook.get_current_page()
        if idx < 0 or idx >= len(self.tabs):
            return None
        return self.tabs[idx]

    def _add_tab(self, path=None):
        tab = EditorTab(path)
        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=tab.title())
        label_box.append(label)
        close = Gtk.Button(label="✕")
        close.set_has_frame(False)
        close.connect("clicked", lambda _b, t=tab: self._close_tab(t))
        label_box.append(close)

        page = self.notebook.append_page(tab, label_box)
        self.notebook.set_current_page(page)
        self.tabs.append(tab)
        tab._label = label
        self._apply_settings_to_tab(tab)
        if tab.path:
            try:
                gfile = Gio.File.new_for_path(str(tab.path))
                mon = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
                mon.connect("changed", self._on_file_changed)
                tab._monitor = mon
            except Exception:
                tab._monitor = None
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_auto_pair)
        tab.view.add_controller(key_ctrl)
        tab.view.grab_focus()
        return tab

    def _close_tab(self, tab):
        if tab is None or tab not in self.tabs:
            return
        if not tab.dirty:
            return self._remove_tab(tab)
        d = Adw.MessageDialog(
            transient_for=self,
            heading="Save changes?",
            body=f"{tab.title()} has unsaved changes.")
        d.add_response("cancel", "Cancel")
        d.add_response("discard", "Discard")
        d.add_response("save", "Save")
        d.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_default_response("save")
        d.set_close_response("cancel")

        def _resp(_d, r):
            if r == "discard":
                self._remove_tab(tab)
            elif r == "save":
                if not tab.path:
                    self.notebook.set_current_page(self.tabs.index(tab))
                    return self.on_save_as()
                ok, err = tab.save_to_disk()
                if ok:
                    self._remove_tab(tab)
                else:
                    self._show_error("Save failed", err)
        d.connect("response", _resp)
        d.present()

    def _remove_tab(self, tab):
        if tab not in self.tabs:
            return
        idx = self.tabs.index(tab)
        self.tabs.remove(tab)
        self.notebook.remove_page(idx)
        if not self.tabs:
            self._add_tab()

    def _on_tab_switch(self, _nb, _page, _idx):
        self._refresh_status()

    def _do(self, action):
        tab = self._active_tab()
        if not tab:
            return
        buf = tab.buffer
        if action == "undo":
            buf.undo() if buf.get_can_undo() else None
        elif action == "redo":
            buf.redo() if buf.get_can_redo() else None
        elif action == "cut":
            buf.cut_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), True)
        elif action == "copy":
            buf.copy_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD))
        elif action == "paste":
            buf.paste_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), None, True)
        elif action == "select_all":
            buf.select_range(buf.get_start_iter(), buf.get_end_iter())

    def _refresh_status(self):
        if self.status is None:
            return
        tab = self._active_tab()
        if not tab:
            self.status.set_text(" Ready")
            return
        name = tab.path.name if tab.path else "untitled"
        dirty = " ●" if tab.dirty else ""
        cursor = tab.buffer.get_iter_at_mark(tab.buffer.get_insert())
        line = cursor.get_line() + 1
        col = cursor.get_line_offset() + 1
        ro = "  ·  RO" if getattr(self, "_read_only", False) else ""
        self.status.set_text(f" {name}{dirty}  ·  Ln {line}, Col {col}{ro}  ·  vintage-brown")

    # ---------- actions ----------

    def on_new(self, *_):
        self._add_tab()

    def on_open(self, *_):
        dialog = Gtk.FileDialog(title="Open File")
        def _done(d, result):
            try:
                f = d.open_finish(result)
                if f:
                    path = f.get_path()
                    self._add_tab(path)
                    _push_recent(path)
            except GLib.Error:
                pass
            except Exception as e:
                self._show_error("Open failed", str(e))
        dialog.open(self, None, _done)

    def on_save(self, *_):
        tab = self._active_tab()
        if not tab:
            return
        if not tab.path:
            return self.on_save_as()
        ok, err = tab.save_to_disk()
        if ok:
            tab._label.set_text(tab.title())
            _push_recent(tab.path)
        else:
            self._show_error("Save failed", err)

    def on_revert(self, *_):
        tab = self._active_tab()
        if not tab or not tab.path:
            return
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Revert file?",
            body=f"Discard changes and reload {tab.path.name}?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("revert", "Revert")
        dialog.set_response_appearance("revert", Adw.ResponseAppearance.DESTRUCTIVE)

        def _on_resp(d, resp):
            if resp == "revert":
                tab._load_from_disk()
                tab._label.set_text(tab.title())

        dialog.connect("response", _on_resp)
        dialog.present()

    def _show_error(self, title, msg):
        d = Adw.MessageDialog(transient_for=self, heading=title, body=str(msg))
        d.add_response("ok", "OK")
        d.present()

    def on_save_as(self, *_):
        tab = self._active_tab()
        if not tab:
            return
        dialog = Gtk.FileDialog(title="Save As")
        def _done(d, result):
            try:
                f = d.save_finish(result)
                if f:
                    tab.path = Path(f.get_path())
                    self.on_save()
            except GLib.Error:
                pass
            except Exception as e:
                self._show_error("Save As failed", str(e))
        dialog.save(self, None, _done)

    def on_quit(self, *_):
        self.close()

    def on_about(self, *_):
        about = Adw.AboutWindow(
            application_name="Quillinks",
            application_icon="accessories-text-editor",
            version="0.3.0-gtk",
            developer_name="Apersonwithtoenail",
            comments="A modern text editor. GTK4 edition.",
        )
        about.set_transient_for(self)
        about.present()

    def on_toggle_simple(self, _btn):
        if self.simple_btn.get_label() == "◀ Simple Mode":
            self.simple_btn.set_label("▶ Full Mode")
        else:
            self.simple_btn.set_label("◀ Simple Mode")

    def _on_close(self, *_):
        dirty_tabs = [t for t in self.tabs if t.dirty]
        if not dirty_tabs:
            self._do_close()
            return True

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Unsaved changes",
            body=f"{len(dirty_tabs)} tab(s) have unsaved changes. Save before closing?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Discard")
        dialog.add_response("save", "Save All")
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def _on_response(_d, resp):
            if resp == "cancel":
                return
            if resp == "save":
                for tab in dirty_tabs:
                    if tab.path:
                        tab.save_to_disk()
                    else:
                        # Unnamed tab: fall back to Save As on the active one,
                        # then discard the rest (rare edge case)
                        if tab is self._active_tab():
                            self.on_save_as()
            self._do_close()

        dialog.connect("response", _on_response)
        dialog.present()
        return True

    def _do_close(self):
        # Save geometry
        try:
            w = self.get_width()
            h = self.get_height()
            self.settings["geometry"] = f"{w}x{h}"
        except Exception:
            pass
        # Save session with cursor line per tab
        open_files = []
        for t in self.tabs:
            if not t.path:
                continue
            try:
                it = t.buffer.get_iter_at_mark(t.buffer.get_insert())
                line = it.get_line()
            except Exception:
                line = 0
            open_files.append({"path": str(t.path), "line": line})
        _save_json(_SESSION_FILE, {"open_files": open_files})
        # Save settings
        _save_settings(self.settings)
        # Destroy
        self.get_application().quit()


# ══════════════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════════════

class QuillinksApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.apwith.quillinks.gtk")
        self.win = None
        self._initial_paths = []

    def do_handle_local_options(self, options):
        # Extract file args from sys.argv
        for arg in sys.argv[1:]:
            if not arg.startswith("-") and Path(arg).exists():
                self._initial_paths.append(arg)
        return -1

    def do_activate(self):
        apply_css(VINTAGE)
        if self.win is None:
            self.win = QuillinksWindow(self, initial_paths=self._initial_paths)
        self.win.present()


def main():
    app = QuillinksApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
