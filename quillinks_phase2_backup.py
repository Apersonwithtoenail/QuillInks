#!/usr/bin/env python3
"""Quillinks — modern terminal text editor."""

import json
import sys
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static, TextArea


# ---------------- config paths ----------------

def _config_dir() -> Path:
    d = Path.home() / ".local" / "share" / "quillinks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _scratch_path() -> Path:
    return _config_dir() / "scratch.md"


def _session_path() -> Path:
    return _config_dir() / "session.json"


def _load_session() -> str | None:
    try:
        data = json.loads(_session_path().read_text())
        return data.get("last_file")
    except Exception:
        return None


def _save_session(path: Path | None) -> None:
    try:
        _session_path().write_text(json.dumps({"last_file": str(path) if path else None}))
    except Exception:
        pass


# ---------------- search modal ----------------

class SearchBar(ModalScreen):
    CSS = """
    SearchBar { align: center middle; }
    #search-box {
        width: 60; height: auto; padding: 1 2;
        background: $surface; border: thick $primary;
    }
    #search-row, #replace-row { height: 3; }
    #search-input, #replace-input { width: 1fr; }
    #hint { color: $text-muted; }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "find_next", "Find"),
    ]

    def __init__(self, replace_mode: bool = False):
        super().__init__()
        self.replace_mode = replace_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="search-box"):
            with Horizontal(id="search-row"):
                yield Input(placeholder="Search…", id="search-input")
                yield Button("Find", id="btn-find", variant="primary")
            if self.replace_mode:
                with Horizontal(id="replace-row"):
                    yield Input(placeholder="Replace with…", id="replace-input")
                    yield Button("Replace", id="btn-replace", variant="warning")
            yield Label("Enter = find next  ·  Esc = close", id="hint")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-find":
            self.action_find_next()
        elif event.button.id == "btn-replace":
            self._do_replace()

    def action_find_next(self) -> None:
        term = self.query_one("#search-input", Input).value
        if not term:
            return
        editor = self.app.query_one("#editor", TextArea)
        text = editor.text
        row, col = editor.cursor_location
        start = sum(len(line) + 1 for line in text.split("\n")[:row]) + col
        idx = text.lower().find(term.lower(), start)
        if idx == -1:
            idx = text.lower().find(term.lower())
        if idx >= 0:
            before = text[:idx]
            r = before.count("\n")
            c = idx - (before.rfind("\n") + 1)
            editor.cursor_location = (r, c)
            editor.selection = ((r, c), (r, c + len(term)))

    def _do_replace(self) -> None:
        term = self.query_one("#search-input", Input).value
        repl = self.query_one("#replace-input", Input).value
        if not term:
            return
        editor = self.app.query_one("#editor", TextArea)
        editor.text = editor.text.replace(term, repl)
        self.app.notify(f"Replaced {term} → {repl}")


class _LinePrompt(ModalScreen):
    CSS = """
    _LinePrompt { align: center middle; }
    #box { width: 40; height: auto; padding: 1 2; background: $surface; border: thick $primary; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Go to line number:")
            yield Input(placeholder="e.g. 42", id="line-input")

    def on_mount(self) -> None:
        self.query_one("#line-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


# ---------------- main app ----------------

class Quillinks(App):
    CSS = """
    #status { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new", "New"),
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+h", "replace", "Replace"),
        Binding("ctrl+l", "toggle_lines", "Lines"),
        Binding("ctrl+w", "toggle_wrap", "Wrap"),
        Binding("ctrl+g", "goto_line", "Go to"),
        Binding("f5", "insert_date", "Date"),
    ]

    AUTOSAVE_DELAY = 5.0  # seconds after last edit

    def __init__(self, path=None):
        super().__init__()
        # Resolve startup file: explicit arg → last session → scratch
        if path:
            self.path = Path(path).expanduser().resolve()
        else:
            last = _load_session()
            if last and Path(last).exists():
                self.path = Path(last)
            else:
                self.path = _scratch_path()
        self.title = self.path.name
        self._dirty = False
        self._autosave_timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield TextArea(id="editor", show_line_numbers=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        editor = self.query_one("#editor", TextArea)
        if self.path.exists():
            editor.text = self.path.read_text()
        elif self.path == _scratch_path():
            # new scratch — seed with a header
            editor.text = f"# Scratch\n\nStarted {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        editor.focus()
        self._refresh_status()
        self.set_interval(0.5, self._refresh_status)

    def _refresh_status(self) -> None:
        editor = self.query_one("#editor", TextArea)
        row, col = editor.cursor_location
        name = self.path.name if self.path else "untitled"
        dirty = " ●" if self._dirty else ""
        n_lines = editor.text.count("\n") + 1
        wrap = "wrap" if editor.soft_wrap else "nowrap"
        saved = "saved" if not self._dirty else "autosave in " + str(int(self.AUTOSAVE_DELAY)) + "s"
        self.query_one("#status", Static).update(
            f" {name}{dirty}  ·  Ln {row + 1}, Col {col + 1}  ·  {n_lines} lines  ·  {wrap}  ·  {saved}"
        )

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._dirty = True
        self._schedule_autosave()
        self._refresh_status()

    def on_text_area_selection_changed(self, event) -> None:
        self._refresh_status()

    def _schedule_autosave(self) -> None:
        """Reset autosave timer — fires only after user stops typing."""
        if self._autosave_timer is not None:
            self._autosave_timer.stop()
        self._autosave_timer = self.set_timer(self.AUTOSAVE_DELAY, self._do_autosave)

    def _do_autosave(self) -> None:
        if not self._dirty or self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.query_one("#editor", TextArea).text)
            self._dirty = False
            self._refresh_status()
        except Exception as e:
            self.notify(f"Autosave failed: {e}", severity="error")

    def action_save(self) -> None:
        self._do_autosave()
        if self.path:
            self.notify(f"Saved {self.path.name}")

    def action_new(self) -> None:
        self.path = _scratch_path()
        self.query_one("#editor", TextArea).text = ""
        self._dirty = False
        self._refresh_status()

    def action_find(self) -> None:
        self.push_screen(SearchBar(replace_mode=False))

    def action_replace(self) -> None:
        self.push_screen(SearchBar(replace_mode=True))

    def action_toggle_lines(self) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.show_line_numbers = not editor.show_line_numbers
        self.notify(f"Line numbers {'on' if editor.show_line_numbers else 'off'}")

    def action_toggle_wrap(self) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.soft_wrap = not editor.soft_wrap
        self._refresh_status()

    def action_goto_line(self) -> None:
        def _on_line(line: str | None) -> None:
            if not line or not line.strip().isdigit():
                return
            editor = self.query_one("#editor", TextArea)
            target = max(0, int(line) - 1)
            total = editor.text.count("\n")
            target = min(target, total)
            editor.cursor_location = (target, 0)
            editor.focus()
        self.push_screen(_LinePrompt(), _on_line)

    def action_insert_date(self) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.insert(datetime.now().strftime("%Y-%m-%d %H:%M"))
        self._dirty = True

    def on_unmount(self) -> None:
        """Save session + final flush on quit."""
        self._do_autosave()
        _save_session(self.path)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    Quillinks(arg).run()
