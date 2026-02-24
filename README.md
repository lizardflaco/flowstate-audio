# FlowState Audio — Native macOS App

A polished, native macOS application for creating professional sleep/meditation audio with binaural beats.

## Features

- 🎵 **Drag & Drop Audio** — Drop your audio files, I'll analyze and sequence them
- 🧠 **Binaural Beats** — Real binaural generation with presets (Delta, Theta, Alpha)
- 🎚️ **Professional Mixing** — Intelligent crossfades, loudness normalization
- 🎬 **Video Export** — Black screen, image slideshow, or hybrid modes
- ✨ **Native macOS UI** — Dark theme, smooth animations, proper integration

## Requirements

- macOS 10.14 or later
- ffmpeg (`brew install ffmpeg`)
- Python 3.8+ (for running from source)

## Installation

### Option 1: Pre-built App (Recommended)

1. Download `FlowState-Audio-v1.0.0.dmg`
2. Double-click to mount
3. Drag `FlowState.app` to Applications
4. Launch from Applications folder

### Option 2: Run from Source

```bash
cd flowstate-gui/src
pip install PyQt6 numpy
python3 FlowState.py
```

## Building from Source

```bash
cd flowstate-gui
./build.sh
```

This creates `FlowState-Audio-v1.0.0.dmg` in the parent directory.

## Usage

1. **Add Audio Files** — Drop files or use the browse button
2. **Choose Binaural Preset** — Select frequency for desired mental state
3. **Adjust Settings** — Crossfade duration, loudness, etc.
4. **Configure Video** — Black screen, images, or audio-only
5. **Create Master Track** — Export to Desktop/FlowState Exports/

## Exports

All exports are saved to `~/Desktop/FlowState Exports/`:
- `{project_name}_master.wav` — 24-bit master audio
- `{project_name}.mp4` — Video with audio (if video mode selected)

## Binaural Presets

| Preset | Frequency | Best For |
|--------|-----------|----------|
| Delta (2.5 Hz) | Deep Sleep | Overnight sleep, healing |
| Theta Deep (6 Hz) | Deep Meditation | Creativity, REM states |
| Theta Light (4.5 Hz) | Pre-Sleep | Drifting, light meditation |
| Alpha (10 Hz) | Calm Focus | Stress relief, background work |
| Alpha Light (8 Hz) | Gentle Relaxation | Mindful calm |

---

Built with ❤️‍🔥 for Jud Smith
