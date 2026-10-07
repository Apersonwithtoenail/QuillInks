# Lyrical

**Terminal live lyrics for any MPRIS player — Spotify, mpv, VLC, Rhythmbox, anything playerctl can see.**

Shows synced lyrics for the track currently playing, right in your terminal. Centered layout, progress bar, fading context lines, and a steady highlight on the active line. No API key needed — lyrics come from LRCLIB.

## Features

- Live synced lyrics for any MPRIS-compatible player
- Centered layout with progress bar
- Current line highlighted, context lines fade out
- Fuzzy fallback when exact match fails
- Alt-screen buffer — no scrollback pollution, no flicker
- Auto-reload on track change

## Requirements

- playerctl — sudo apt install playerctl
- python3

## Install

    git clone https://github.com/Apersonwithtoenail/Lyrical.git
    cd Lyrical
    cp lyrical.py ~/bin/live_lyrics.py
    chmod +x ~/bin/live_lyrics.py

Make sure ~/bin is on your PATH (it usually already is on Kali).

## Usage

Play something in any MPRIS-compatible player, then:

    python3 ~/bin/live_lyrics.py

## Controls

| Key | Action |
|-----|--------|
| Ctrl-C | Quit |

## How it works

1. Polls playerctl for the current track
2. Looks up the track on LRCLIB (exact match, falls back to fuzzy)
3. If synced lyrics exist, renders them line-by-line with a progress bar
4. Fades older lines, highlights the active one

## Platform status

| Platform | Status |
|----------|--------|
| Linux (MPRIS) | Tested |
| macOS | No MPRIS |
| Windows | No MPRIS |

## License

MIT — see LICENSE.

