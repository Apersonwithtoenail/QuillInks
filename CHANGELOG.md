# Changelog

## [0.1.0] — 2026-10-03

### Added — Tier 0 complete

**Both editions (TUI + GUI)**
- Open, save, save-as, revert
- Undo / redo, cut / copy / paste, select all
- Find & replace with case-sensitive and whole-word modes
- Highlight all matches, search history
- Go to line, line ops (duplicate, delete, toggle comment)
- Case conversion, sort lines, trim whitespace
- Auto-indent, auto-pairing brackets/quotes, bracket matching
- Line numbers gutter, word wrap
- Whitespace visibility, EOL markers
- Status bar with line/col, encoding, tab state
- Font selection, zoom
- Themes: dark, light, high-contrast, gruvbox, nord, solarized
- Read-only mode, line ending detection + conversion (LF/CRLF/CR)
- BOM detection + preservation
- Tabs to spaces / spaces to tabs conversion
- Portable mode
- Config file at `~/.config/quillinks/settings.json`

**GUI-specific**
- Tabs, split panes with resize
- Path-completion dialog (Tab to autocomplete)
- Recent files menu
- Autosave every 5 seconds
- Window geometry persistence
- Column ruler
- F1 keyboard shortcuts dialog

**TUI-specific**
- Session save/restore
- Markdown preview

**Plugins**
- Plugin system with community manifest
- Plugin manager (install / delete)
- Font Picker plugin
