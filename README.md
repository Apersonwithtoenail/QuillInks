# QuillInks

**A modern text editor for terminal and desktop — built from scratch in Python.**

QuillInks ships three editions in one repo: a terminal UI built on Textual, a desktop GUI built on Tkinter, and a modern GTK4 edition. All share the same feature set and keyboard shortcuts.

## Features

### Editing
- Tabs (Ctrl+T, Ctrl+W, Ctrl+PgUp/PgDn)
- Split panes (Ctrl+\ to toggle, drag to resize)
- Line numbers gutter
- Word wrap, column ruler
- Auto-indent, auto-pairing brackets/quotes
- Bracket matching
- Comment/uncomment lines (Ctrl+/)
- Duplicate line (Ctrl+D), delete line (Ctrl+Shift+K)
- Case conversion, sort lines, trim whitespace
- Tabs-to-spaces conversion
- Read-only mode

### File handling
- Open, save, save-as
- Path completion in Open/Save dialog (Tab to autocomplete)
- Recent files menu
- Revert to disk
- Autosave every 5 seconds
- Line-ending detection and conversion (LF / CRLF / CR)
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

## Requirements

- Python 3.9+
- Tkinter (bundled with most Python installs; needs python-tk on macOS)
- Textual (for the TUI edition — see requirements.txt)

## Install

### Linux (GUI)

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 quillinks_gui.py

### macOS (GUI)

    brew install python-tk
    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 quillinks_gui.py

### Windows (GUI)

Install Python from python.org (Tkinter bundled), then:

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python quillinks_gui.py

### GTK4 (in progress)

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 quillinks_gtk.py

Requires GTK4 and GtkSourceView 5:

    sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-gtksource-5

### TUI (terminal)

    git clone https://github.com/Apersonwithtoenail/QuillInks.git
    cd QuillInks
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python quillinks.py

## Usage

Open a file with Ctrl+O, save with Ctrl+S. Press F1 inside the app for the full shortcut list.

## Controls

| Key | Action |
|-----|--------|
| Ctrl+T | New tab |
| Ctrl+W | Close tab |
| Ctrl+\ | Toggle split |
| Ctrl+Shift+W | Close active pane |
| Ctrl+PgUp / PgDn | Previous / next tab |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Q | Quit |
| Ctrl+A | Select all |
| Ctrl+Z / Ctrl+Y | Undo / Redo |
| Ctrl+D | Duplicate line |
| Ctrl+Shift+K | Delete line |
| Ctrl+/ | Toggle comment |
| Ctrl+F / Ctrl+H | Find & Replace |
| Ctrl+G | Go to line |
| Ctrl++ / Ctrl+- | Zoom |
| Ctrl+Shift+F | Font picker |
| F5 | Insert date/time |
| F11 | Fullscreen |
| F1 | Shortcuts dialog |

## Configuration

Config lives at:

| OS | Path |
|----|------|
| Linux | ~/.config/quillinks/ |
| macOS | ~/Library/Application Support/Quillinks/ |
| Windows | %APPDATA%\Quillinks\ |
| Portable | ./config/ (set QUILLINKS_PORTABLE=1) |

Files:

- settings.json — theme, font, tab width, geometry, toggles
- recent.json — recently opened files
- search_history.json — recent searches
- fonts_cache.json — cached font list (24h TTL)

## How it works

Two independent front-ends sharing a feature set:

- TUI — Textual app (quillinks.py)
- GUI — Tkinter app (quillinks_gui.py)

Both read and write the same config layout and expose the same shortcuts.

## Platform status

| Platform | Status |
|----------|--------|
| Linux | Tested |
| macOS | GUI tested, TUI untested |
| Windows | GUI tested, TUI untested |

## Roadmap

- [x] Tier 0 — MVP: tabs, splits, path completion, themes, config
- [x] Tier 1 — syntax highlighting, regex search, drag-drop, external-change detection, command palette
- [ ] Tier 2 — multi-cursor, code folding, snippets, autocomplete
- [ ] Tier 3 — IME/CJK, bidi text, grapheme clusters

## Plugin system

QuillInks supports community plugins. The plugin manager downloads .py files from the manifest URL into plugins/.

Available now:

- Font Picker — browse all system fonts with live preview (Ctrl+Shift+F)

Installing: Open the app -> Tools -> Plugin Manager -> Install.

Writing one: Drop a .py file in plugins/. See plugins/font_picker.py.

Manifest: See plugins/manifest.json. Want to add yours? Open a PR editing that file.

## License

MIT — see LICENSE.
