#!/usr/bin/env python3
"""Quillinks GUI — Tkinter-based editor."""

import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from pathlib import Path


class QuillinksGUI:
    def __init__(self, path=None):
        self.root = tk.Tk()
        self.root.title("Quillinks")
        self.root.geometry("900x650")

        self.path = Path(path).expanduser().resolve() if path else None
        self.dirty = False
        self._font_size = 11
        self._font_family = "Monospace"

        # --- menu bar ---
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.text.event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find…", accelerator="Ctrl+F", command=self.open_find)
        edit_menu.add_command(label="Insert Date/Time", accelerator="F5", command=self.insert_datetime)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        self.wrap_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_wrap)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", accelerator="Ctrl++", command=lambda: self.zoom(1))
        view_menu.add_command(label="Zoom Out", accelerator="Ctrl+-", command=lambda: self.zoom(-1))
        view_menu.add_command(label="Reset Zoom", accelerator="Ctrl+0", command=self.zoom_reset)
        view_menu.add_separator()

        font_menu = tk.Menu(view_menu, tearoff=0)
        font_menu.add_command(label="Change Font Family…", command=self.open_font_picker)
        font_menu.add_separator()
        for name in ["Monospace", "DejaVu Sans Mono", "Courier New", "Courier",
                     "Liberation Mono", "Ubuntu Mono", "Fira Code", "Cascadia Code",
                     "JetBrains Mono", "Consolas", "Menlo", "Source Code Pro",
                     "Sans", "Serif", "Helvetica", "Arial"]:
            font_menu.add_command(label=name, command=lambda n=name: self.set_font_family(n))
        view_menu.add_cascade(label="Font", menu=font_menu)

        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Plugin Manager…", command=self.open_plugin_manager)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard Shortcuts", accelerator="F1", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        # --- text area ---
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.scroll = tk.Scrollbar(frame)
        self.scroll.pack(side="right", fill="y")

        self.text = tk.Text(
            frame,
            wrap="none",
            undo=True,
            font=(self._font_family, self._font_size),
            yscrollcommand=self.scroll.set,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264f78",
        )
        self.text.pack(fill="both", expand=True)
        self.scroll.config(command=self.text.yview)

        # --- status bar ---
        self.status = tk.Label(self.root, anchor="w", bg="#2d2d2d", fg="#d4d4d4", padx=6)
        self.status.pack(fill="x", side="bottom")

        # --- bindings ---
        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<KeyRelease>", self.update_status)
        self.text.bind("<ButtonRelease>", self.update_status)

        # File
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-q>", lambda e: self.on_close())
        # Edit
        self.root.bind("<Control-a>", self.select_all)
        self.root.bind("<Control-z>", lambda e: self.text.event_generate("<<Undo>>"))
        self.root.bind("<Control-y>", lambda e: self.text.event_generate("<<Redo>>"))
        self.root.bind("<Control-Shift-Z>", lambda e: self.text.event_generate("<<Redo>>"))
        self.root.bind("<Control-x>", lambda e: self.text.event_generate("<<Cut>>"))
        self.root.bind("<Control-c>", lambda e: self.text.event_generate("<<Copy>>"))
        self.root.bind("<Control-v>", lambda e: self.text.event_generate("<<Paste>>"))
        self.root.bind("<Control-d>", self.duplicate_line)
        self.root.bind("<Control-Shift-K>", self.delete_line)
        self.root.bind("<Alt-Up>", lambda e: self.move_line(-1))
        self.root.bind("<Alt-Down>", lambda e: self.move_line(1))
        self.root.bind("<Control-slash>", self.toggle_comment)
        # Find / Go
        self.root.bind("<Control-f>", lambda e: self.open_find())
        self.root.bind("<Control-h>", lambda e: self.open_find())
        self.root.bind("<Control-g>", self.goto_line)
        # View
        self.root.bind("<Control-equal>", lambda e: self.zoom(1))
        self.root.bind("<Control-plus>", lambda e: self.zoom(1))
        self.root.bind("<Control-minus>", lambda e: self.zoom(-1))
        self.root.bind("<Control-0>", lambda e: self.zoom_reset())
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Control-Shift-F>", lambda e: self.open_font_picker())
        # Misc
        self.root.bind("<F5>", lambda e: self.insert_datetime())
        self.root.bind("<F1>", lambda e: self.show_shortcuts())

        # load file
        if self.path and self.path.exists():
            self.text.insert("1.0", self.path.read_text())
            self.text.edit_modified(False)
            self.dirty = False
            self.update_title()

        self.update_status()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(300, self._autosave_tick)

    # ---------- file ops ----------

    def new_file(self):
        if not self._confirm_discard():
            return
        self.text.delete("1.0", "end")
        self.path = None
        self.dirty = False
        self.text.edit_modified(False)
        self.update_title()

    def open_file(self):
        if not self._confirm_discard():
            return
        p = filedialog.askopenfilename()
        if not p:
            return
        self.path = Path(p)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.path.read_text())
        self.dirty = False
        self.text.edit_modified(False)
        self.update_title()

    def save_file(self):
        if self.path is None:
            return self.save_as()
        self.path.write_text(self.text.get("1.0", "end-1c"))
        self.dirty = False
        self.text.edit_modified(False)
        self.update_title()
        self.status.config(text=f"Saved {self.path.name}")

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".md")
        if not p:
            return
        self.path = Path(p)
        self.save_file()

    def on_close(self):
        if not self._confirm_discard():
            return
        self.root.destroy()

    def _confirm_discard(self):
        if not self.dirty:
            return True
        return messagebox.askyesno("Quillinks", "Discard unsaved changes?")

    # ---------- edit ops ----------

    def insert_datetime(self):
        self.text.insert("insert", datetime.now().strftime("%Y-%m-%d %H:%M"))

    def toggle_wrap(self):
        self.text.config(wrap="word" if self.wrap_var.get() else "none")

    def on_modified(self, event):
        if self.text.edit_modified():
            self.dirty = True
            self.update_title()

    def update_title(self):
        name = self.path.name if self.path else "untitled"
        star = " ●" if self.dirty else ""
        self.root.title(f"{name}{star} — Quillinks")

    def update_status(self, event=None):
        row, col = self.text.index("insert").split(".")
        self.status.config(text=f" Ln {row}, Col {int(col)+1}  ·  {'saved' if not self.dirty else 'modified'}")

    # ---------- find ----------

    def open_find(self):
        win = tk.Toplevel(self.root)
        win.title("Find & Replace")
        win.geometry("400x140")
        win.transient(self.root)

        tk.Label(win, text="Find:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        find_entry = tk.Entry(win, width=30)
        find_entry.grid(row=0, column=1, padx=6, pady=4)
        find_entry.focus()

        tk.Label(win, text="Replace:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        repl_entry = tk.Entry(win, width=30)
        repl_entry.grid(row=1, column=1, padx=6, pady=4)

        def find_next():
            self.text.tag_remove("match", "1.0", "end")
            term = find_entry.get()
            if not term:
                return
            idx = "1.0"
            count = 0
            while True:
                idx = self.text.search(term, idx, nocase=True, stopindex="end")
                if not idx:
                    break
                end = f"{idx}+{len(term)}c"
                self.text.tag_add("match", idx, end)
                count += 1
                idx = end
            self.text.tag_config("match", background="#264f78")
            if count == 0:
                messagebox.showinfo("Find", "No matches")
            else:
                pos = self.text.tag_ranges("match")
                self.text.mark_set("insert", pos[0])
                self.text.see(pos[0])

        def replace_all():
            term = find_entry.get()
            repl = repl_entry.get()
            if not term:
                return
            content = self.text.get("1.0", "end-1c")
            count = content.count(term)
            if count == 0:
                messagebox.showinfo("Replace", "No matches")
                return
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content.replace(term, repl))
            messagebox.showinfo("Replace", f"Replaced {count} occurrences")

        tk.Button(win, text="Find Next", command=find_next).grid(row=2, column=0, padx=6, pady=8)
        tk.Button(win, text="Replace All", command=replace_all).grid(row=2, column=1, padx=6, pady=8)

    # ---------- common shortcuts ----------

    def select_all(self, event=None):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")
        return "break"

    def duplicate_line(self, event=None):
        try:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
            line = self.text.get(start, end)
            self.text.insert(f"{end}", "\n" + line)
        except tk.TclError:
            pass
        return "break"

    def delete_line(self, event=None):
        try:
            self.text.delete("insert linestart", "insert lineend +1c")
        except tk.TclError:
            pass
        return "break"

    def move_line(self, direction):
        try:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
            line = self.text.get(start, end)
            if direction < 0:
                prev_start = self.text.index(f"{start} -1 line linestart")
                if self.text.compare(prev_start, ">=", "1.0"):
                    prev_end = self.text.index(f"{prev_start} lineend")
                    prev_line = self.text.get(prev_start, prev_end)
                    self.text.delete(prev_start, f"{end} +1c")
                    self.text.insert(prev_start, line + "\n" + prev_line)
                    self.text.mark_set("insert", prev_start)
            else:
                next_start = self.text.index(f"{end} +1c")
                if self.text.compare(next_start, "<", "end-1c"):
                    next_end = self.text.index(f"{next_start} lineend")
                    next_line = self.text.get(next_start, next_end)
                    self.text.delete(start, f"{next_end} +1c")
                    self.text.insert(start, next_line + "\n" + line)
                    self.text.mark_set("insert", f"{start} +1 line")
        except tk.TclError:
            pass
        return "break"

    def toggle_comment(self, event=None):
        try:
            start = self.text.index("insert linestart")
            end = self.text.index("insert lineend")
            line = self.text.get(start, end)
            if line.lstrip().startswith("#"):
                idx = line.find("#")
                new = line[:idx] + line[idx+1:].lstrip(" ")
                self.text.delete(start, end)
                self.text.insert(start, new)
            else:
                self.text.insert(start, "# ")
        except tk.TclError:
            pass
        return "break"

    def goto_line(self, event=None):
        win = tk.Toplevel(self.root)
        win.title("Go to line")
        win.geometry("240x80")
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

    # ---------- view helpers ----------

    def _apply_font(self):
        self.text.config(font=(self._font_family, self._font_size))

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

    def open_font_picker(self):
        try:
            from plugins.font_picker import open_font_picker
            open_font_picker(self.root, self._font_family, self.set_font_family)
        except ImportError:
            messagebox.showinfo(
                "Font picker unavailable",
                "plugins/font_picker.py not found.\nUsing View → Font menu instead."
            )

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))
        return "break"

    # ---------- help ----------

    def show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.geometry("460x520")
        win.transient(self.root)
        win.configure(bg="#1e1e1e")

        tk.Label(win, text="Keyboard Shortcuts", bg="#1e1e1e", fg="#d4d4d4",
                 font=("Sans", 13, "bold")).pack(pady=(12, 8))

        frame = tk.Frame(win, bg="#1e1e1e")
        frame.pack(fill="both", expand=True, padx=20)

        rows = [
            ("File", ""),
            ("Ctrl+N", "New file"),
            ("Ctrl+O", "Open file"),
            ("Ctrl+S", "Save"),
            ("Ctrl+Shift+S", "Save As"),
            ("Ctrl+Q", "Quit"),
            ("", ""),
            ("Edit", ""),
            ("Ctrl+A", "Select all"),
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Ctrl+X / C / V", "Cut / Copy / Paste"),
            ("Ctrl+D", "Duplicate line"),
            ("Ctrl+Shift+K", "Delete line"),
            ("Alt+↑ / Alt+↓", "Move line up / down"),
            ("Ctrl+/", "Toggle comment"),
            ("", ""),
            ("Find / Navigate", ""),
            ("Ctrl+F or Ctrl+H", "Find & Replace"),
            ("Ctrl+G", "Go to line"),
            ("", ""),
            ("View", ""),
            ("Ctrl++ / Ctrl+-", "Zoom in / out"),
            ("Ctrl+0", "Reset zoom"),
            ("F11", "Fullscreen"),
            ("View → Font", "Change font family"),
            ("", ""),
            ("Misc", ""),
            ("F5", "Insert date/time"),
            ("F1", "This dialog"),
        ]
        for key, desc in rows:
            if not key and not desc:
                tk.Frame(frame, height=8, bg="#1e1e1e").pack()
                continue
            if not desc:
                tk.Label(frame, text=key, bg="#1e1e1e", fg="#4ec9b0",
                         font=("Sans", 11, "bold"), anchor="w").pack(fill="x", pady=(6, 2))
                continue
            row = tk.Frame(frame, bg="#1e1e1e")
            row.pack(fill="x")
            tk.Label(row, text=key, bg="#1e1e1e", fg="#dcdcaa",
                     font=("Monospace", 10), width=20, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg="#1e1e1e", fg="#d4d4d4",
                     font=("Sans", 10), anchor="w").pack(side="left")

        tk.Button(win, text="Close", command=win.destroy).pack(pady=12)

    def open_plugin_manager(self):
        try:
            from plugins.plugin_manager import open_plugin_manager
            open_plugin_manager(self.root, on_change=self._on_plugins_changed)
        except ImportError as e:
            messagebox.showerror("Plugin Manager", f"Not available: {e}")

    def _on_plugins_changed(self):
        # Rebind Ctrl+Shift+F if font_picker just got installed
        try:
            from plugins.font_picker import open_font_picker  # noqa
            self.status.config(text=" Font picker plugin ready")
        except ImportError:
            pass

    def show_about(self):
        messagebox.showinfo(
            "About Quillinks",
            "Quillinks — a modern terminal + GUI text editor.\n\n"
            "Built with Python, Textual, and Tkinter.\n"
            "github.com/Apersonwithtoenail/QuillInks"
        )

    # ---------- autosave ----------

    def _autosave_tick(self):
        if self.dirty and self.path is not None:
            try:
                self.path.write_text(self.text.get("1.0", "end-1c"))
                self.dirty = False
                self.text.edit_modified(False)
                self.update_title()
            except Exception:
                pass
        self.root.after(5000, self._autosave_tick)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    app = QuillinksGUI(arg)
    app.root.mainloop()
