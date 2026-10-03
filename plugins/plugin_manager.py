"""Plugin manager — install/uninstall community plugins."""
import json
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox


MANIFEST_URL = "https://raw.githubusercontent.com/Apersonwithtoenail/QuillInks/main/plugins/manifest.json"
LOCAL_MANIFEST = Path(__file__).parent / "manifest.json"
PLUGINS_DIR = Path(__file__).parent


def fetch_manifest():
    """Try remote first, fall back to local."""
    try:
        with urllib.request.urlopen(MANIFEST_URL, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        try:
            return json.loads(LOCAL_MANIFEST.read_text())
        except Exception:
            return {"plugins": []}


def open_plugin_manager(root, on_change=None):
    """Show plugin manager dialog. Calls on_change() after install/uninstall."""
    win = tk.Toplevel(root)
    win.title("Plugin Manager")
    win.geometry("620x560")
    win.transient(root)
    win.configure(bg="#1e1e1e")

    tk.Label(win, text="Plugin Manager", bg="#1e1e1e", fg="#d4d4d4",
             font=("Sans", 13, "bold")).pack(pady=(14, 4))
    tk.Label(win, text="Install from community · Delete to remove",
             bg="#1e1e1e", fg="#888", font=("Sans", 9)).pack()

    # Scrollable body
    outer = tk.Frame(win, bg="#1e1e1e")
    outer.pack(fill="both", expand=True, padx=16, pady=8)
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

    status = tk.Label(win, text="", bg="#1e1e1e", fg="#4ec9b0", font=("Sans", 9))
    status.pack()

    def installed_ids():
        return {p.stem for p in PLUGINS_DIR.glob("*.py")}

    def rebuild():
        for c in inner.winfo_children():
            c.destroy()

        manifest = fetch_manifest()
        plugins = manifest.get("plugins", [])
        installed = installed_ids()

        # --- INSTALLED section ---
        tk.Label(inner, text="  INSTALLED", bg="#252526", fg="#4ec9b0",
                 font=("Sans", 10, "bold"), anchor="w").pack(fill="x", pady=(8, 4))

        if not installed:
            tk.Label(inner, text="  (none)", bg="#252526", fg="#888",
                     font=("Sans", 10, "italic"), anchor="w").pack(fill="x")

        for pid in sorted(installed):
            row = tk.Frame(inner, bg="#2d2d30", pady=6)
            row.pack(fill="x", padx=8, pady=2)
            meta = next((p for p in plugins if p["id"] == pid), None)
            label = meta["name"] if meta else pid
            desc = meta["description"] if meta else "(installed locally)"
            left = tk.Frame(row, bg="#2d2d30")
            left.pack(side="left", fill="x", expand=True, padx=8)
            tk.Label(left, text=label, bg="#2d2d30", fg="#d4d4d4",
                     font=("Sans", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(left, text=desc, bg="#2d2d30", fg="#a0a0a0",
                     font=("Sans", 9), anchor="w", justify="left").pack(fill="x")

            def delete(p=pid, name=label):
                if not messagebox.askyesno("Delete", f"Delete plugin '{name}'?"):
                    return
                target = PLUGINS_DIR / f"{p}.py"
                if target.exists():
                    target.unlink()
                status.config(text=f"Deleted: {name}")
                if on_change:
                    try: on_change()
                    except Exception: pass
                rebuild()

            tk.Button(row, text="Delete", command=delete,
                      bg="#5a1d1d", fg="#ffcccc", activebackground="#7a2d2d",
                      relief="flat", padx=14).pack(side="right", padx=8)

        # --- AVAILABLE section ---
        tk.Label(inner, text="  AVAILABLE FROM COMMUNITY", bg="#252526", fg="#dcdcaa",
                 font=("Sans", 10, "bold"), anchor="w").pack(fill="x", pady=(16, 4))

        available = [p for p in plugins if p["id"] not in installed]
        if not available:
            tk.Label(inner, text="  (all installed — nothing new)",
                     bg="#252526", fg="#888", font=("Sans", 10, "italic"),
                     anchor="w").pack(fill="x")

        for meta in available:
            row = tk.Frame(inner, bg="#2d2d30", pady=6)
            row.pack(fill="x", padx=8, pady=2)
            left = tk.Frame(row, bg="#2d2d30")
            left.pack(side="left", fill="x", expand=True, padx=8)
            tk.Label(left, text=meta.get("name", meta["id"]), bg="#2d2d30", fg="#d4d4d4",
                     font=("Sans", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(left, text=meta.get("description", ""), bg="#2d2d30", fg="#a0a0a0",
                     font=("Sans", 9), anchor="w", justify="left").pack(fill="x")
            tk.Label(left, text=f"by {meta.get('author', 'unknown')} · v{meta.get('version', '?')}",
                     bg="#2d2d30", fg="#6a9955", font=("Sans", 8)).pack(anchor="w")

            def install(m=meta):
                status.config(text=f"Downloading {m['name']}…")
                win.update_idletasks()
                try:
                    url = m["url"]
                    with urllib.request.urlopen(url, timeout=15) as r:
                        data = r.read()
                    dest = PLUGINS_DIR / m["file"]
                    dest.write_bytes(data)
                    status.config(text=f"Installed: {m['name']}")
                    if on_change:
                        try: on_change()
                        except Exception: pass
                    rebuild()
                except Exception as e:
                    status.config(text=f"Failed: {e}")
                    messagebox.showerror("Install failed", str(e))

            tk.Button(row, text="Install", command=install,
                      bg="#1d4a5a", fg="#cceeff", activebackground="#2d6a8a",
                      relief="flat", padx=14).pack(side="right", padx=8)

    def cleanup_and_close():
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")
        win.destroy()

    rebuild()

    tk.Button(win, text="Close", command=cleanup_and_close,
              bg="#3d3d3d", fg="#d4d4d4", relief="flat",
              padx=20, pady=4).pack(pady=10)
