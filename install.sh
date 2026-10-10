#!/usr/bin/env bash
# install.sh — install QuillInks to ~/.local/bin + app menu
set -e

APP_NAME="QuillInks"
APP_ID="quillinks"
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/quillinks_gtk.py"

BIN="$HOME/.local/bin"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS="$HOME/.local/share/applications"
mkdir -p "$BIN" "$ICONS" "$APPS"

[ -f "$SCRIPT" ] || { echo "❌ missing: $SCRIPT"; exit 1; }
chmod +x "$SCRIPT"

# wrapper script — pins /usr/bin/python3 so a stray venv can't break it
cat > "$BIN/$APP_ID" <<WRAP
#!/usr/bin/env bash
GSK_RENDERER=cairo /usr/bin/python3 "$SCRIPT" "\$@"
WRAP
chmod +x "$BIN/$APP_ID"

# icon
cp "$(dirname "$SCRIPT")/assets/icon.svg" "$ICONS/$APP_ID.svg"

# .desktop
cat > "$APPS/$APP_ID.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Text Editor
Comment=Modern GTK4 text editor
Exec=$BIN/$APP_ID
Icon=$APP_ID
Terminal=false
Categories=Utility;TextEditor;Development;
Keywords=editor;text;code;
DESKTOP

# refresh
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "✅ $APP_NAME installed"
echo "   Run from terminal:  $APP_ID"
echo "   Or search the app menu."
echo "   Uninstall:          ./uninstall.sh"
