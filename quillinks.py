#!/usr/bin/env python3
"""Quillinks — modern terminal text editor."""

import sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TextArea


class Editor(App):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new", "New"),
    ]

    def __init__(self, path=None):
        super().__init__()
        self.path = Path(path) if path else None
        self.title = self.path.name if self.path else "untitled"

    def compose(self) -> ComposeResult:
        yield Header()
        yield TextArea(id="editor")
        yield Footer()

    def on_mount(self) -> None:
        editor = self.query_one("#editor", TextArea)
        if self.path and self.path.exists():
            editor.text = self.path.read_text()
        editor.focus()

    def action_save(self) -> None:
        editor = self.query_one("#editor", TextArea)
        if not self.path:
            self.path = Path("untitled.txt")
        self.path.write_text(editor.text)
        self.notify(f"Saved {self.path.name}")

    def action_new(self) -> None:
        self.path = None
        self.query_one("#editor", TextArea).text = ""


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    Editor(path).run()
