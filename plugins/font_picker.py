"""Optional font picker plugin for Quillinks."""
import tkinter as tk
import tkinter.font as tkfont


def open_font_picker(root, current_family, on_apply):
    win = tk.Toplevel(root)
    win.title("Choose Font")
    win.geometry("480x560")
    win.transient(root)
    win.configure(bg="#1e1e1e")

    tk.Label(win, text="Each name shown in its own font",
             bg="#1e1e1e", fg="#d4d4d4", font=("Sans", 11, "bold")).pack(pady=(12, 8))

    outer = tk.Frame(win, bg="#1e1e1e")
    outer.pack(fill="both", expand=True, padx=16, pady=4)
    canvas = tk.Canvas(outer, bg="#252526", highlightthickness=0)
    vbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg="#252526")
    canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")
    inner.bind("<Configure>", lambda e: (canvas.configure(scrollregion=canvas.bbox("all")),
                                          canvas.itemconfig("inner", width=canvas.winfo_width())))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig("inner", width=canvas.winfo_width()))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    all_fonts = sorted(set(tkfont.families(root)))
    selected = {"family": current_family}

    def make_row(name):
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
        def dbl(e): click(e); apply_and_close()

        lbl.bind("<Button-1>", click)
        lbl.bind("<Double-Button-1>", dbl)
        lbl.bind("<Enter>", hover)
        lbl.bind("<Leave>", unhover)
        if name == current_family:
            lbl.config(bg="#264f78", fg="#ffffff")

    for f in all_fonts:
        make_row(f)

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
