# Quillinks

A modern text editor for terminal and desktop. Built from scratch in Python.

Two editors in one repo:

- **TUI** (`quillinks.py`) — terminal editor built on [Textual](https://textual.textualize.io/)
- **GUI** (`quillinks_gui.py`) — desktop editor built on Tkinter

Both share the same features and shortcuts.

---

## Features

### Editing
- Tabs (Ctrl+T, Ctrl+W, Ctrl+PgUp/PgDn)
- Split panes (Ctrl+\\ to toggle, drag to resize)
- Line numbers gutter
- Word wrap, column ruler
- Auto-indent, auto-pairing brackets/quotes
- Bracket matching
- Comment/uncomment lines (Ctrl+/)
- Duplicate line (Ctrl+D), delete line (Ctrl+Shift+K)
- Case conversion, sort lines, trim whitespace
- Tabs to spaces conversion
- Read-only mode

### File handling
- Open, save, save-as
- Path completion in Open/Save dialog (Tab to autocomplete)
- Recent files menu
- Revert to disk
- Autosave every 5 seconds
- Line ending detection and conversion (LF / CRLF / CR)
- BOM detection and preservation
- Trailing-newline-at-EOF enforcement
- Portable mode (QUILLINKS_PORTABLE=1)

### Find & Replace
- Case-sensitive / whole-word
- Highlight all matches live
- Search history

### Appearance
- 6 themes: dark, light, high-contrast, gruvbox, nord, solarized
- Font family and size
- Zoom (Ctrl++, Ctrl+-, Ctrl+0)
- Fullscreen (F11)
- Whitespace visibility toggle
- EOL markers toggle

### Plugin system
- plugins/ folder with install/delete manager
- Community manifest at plugins/manifest.json
- Plugin Manager UI (Tools -> Plugin Manager)
- Ships with a Font Picker plugin

### Configuration
- Persists to ~/.config/quillinks/settings.json
- Saves window geometry, font, theme, tab width, and more

---

## Install

### Linux
Tkinter is included with Python:

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 quillinks_gui.py

### Windows
Install Python from [python.org](https://www.python.org/downloads/) (Tkinter is bundled), then:

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python quillinks_gui.py

Config lives at `%APPDATA%\Quillinks\`.

### macOS
Tkinter needs to be installed separately:

    brew install python-tk
    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 quillinks_gui.py

Config lives at `~/Library/Application Support/Quillinks/`.

### TUI (terminal)

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python quillinks.py

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| Ctrl+T | New tab |
| Ctrl+W | Close tab |
| Ctrl+\\ | Toggle split |
| Ctrl+Shift+W | Close active pane |
| Ctrl+PgUp / PgDn | Prev / next tab |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Q | Quit |
| Ctrl+A | Select all |
| Ctrl+Z / Ctrl+Y | Undo / Redo |
| Ctrl+D | Duplicate line |
| Ctrl+Shift+K | Delete line |
| Ctrl+/ | Toggle comment |
| Ctrl+F or Ctrl+H | Find & Replace |
| Ctrl+G | Go to line |
| Ctrl++ / Ctrl+- | Zoom |
| Ctrl+Shift+F | Font picker |
| F5 | Insert date/time |
| F11 | Fullscreen |
| F1 | Shortcuts dialog |

Full list: press F1 in the app.

---

## Plugin system

Quillinks supports community plugins. The plugin manager downloads .py files from the manifest URL into plugins/.

### Currently available

- **Font Picker** — browse all system fonts with live preview (Ctrl+Shift+F)

### Installing a plugin

Open the app -> Tools -> Plugin Manager -> click Install next to any available plugin.

### Writing a plugin

Drop a .py file in plugins/. See plugins/font_picker.py for the pattern.

### Manifest format

See plugins/manifest.json.

Want to add your plugin? Open a PR editing plugins/manifest.json.

---

## Roadmap

- [x] **Tier 0** — MVP: tabs, splits, path completion, themes, config (current)
- [ ] **Tier 1** — syntax highlighting, regex search, drag-drop, external-change detection, command palette
- [ ] **Tier 2** — multi-cursor, code folding, snippets, autocomplete
- [ ] **Tier 3** — IME/CJK, bidi text, grapheme clusters

---

## Config location

| OS | Path |
|----|------|
| Linux | ~/.config/quillinks/ |
| Portable | ./config/ (set QUILLINKS_PORTABLE=1) |

Files:
- settings.json — theme, font, tab width, geometry, toggles
- recent.json — recently opened files
- search_history.json — recent searches
- fonts_cache.json — cached font list (24h TTL)

---

## License

MIT — see LICENSE.
