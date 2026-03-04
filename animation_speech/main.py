"""Entry point, argparse, and config file discovery utilities."""

import os
import sys
import argparse
import gettext as _gettext
import traceback

import yaml

from .utils import _, normalize_config_colors
from .constants import VALID_ANIMATION_TYPES

# Translate argparse's own strings (help, usage, etc.)
_gettext.textdomain('animation-speech')
argparse._ = _


def list_available_configs():
    """List all available configurations."""
    configs = {}

    # Directories to scan
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        (_("User - configs"), os.path.expanduser("~/.config/animation-speech")),
        (_("User - main"), os.path.expanduser("~/.local/share/animation-speech")),
        (_("User - examples"), os.path.expanduser("~/.local/share/animation-speech/config.examples")),
        (_("System - main"), "/usr/local/share/animation-speech"),
        (_("System - examples"), "/usr/local/share/animation-speech/config.examples"),
        (_("Script - main"), os.path.join(script_dir, '..')),
        (_("Script - examples"), os.path.join(script_dir, '..', "config.examples")),
    ]

    for label, directory in search_dirs:
        if os.path.isdir(directory):
            try:
                for root, dirs, files in os.walk(directory):
                    for filename in files:
                        if filename.endswith('.yaml') or filename.endswith('.yml'):
                            name_without_ext = filename.rsplit('.', 1)[0]
                            if name_without_ext not in configs:
                                configs[name_without_ext] = (label, os.path.join(root, filename))
            except PermissionError:
                pass

    return configs


def display_available_configs():
    """Display all available configurations."""
    configs = list_available_configs()

    if not configs:
        print(_("No configuration found"))
        return

    print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print(_("\u2551          Available configurations                        \u2551"))
    print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
    print()

    # Group by location
    by_location = {}
    for name, (location, path) in configs.items():
        if location not in by_location:
            by_location[location] = []
        by_location[location].append((name, path))

    for location in by_location:
        print(f"\U0001f4c1 {location}")
        for name, path in sorted(by_location[location]):
            anim_type = "?"
            try:
                with open(path, 'r') as f:
                    for line in f:
                        if line.strip().startswith('animation_type:'):
                            anim_type = line.split(':')[1].strip()
                            break
            except Exception:
                pass

            print(f"   \u2022 {name:<25} [{anim_type}]")
        print()

    print(_("Usage:"))
    print(_("   animation-speech NAME"))
    print()
    print(_("   Examples:"))
    if configs:
        examples = list(configs.keys())[:3]
        for ex in examples:
            print(f"     animation-speech {ex}")
    print()


def find_config_file(config_path):
    """Search for the config file in several standard locations."""
    # If the path is absolute and exists, use it directly
    if os.path.isabs(config_path) and os.path.exists(config_path):
        return config_path

    # If the file exists in the current directory
    if os.path.exists(config_path):
        return config_path

    # Add .yaml if no extension
    if not config_path.endswith('.yaml') and not config_path.endswith('.yml'):
        config_with_ext = config_path + '.yaml'
    else:
        config_with_ext = config_path

    # If the file with extension exists in the current directory
    if os.path.exists(config_with_ext):
        return config_with_ext

    # Extract just the filename if it's a path
    config_basename = os.path.basename(config_with_ext)

    # Standard directories to scan
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        os.path.expanduser("~/.config/animation-speech"),
        os.path.expanduser("~/.local/share/animation-speech"),
        "/usr/local/share/animation-speech",
        os.path.join(script_dir, '..'),
    ]

    # Search in each directory and its subdirectories
    for base_dir in search_dirs:
        if not os.path.isdir(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            candidate = os.path.join(root, config_basename)
            if os.path.exists(candidate):
                return candidate

    # If the original path contains /, also search with the full relative path
    if "/" in config_with_ext:
        for base_dir in search_dirs:
            candidate = os.path.join(base_dir, config_with_ext)
            if os.path.exists(candidate):
                return candidate

    # If no file found, return the original path for the error
    return config_with_ext


def main():
    parser = argparse.ArgumentParser(
        description=_('Speech animation for Wayland controlled by UNIX signals'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_('''
Usage examples:
  %(prog)s --list                             # List all available configs
  %(prog)s                                    # Default configuration
  %(prog)s monochrome-bw                      # Just the name (adds .yaml auto)
  %(prog)s wave-energetic                     # Another example
  %(prog)s -w 1200 -mb 50                     # Width 1200px, 50px from bottom
  %(prog)s monochrome-bw -w 1400 -H 150       # Config + dimension overrides

Control:
  kill -SIGUSR1 <PID>    # Start animation
  kill -SIGUSR2 <PID>    # Stop animation

Automatic search:
  For "monochrome-bw" -> searches "monochrome-bw.yaml" in:
  1. ~/.config/animation-speech/
  2. ~/.local/share/animation-speech/config.examples/
  3. /usr/local/share/animation-speech/config.examples/
  4. Script directory/config.examples/
        ''')
    )

    parser.add_argument('config', nargs='?', default='config.yaml',
                        help=_('YAML configuration file (default: config.yaml)'))

    # List and selector
    parser.add_argument('-l', '--list', action='store_true',
                        help=_('List all available configurations'))
    parser.add_argument('--choose', nargs='?', const='', default=None, metavar='FILTER',
                        help=_('Open visual selector (optional filter, e.g.: --choose kurve)'))

    # Dimensions
    parser.add_argument('-w', '--width', type=int, metavar='PX',
                        help=_('Animation width in pixels'))
    parser.add_argument('-H', '--height', type=int, metavar='PX',
                        help=_('Animation height in pixels'))

    # Position and margins
    parser.add_argument('-p', '--position', choices=['top', 'bottom', 'left', 'right', 'center',
                                                      'top-left', 'top-right', 'bottom-left', 'bottom-right'],
                        help=_('Overlay position on screen'))
    parser.add_argument('-mt', '--margin-top', type=int, metavar='PX',
                        help=_('Margin from top of screen (in pixels)'))
    parser.add_argument('-mb', '--margin-bottom', type=int, metavar='PX',
                        help=_('Margin from bottom of screen (in pixels)'))
    parser.add_argument('-ml', '--margin-left', type=int, metavar='PX',
                        help=_('Margin from left of screen (in pixels)'))
    parser.add_argument('-mr', '--margin-right', type=int, metavar='PX',
                        help=_('Margin from right of screen (in pixels)'))

    # Animation parameters
    parser.add_argument('-s', '--speed', type=float, metavar='N',
                        help=_('Animation speed (0.5=slow, 2=normal, 5=fast)'))
    parser.add_argument('-c', '--count', type=int, metavar='N',
                        help=_('Number of curves/circles (default: 8 for wave, 12 for circular)'))

    # Rounded background (cartouche)
    parser.add_argument('--bg', action='store_true', default=None,
                        help=_('Enable rounded background (cartouche)'))
    parser.add_argument('--no-bg', action='store_true', default=None,
                        help=_('Disable rounded background'))
    parser.add_argument('--bg-opacity', type=float, metavar='N',
                        help=_('Rounded background opacity (0.0=invisible, 1.0=opaque, default: 0.85)'))

    # Audio capture
    parser.add_argument('-a', '--audio', action='store_true',
                        help=_('Enable microphone modulation'))
    parser.add_argument('--sensitivity', type=float, metavar='N',
                        help=_('Microphone sensitivity (default: 1.5)'))
    parser.add_argument('--on-escape', type=str, metavar='CMD',
                        help=_('Shell command to execute on Escape key (enables exclusive keyboard grab)'))

    args = parser.parse_args()

    # If --list, display the list and exit
    if args.list:
        display_available_configs()
        sys.exit(0)

    # If --choose, open the visual selector
    if args.choose is not None:
        from .config_chooser import ConfigChooser
        filter_name = args.choose if args.choose else None
        chooser = ConfigChooser(filter_name)
        chooser.run()
        sys.exit(0)

    # Determine rounded background state
    bg_enabled = None
    if args.bg:
        bg_enabled = True
    elif args.no_bg:
        bg_enabled = False

    # Create overrides dictionary
    cli_overrides = {
        'width': args.width,
        'height': args.height,
        'position': args.position,
        'margin_top': args.margin_top,
        'margin_bottom': args.margin_bottom,
        'margin_left': args.margin_left,
        'margin_right': args.margin_right,
        'speed': args.speed,
        'count': args.count,
        'audio': args.audio,
        'audio_sensitivity': args.sensitivity,
        'bg_enabled': bg_enabled,
        'bg_opacity': args.bg_opacity,
        'on_escape_cmd': args.on_escape,
    }

    # Remove None values from dictionary
    cli_overrides = {k: v for k, v in cli_overrides.items() if v is not None}

    # Find the configuration file
    config_path = find_config_file(args.config)

    try:
        from .animation import SpeechAnimation
        animation = SpeechAnimation(config_path, cli_overrides)
        animation.run()
    except FileNotFoundError as e:
        print(_("\nError: File not found - {error}").format(error=e))
        print(_("File searched: '{config}'").format(config=args.config))
        print(_("\nLocations checked:"))
        print(_("  - Current directory"))
        print("  - ~/.config/animation-speech/")
        print("  - ~/.local/share/animation-speech/")
        print("  - /usr/local/share/animation-speech/")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(_("\nYAML configuration error: {error}").format(error=e))
        print(_("Check the syntax of '{config}'").format(config=args.config))
        sys.exit(1)
    except KeyboardInterrupt:
        print(_("\nInterrupted by user"))
        sys.exit(0)
    except Exception as e:
        print(_("\nFatal error: {error}").format(error=e))
        traceback.print_exc()
        sys.exit(1)
