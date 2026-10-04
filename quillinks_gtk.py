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
from gi.repository import Gtk, Gdk, Gio, GLib, Adw, GtkSource  # noqa: E402


# Singleton managers for language/style lookup
_LANG_MGR = GtkSource.LanguageManager.get_default()
_STYLE_MGR = GtkSource.StyleSchemeManager.get_default()


# ══════════════════════════════════════════════════════════════
#  THEME — vintage-brown for the first look
# ══════════════════════════════════════════════════════════════

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
    tabbar {{
        background: {t['tab_bg']};
    }}
    tabbar tab {{
        background: {t['tab_bg']};
        color: {t['tab_fg']};
        border: none;
        border-radius: 10px 10px 0 0;
        padding: 8px 18px;
        margin: 4px 2px 0 2px;
        transition: all 160ms ease-out;
    }}
    tabbar tab:hover {{
        background: {t['hover']};
    }}
    tabbar tab:selected {{
        background: {t['tab_active']};
        color: {t['fg']};
        box-shadow: inset 0 2px 0 {t['accent']},
                    0 -2px 8px rgba(0,0,0,0.3);
    }}
    tabbar tab button {{
        color: {t['tab_fg']};
        background: transparent;
        border: none;
        min-width: 18px;
        min-height: 18px;
    }}
    tabbar tab button:hover {{
        background: {t['accent2']};
        border-radius: 9px;
    }}

    /* ---- text area ---- */
    textview, textview text {{
        background: {t['bg']};
        color: {t['fg']};
        font-family: "Monospace", "DejaVu Sans Mono", monospace;
        font-size: 13px;
        padding: 8px;
    }}

    /* ---- status bar ---- */
    .status-bar {{
        background: {t['status_bg']};
        color: {t['status_fg']};
        border-top: 1px solid {t['border']};
        padding: 4px 12px;
        font-size: 11px;
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
#  Editor tab — a text view + scroll
# ══════════════════════════════════════════════════════════════

class EditorTab(Gtk.Box):
    """A single editor tab: GtkSource.View with syntax highlighting, line numbers,
    bracket matching, auto-indent, current-line highlight — all native."""

    def __init__(self, path=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.path = Path(path).expanduser().resolve() if path else None
        self.dirty = False

        # GtkSource.Buffer with our style scheme
        self.buffer = GtkSource.Buffer()
        scheme = _STYLE_MGR.get_scheme("oblivion")
        if scheme:
            self.buffer.set_style_scheme(scheme)
        self.buffer.set_highlight_matching_brackets(True)

        # Load file
        if self.path and self.path.exists():
            raw = self.path.read_text(errors="replace")
            self.buffer.set_text(raw)

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

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.view)
        self.append(scrolled)

        self.buffer.connect("changed", self._on_changed)

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
#  Main window
# ══════════════════════════════════════════════════════════════

class QuillinksWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Quillinks")
        self.set_default_size(1100, 720)

        self.status = None  # created below; guarded in _refresh_status

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
            ("-", None),
            ("Quit", self.on_quit),
        ]))
        toolbar.append(self._make_menu("Edit", [
            ("Undo", lambda *_: self._do("undo")),
            ("Redo", lambda *_: self._do("redo")),
            ("-", None),
            ("Cut", lambda *_: self._do("cut")),
            ("Copy", lambda *_: self._do("copy")),
            ("Paste", lambda *_: self._do("paste")),
            ("Select All", lambda *_: self._do("select_all")),
        ]))
        toolbar.append(self._make_menu("View", [
            ("Zoom In", None),
            ("Zoom Out", None),
            ("Reset Zoom", None),
        ]))
        toolbar.append(self._make_menu("Help", [
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
        self._add_tab()
        root.append(self.notebook)

        # ---- status bar ----
        self.status = Gtk.Label(label=" Ready")
        self.status.add_css_class("status-bar")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_xalign(0)
        root.append(self.status)

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
        for name, cb in items:
            if name == "-":
                vbox.append(Gtk.Separator())
                continue
            b = Gtk.Button(label=name)
            b.set_has_frame(False)
            b.set_halign(Gtk.Align.FILL)
            b.get_child().set_xalign(0)
            if cb:
                b.connect("clicked", lambda _b, c=cb: (c(), popover.popdown()))
            else:
                b.set_sensitive(False)
            vbox.append(b)
        popover.set_child(vbox)
        btn.set_popover(popover)
        return btn

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
        tab.view.grab_focus()
        return tab

    def _close_tab(self, tab):
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
        self.status.set_text(f" {name}{dirty}  ·  Ln {line}, Col {col}  ·  vintage-brown")

    # ---------- actions ----------

    def on_new(self, *_):
        self._add_tab()

    def on_open(self, *_):
        dialog = Gtk.FileDialog(title="Open File")
        def _done(d, result):
            try:
                f = d.open_finish(result)
                if f:
                    self._add_tab(f.get_path())
            except Exception:
                pass
        dialog.open(self, None, _done)

    def on_save(self, *_):
        tab = self._active_tab()
        if not tab:
            return
        if not tab.path:
            return self.on_save_as()
        tab.path.write_text(tab.buffer.get_text(
            tab.buffer.get_start_iter(),
            tab.buffer.get_end_iter(), False))
        tab.dirty = False
        tab._label.set_text(tab.title())

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
            except Exception:
                pass
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
        return False


# ══════════════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════════════

class QuillinksApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.apwith.quillinks.gtk")
        self.win = None

    def do_activate(self):
        apply_css(VINTAGE)
        if self.win is None:
            self.win = QuillinksWindow(self)
        self.win.present()


def main():
    app = QuillinksApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
