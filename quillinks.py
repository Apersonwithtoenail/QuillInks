#!/usr/bin/env python3
"""Quillinks — modern terminal text editor with tabs."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static, TextArea


# =================== config ===================

def _config_dir() -> Path:
    d = Path.home() / ".local" / "share" / "quillinks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _scratch_path() -> Path:
    return _config_dir() / "scratch.md"


def _session_path() -> Path:
    return _config_dir() / "session.json"


def _load_session() -> list[str]:
    try:
        data = json.loads(_session_path().read_text())
        return [f for f in data.get("open_files", []) if f and Path(f).exists()]
    except Exception:
        return []


def _save_session(paths) -> None:
    try:
        _session_path().write_text(
            json.dumps({"open_files": [str(p) if p else None for p in paths]})
        )
    except Exception:
        pass


# =================== buffer ===================

class Buffer:
    __slots__ = ("path", "text", "cursor", "dirty")

    def __init__(self, path=None, text="", cursor=(0, 0), dirty=False):
        self.path = path
        self.text = text
        self.cursor = cursor
        self.dirty = dirty


# =================== modals ===================

class SearchBar(ModalScreen):
    CSS = """
    SearchBar { align: center middle; }
    #search-box { width: 60; height: auto; padding: 1 2; background: $surface; border: thick $primary; }
    #search-row, #replace-row { height: 3; }
    #search-input, #replace-input { width: 1fr; }
    #hint { color: $text-muted; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, replace_mode=False):
        super().__init__()
        self.replace_mode = replace_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="search-box"):
            with Horizontal(id="search-row"):
                yield Input(placeholder="Search…", id="search-input")
                yield Button("Find", id="btn-find", variant="primary")
            if self.replace_mode:
                with Horizontal(id="replace-row"):
                    yield Input(placeholder="Replace…", id="replace-input")
                    yield Button("Replace", id="btn-replace", variant="warning")
            yield Label("Enter = find · Esc = close", id="hint")

    def on_mount(self):
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event):
        if event.button.id == "btn-find":
            self._find_next()
        elif event.button.id == "btn-replace":
            self._do_replace()

    def on_input_submitted(self, event):
        if event.input.id == "search-input":
            self._find_next()

    def _find_next(self):
        term = self.query_one("#search-input", Input).value
        if not term:
            return
        editor = self.app.query_one("#editor", TextArea)
        text = editor.text
        row, col = editor.cursor_location
        start = sum(len(l) + 1 for l in text.split("\n")[:row]) + col
        idx = text.lower().find(term.lower(), start)
        if idx == -1:
            idx = text.lower().find(term.lower())
        if idx >= 0:
            before = text[:idx]
            r = before.count("\n")
            c = idx - (before.rfind("\n") + 1)
            editor.cursor_location = (r, c)
            editor.selection = ((r, c), (r, c + len(term)))

    def _do_replace(self):
        term = self.query_one("#search-input", Input).value
        repl = self.query_one("#replace-input", Input).value
        if not term:
            return
        editor = self.app.query_one("#editor", TextArea)
        editor.text = editor.text.replace(term, repl)
        self.app.notify(f"Replaced '{term}' → '{repl}'")


class PathPrompt(ModalScreen):
    CSS = """
    PathPrompt { align: center middle; }
    #box { width: 70; height: auto; padding: 1 2; background: $surface; border: thick $primary; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, title, default=""):
        super().__init__()
        self._title = title
        self._default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self._title)
            yield Input(value=self._default, placeholder="~/notes/file.md", id="path-input")

    def on_mount(self):
        self.query_one("#path-input", Input).focus()

    def on_input_submitted(self, event):
        self.dismiss(event.value)


class LinePrompt(ModalScreen):
    CSS = """
    LinePrompt { align: center middle; }
    #box { width: 40; height: auto; padding: 1 2; background: $surface; border: thick $primary; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Go to line:")
            yield Input(placeholder="42", id="line-input")

    def on_mount(self):
        self.query_one("#line-input", Input).focus()

    def on_input_submitted(self, event):
        self.dismiss(event.value)


# =================== markdown preview ===================

class MarkdownPreview(ModalScreen):
    CSS = """
    MarkdownPreview { align: center middle; }
    #preview-box {
        width: 90%; height: 90%;
        background: $surface; border: thick $primary;
        padding: 1 2;
    }
    """
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+m", "dismiss", "Close"),
    ]

    def __init__(self, text):
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="preview-box"):
            yield Label("Markdown preview — Esc to close")
            yield Markdown(self._text, id="preview-markdown")


# =================== main app ===================

class Quillinks(App):
    CSS = """
    #tabbar { height: 3; background: $boost; padding: 0; }
    #tabbar Button { height: 3; min-width: 12; margin: 0 0 0 0; }
    #status { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+t", "new_tab", "New tab"),
        Binding("ctrl+w", "close_tab", "Close"),
        Binding("alt+right", "next_tab", "→"),
        Binding("alt+left", "prev_tab", "←"),
        Binding("alt+1", "tab_1", ""),
        Binding("alt+2", "tab_2", ""),
        Binding("alt+3", "tab_3", ""),
        Binding("alt+4", "tab_4", ""),
        Binding("alt+5", "tab_5", ""),
        Binding("ctrl+o", "open_file", "Open"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+shift+s", "save_as", "Save as"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+h", "replace", "Replace"),
        Binding("ctrl+l", "toggle_lines", "Lines"),
        Binding("ctrl+g", "goto_line", "Go to"),
        Binding("f5", "insert_date", "Date"),
        Binding("ctrl+y", "next_theme", "Theme"),
        Binding("ctrl+m", "preview_md", "Preview"),
        Binding("ctrl+shift+d", "duplicate_line", "Dup"),
        Binding("ctrl+shift+k", "delete_line", "Del line"),
        Binding("ctrl+shift+u", "uppercase", "UPPER"),
        Binding("ctrl+shift+l", "lowercase", "lower"),
        Binding("ctrl+shift+t", "trim_ws", "Trim"),
        Binding("ctrl+shift+o", "sort_lines", "Sort"),
    ]

    AUTOSAVE_DELAY = 5.0

    def __init__(self, paths=None):
        super().__init__()
        self.buffers: list[Buffer] = []
        self.active = 0
        self._swapping = False
        self._autosave_timer = None
        self._initial_paths = paths or []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(id="tabbar")
        yield TextArea(id="editor", show_line_numbers=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self):
        if self._initial_paths:
            to_open = [Path(p).expanduser().resolve() for p in self._initial_paths]
        else:
            last = _load_session()
            to_open = [Path(p) for p in last] if last else [_scratch_path()]

        for p in to_open:
            self._add_buffer(p, focus=False)
        if not self.buffers:
            self._add_buffer(_scratch_path(), focus=False)

        self.active = 0
        self._activate(0)
        self.query_one("#editor", TextArea).focus()
        self.set_interval(0.5, self._refresh_status)

    # ---- buffer management ----

    def _add_buffer(self, path=None, text="", focus=True) -> int:
        buf = Buffer(path=path, text=text)
        if path and path.exists():
            buf.text = path.read_text()
        elif path and path == _scratch_path() and not path.exists():
            buf.text = f"# Scratch\n\nStarted {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        self.buffers.append(buf)
        idx = len(self.buffers) - 1
        if focus:
            self._activate(idx)
        return idx

    def _activate(self, idx):
        if not (0 <= idx < len(self.buffers)):
            return
        self._sync_active_to_buffer()
        self.active = idx
        buf = self.buffers[idx]
        editor = self.query_one("#editor", TextArea)
        self._swapping = True
        editor.text = buf.text
        editor.cursor_location = buf.cursor
        self._swapping = False
        self._refresh_tabbar()
        self._refresh_status()

    def _sync_active_to_buffer(self):
        if not self.buffers:
            return
        buf = self.buffers[self.active]
        editor = self.query_one("#editor", TextArea)
        buf.text = editor.text
        buf.cursor = editor.cursor_location

    def _close_active(self):
        if len(self.buffers) <= 1:
            self.notify("Can't close the last tab")
            return
        self.buffers.pop(self.active)
        if self.active >= len(self.buffers):
            self.active = len(self.buffers) - 1
        self._activate(self.active)

    def _refresh_tabbar(self):
        """Fire-and-forget: schedule async tabbar rebuild."""
        try:
            asyncio.get_running_loop().create_task(self._refresh_tabbar_async())
        except RuntimeError:
            pass

    async def _refresh_tabbar_async(self):
        try:
            bar = self.query_one("#tabbar", Horizontal)
        except Exception:
            return
        # Remove children (async — must await before mounting same IDs)
        await bar.remove_children()
        for i, b in enumerate(self.buffers):
            name = b.path.name if b.path else "untitled"
            if b.dirty:
                name = "● " + name
            btn = Button(name, id=f"tab-{i}")
            btn.variant = "primary" if i == self.active else "default"
            await bar.mount(btn)

    def on_button_pressed(self, event):
        bid = event.button.id or ""
        if bid.startswith("tab-"):
            try:
                self._activate(int(bid.split("-", 1)[1]))
            except ValueError:
                pass

    # ---- status ----

    def _refresh_status(self):
        if not self.buffers:
            return
        buf = self.buffers[self.active]
        editor = self.query_one("#editor", TextArea)
        row, col = editor.cursor_location
        name = buf.path.name if buf.path else "untitled"
        dirty = " ●" if buf.dirty else ""
        n = editor.text.count("\n") + 1
        idx = f" [{self.active + 1}/{len(self.buffers)}]"
        saved = "saved" if not buf.dirty else f"autosave in {int(self.AUTOSAVE_DELAY)}s"
        self.query_one("#status", Static).update(
            f" {name}{dirty}{idx}  ·  Ln {row + 1}, Col {col + 1}  ·  {n} lines  ·  {saved}"
        )

    def on_text_area_changed(self, event):
        if self._swapping:
            return
        if self.buffers:
            self.buffers[self.active].dirty = True
            self._schedule_autosave()
            self._refresh_tabbar()
        self._refresh_status()

    def on_text_area_selection_changed(self, event):
        self._refresh_status()

    # ---- autosave ----

    def _schedule_autosave(self):
        if self._autosave_timer is not None:
            self._autosave_timer.stop()
        self._autosave_timer = self.set_timer(self.AUTOSAVE_DELAY, self._do_autosave)

    def _do_autosave(self):
        try:
            self._sync_active_to_buffer()
        except Exception:
            # Widget already unmounted — buffer text is already up to date from on_text_area_changed
            pass
        if not self.buffers:
            return
        buf = self.buffers[self.active]
        if not buf.dirty or buf.path is None:
            return
        try:
            buf.path.parent.mkdir(parents=True, exist_ok=True)
            buf.path.write_text(buf.text)
            buf.dirty = False
            try:
                self._refresh_tabbar()
                self._refresh_status()
            except Exception:
                pass
        except Exception as e:
            self.notify(f"Autosave failed: {e}", severity="error")

    # ---- actions ----

    def action_new_tab(self):
        self._sync_active_to_buffer()
        self._add_buffer(path=None, text="", focus=True)

    def action_close_tab(self):
        self._sync_active_to_buffer()
        self._close_active()

    def action_next_tab(self):
        if self.buffers:
            self._activate((self.active + 1) % len(self.buffers))

    def action_prev_tab(self):
        if self.buffers:
            self._activate((self.active - 1) % len(self.buffers))

    def action_tab_1(self): self._activate(0)
    def action_tab_2(self): self._activate(1)
    def action_tab_3(self): self._activate(2)
    def action_tab_4(self): self._activate(3)
    def action_tab_5(self): self._activate(4)

    def action_open_file(self):
        def _on_path(p):
            if not p:
                return
            path = Path(p).expanduser().resolve()
            if not path.exists():
                self.notify(f"Not found: {path}", severity="warning")
                return
            self._add_buffer(path, focus=True)
        self.push_screen(PathPrompt("Open file:"), _on_path)

    def action_save(self):
        self._sync_active_to_buffer()
        self._do_autosave()
        buf = self.buffers[self.active]
        if buf.path:
            self.notify(f"Saved {buf.path.name}")
        else:
            self.action_save_as()

    def action_save_as(self):
        self._sync_active_to_buffer()
        buf = self.buffers[self.active]
        default = str(buf.path) if buf.path else str(Path.home() / "notes.md")

        def _on_path(p):
            if not p:
                return
            buf.path = Path(p).expanduser().resolve()
            buf.dirty = True
            self._do_autosave()
            self._refresh_tabbar()
        self.push_screen(PathPrompt("Save as:", default=default), _on_path)

    def action_find(self):
        self.push_screen(SearchBar(replace_mode=False))

    def action_replace(self):
        self.push_screen(SearchBar(replace_mode=True))

    def action_toggle_lines(self):
        editor = self.query_one("#editor", TextArea)
        editor.show_line_numbers = not editor.show_line_numbers
        self.notify(f"Line numbers {'on' if editor.show_line_numbers else 'off'}")

    def action_goto_line(self):
        def _on_line(line):
            if not line or not line.strip().isdigit():
                return
            editor = self.query_one("#editor", TextArea)
            target = max(0, int(line) - 1)
            total = editor.text.count("\n")
            target = min(target, total)
            editor.cursor_location = (target, 0)
            editor.focus()
        self.push_screen(LinePrompt(), _on_line)

    def action_insert_date(self):
        editor = self.query_one("#editor", TextArea)
        editor.insert(datetime.now().strftime("%Y-%m-%d %H:%M"))
        if self.buffers:
            self.buffers[self.active].dirty = True

    # ---- phase 4: polish ----

    def action_next_theme(self):
        names = list(self.available_themes.keys())
        if not names:
            return
        try:
            idx = names.index(self.theme)
        except ValueError:
            idx = 0
        self.theme = names[(idx + 1) % len(names)]
        self.notify(f"Theme: {self.theme}")

    def action_preview_md(self):
        editor = self.query_one("#editor", TextArea)
        self.push_screen(MarkdownPreview(editor.text))

    def _current_line_bounds(self):
        editor = self.query_one("#editor", TextArea)
        row, _ = editor.cursor_location
        lines = editor.text.split("\n")
        if not (0 <= row < len(lines)):
            return None
        line = lines[row]
        start = sum(len(l) + 1 for l in lines[:row])
        return row, line, start

    def action_duplicate_line(self):
        editor = self.query_one("#editor", TextArea)
        info = self._current_line_bounds()
        if not info:
            return
        row, line, start = info
        editor.text = editor.text[:start] + line + "\n" + editor.text[start:]
        editor.cursor_location = (row + 1, 0)
        if self.buffers:
            self.buffers[self.active].dirty = True

    def action_delete_line(self):
        editor = self.query_one("#editor", TextArea)
        info = self._current_line_bounds()
        if not info:
            return
        row, line, start = info
        end = start + len(line) + 1
        editor.text = editor.text[:start] + editor.text[end:]
        if self.buffers:
            self.buffers[self.active].dirty = True

    def action_uppercase(self):
        editor = self.query_one("#editor", TextArea)
        if editor.selected_text:
            editor.replace(editor.selected_text.upper())
            if self.buffers:
                self.buffers[self.active].dirty = True

    def action_lowercase(self):
        editor = self.query_one("#editor", TextArea)
        if editor.selected_text:
            editor.replace(editor.selected_text.lower())
            if self.buffers:
                self.buffers[self.active].dirty = True

    def action_trim_ws(self):
        editor = self.query_one("#editor", TextArea)
        editor.text = "\n".join(l.rstrip() for l in editor.text.split("\n"))
        if self.buffers:
            self.buffers[self.active].dirty = True
        self.notify("Trimmed trailing whitespace")

    def action_sort_lines(self):
        editor = self.query_one("#editor", TextArea)
        text = editor.selected_text or editor.text
        if not text.strip():
            return
        sorted_text = "\n".join(sorted(text.split("\n")))
        if editor.selected_text:
            editor.replace(sorted_text)
        else:
            editor.text = sorted_text
        if self.buffers:
            self.buffers[self.active].dirty = True
        self.notify("Sorted lines")

    def on_unmount(self):
        # Flush every dirty buffer to disk without touching widgets
        for buf in self.buffers:
            if buf.dirty and buf.path is not None:
                try:
                    buf.path.parent.mkdir(parents=True, exist_ok=True)
                    buf.path.write_text(buf.text)
                    buf.dirty = False
                except Exception:
                    pass
        _save_session([b.path for b in self.buffers])


if __name__ == "__main__":
    args = sys.argv[1:] or None
    Quillinks(args).run()
