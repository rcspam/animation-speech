# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A transparent overlay animation for Wayland that displays speech activity indicators. Uses GTK3 with gtk-layer-shell for true transparent overlays on Wayland compositors. Controlled via UNIX signals (SIGUSR1/SIGUSR2).

## Key Commands

```bash
# Run the animation (with optional config file and CLI overrides)
./animation-speech.py [config.yaml] [-w WIDTH] [-H HEIGHT] [-p POSITION] [-mb MARGIN_BOTTOM] [--on-escape CMD]

# After installation (.deb or install.sh), the command is:
animation-speech [config.yaml] [OPTIONS]

# Visual config selector
animation-speech --choose

# Control a running instance
./control.sh start     # Send SIGUSR1 - activate animation
./control.sh stop      # Send SIGUSR2 - deactivate animation
./control.sh quit      # Send SIGTERM - exit application
./control.sh status    # Show running state

# Build zipapp
make build                # → animation-speech.pyz

# i18n
make pot                  # Extraire les chaînes traduisibles
make update-po            # Mettre à jour les fichiers .po
make mo                   # Compiler les fichiers .mo
make stats                # Statistiques de traduction

# Install (user-level by default)
./install.sh [--user|--system|--uninstall]

# Debian package
cd debian && ./build-deb.sh
sudo dpkg -i animation-speech_1.2.0_all.deb
```

## Architecture

Package Python modulaire `animation_speech/` distribué via zipapp (.pyz) :

```
animation_speech/
    __init__.py          — version
    __main__.py          — entry point (zipapp + python -m)
    constants.py         — VALID_*, COLOR_PALETTES, PARAM_VISIBILITY
    utils.py             — i18n (_), parse_color(), normalize_config_colors()
    draw_mixin.py        — AnimationDrawMixin (Cairo, 8 types de dessin)
    animation.py         — SpeechAnimation + AnimationPreview + AUDIO_AVAILABLE
    gradient_editor.py   — GradientEditor (widget GTK3)
    config_editor.py     — ConfigEditor (éditeur de config avec preview overlay)
    config_chooser.py    — ConfigChooser (sélecteur visuel FlowBox)
    main.py              — argparse, list/find configs, entry point
```

`animation-speech.py` à la racine est un wrapper de développement.

**Dépendances inter-modules** :
- `constants.py`, `utils.py` → aucune dépendance interne
- `draw_mixin.py` → utils
- `animation.py` → utils, constants, draw_mixin
- `gradient_editor.py` → utils
- `config_editor.py` → utils, constants, gradient_editor, animation
- `config_chooser.py` → utils, constants, config_editor, animation (+ lazy import main)
- `main.py` → utils, constants, animation, config_chooser (lazy imports)

**Fonctionnalités** :
- `gtk-layer-shell` pour overlay Wayland transparent
- Chargement YAML + surcharge CLI
- PID file `/tmp/speech-animation.pid`
- Audio optionnel via PyAudio (modulation micro)
- Détection mute via `pactl` (PulseAudio/PipeWire) avec fallback `amixer` (ALSA)

**Animation types** (set via `animation_type` in config):
- `wave` - Flowing wave pattern (default)
- `equalizer` - Vertical bars
- `circular` - Concentric circles (dynamic spawn, direction: outward/inward/ping-pong)
- `particles` - Animated particles
- `soundwave` - Vertical bars waveform style
- `soundwave-curve` - Symmetric smooth curves (mirror)
- `circular-wave` - Vibrating circle with sinusoidal deformation
- `circular-bars` - Radial bars from a central circle

**Signal handling**:
- SIGUSR1: Start animation
- SIGUSR2: Stop animation
- SIGTERM/SIGINT: Clean shutdown with PID file cleanup

**Escape cancellation** (`--on-escape CMD`):
- When `--on-escape` is passed, the window uses `KeyboardMode.EXCLUSIVE` (grabs all keyboard input via layer-shell)
- On Escape key press: executes CMD via `subprocess.Popen(shell=True)`, then calls `cleanup_and_exit()`
- All other key events are consumed (returns True)
- Without `--on-escape`: default behavior (`KeyboardMode.NONE`, no focus, click passthrough)
- Used by `stt_rapha.sh` / `stt_translate.sh` to cancel recording without transcribing

## Configuration

Primary config: `config.yaml`
Example configs: `config.examples/*.yaml` (audio) and `config.examples/no-audio/*.yaml`

Key config sections:
- `animation_type`, `position`, `width`, `height`
- `colors`: background/primary/secondary/gradient in hex or RGBA float format
- `animation`: fps, bar_count, bar_width, bars_rotation, smoothing, intensity, wave_frequency, circle_count, circle_speed, circle_direction, wave_count, fill_wave, fill_opacity
- `background`: optional rounded capsule (enabled, color, padding, border_width, border_color)
- Callbacks: `on_position_changed_cb`, `on_delete_cb`, `on_save_cb` (ConfigEditor → ConfigChooser)
- `audio`: optional microphone modulation (enabled, sensitivity, smoothing)
- `layer`: Wayland layer-shell settings (layer, exclusive_zone, margins)

## Dependencies

System packages required:
- `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0`, `python3-yaml`
- `gtk-layer-shell`, `gir1.2-gtklayershell-0.1` (for true Wayland overlay)
- `python3-pyaudio` (optional, for microphone modulation)

## Language

The project uses French for documentation, commit messages, and user-facing strings.
