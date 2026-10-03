"""Optional font picker plugin for Quillinks. Virtualized: loads 20 rows at a time."""
import json
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path


_CACHE_FILE = Path.home() / ".local" / "share" / "quillinks" / "fonts_cache.json"
_CACHE_TTL_SEC = 24 * 60 * 60
BATCH_SIZE = 10


def _load_cached_fonts():
    try:
        data = json.loads(_CACHE_FILE.read_text())
        if time.time() - data.get("ts", 0) < _CACHE_TTL_SEC:
            return data.get("fonts")
    except Exception:
        pass
    return None


def _save_cached_fonts(fonts):
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps({"ts": time.time(), "fonts": fonts}))
    except Exception:
        pass


def open_font_picker(root, current_family, on_apply):
    win = tk.Toplevel(root)
    win.title("Choose Font")
    win.geometry("520x560")
    win.transient(root)
    win.configure(bg="#1e1e1e")

    tk.Label(win, text="Scroll to load more · double-click to apply",
             bg="#1e1e1e", fg="#d4d4d4", font=("Sans", 11, "bold")).pack(pady=(12, 8))

    outer = tk.Frame(win, bg="#1e1e1e")
    outer.pack(fill="both", expand=True, padx=16, pady=4)
    canvas = tk.Canvas(outer, bg="#252526", highlightthickness=0)
    vbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg="#252526")
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_config(e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_config(e=None):
        canvas.itemconfig(window_id, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_inner_config)
    canvas.bind("<Configure>", _on_canvas_config)

    cached = _load_cached_fonts()
    if cached is not None:
        all_fonts = cached
    else:
        all_fonts = sorted(set(tkfont.families(root)))
        _save_cached_fonts(all_fonts)

    queue = list(all_fonts)
    selected = {"family": current_family}

    def render_row(name):
        try:
            if tkfont.Font(family=name, size=11).measure("The quick") < 10:
                return
        except tk.TclError:
            return
        lbl = tk.Label(inner, text=f"  {name}   —   The quick brown fox 0123",
                       bg="#252526", fg="#d4d4d4", font=(name, 11),
                       anchor="w", padx=6, pady=4)
        lbl.pack(fill="x")

        def click(e):
            for c in inner.winfo_children():
                c.config(bg="#252526", fg="#d4d4d4")
            selected["family"] = name
            lbl.config(bg="#264f78", fg="#ffffff")
        def hover(e): lbl.config(bg="#2d2d30")
        def unhover(e):
            if selected["family"] != name: lbl.config(bg="#252526")
        def dbl(e):
            click(e); apply_and_close()

        lbl.bind("<Button-1>", click)
        lbl.bind("<Double-Button-1>", dbl)
        lbl.bind("<Enter>", hover)
        lbl.bind("<Leave>", unhover)
        if name == current_family:
            lbl.config(bg="#264f78", fg="#ffffff")

    status = tk.Label(win, text="", bg="#1e1e1e", fg="#888", font=("Sans", 9))
    status.pack()

    pumping = {"active": False}

    def pump():
        if not pumping["active"]:
            return
        loaded = 0
        while loaded < BATCH_SIZE and queue:
            render_row(queue.pop(0))
            loaded += 1
        remaining = len(queue)
        if remaining:
            status.config(text=f"{remaining} more below · scroll to load")
            pumping["active"] = False
        else:
            status.config(text=f"{len(all_fonts)} fonts loaded")
            pumping["active"] = False

    def trigger_pump():
        if pumping["active"] or not queue:
            return
        pumping["active"] = True
        win.after(1, pump)

    def on_scroll(*args):
        canvas.yview(*args)
        _maybe_load_more()

    vbar.config(command=on_scroll)

    def _maybe_load_more():
        if not queue or pumping["active"]:
            return
        top, bottom = canvas.yview()
        if bottom > 0.85:
            trigger_pump()

    def _wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        _maybe_load_more()
        return "break"

    def _wheel_up(event):
        canvas.yview_scroll(-1, "units")
        _maybe_load_more()
        return "break"

    def _wheel_down(event):
        canvas.yview_scroll(1, "units")
        _maybe_load_more()
        return "break"

    canvas.bind_all("<MouseWheel>", _wheel)
    canvas.bind_all("<Button-4>", _wheel_up)
    canvas.bind_all("<Button-5>", _wheel_down)

    # Initial: render first 2 batches so the viewport fills
    trigger_pump()

    def cleanup():
        try:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        except tk.TclError:
            pass

    def apply_and_close():
        on_apply(selected["family"])
        cleanup()
        try: win.destroy()
        except tk.TclError: pass

    def cancel():
        cleanup()
        try: win.destroy()
        except tk.TclError: pass

    btns = tk.Frame(win, bg="#1e1e1e")
    btns.pack(pady=10)
    tk.Button(btns, text="Apply", command=apply_and_close, width=10).pack(side="left", padx=6)
    tk.Button(btns, text="Cancel", command=cancel, width=10).pack(side="left", padx=6)
