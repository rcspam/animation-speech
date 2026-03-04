"""Internationalization, color parsing, and config normalization utilities."""

import os
import gettext


def _setup_i18n():
    """Set up internationalization using gettext."""
    domain = 'animation-speech'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    locale_dirs = [
        os.path.join(script_dir, '..', 'locales'),
        os.path.join(script_dir, 'locales'),
        os.path.expanduser('~/.local/share/animation-speech/locales'),
        '/usr/local/share/animation-speech/locales',
        '/usr/share/locale',
    ]
    for d in locale_dirs:
        if os.path.isdir(d):
            try:
                return gettext.translation(domain, localedir=d).gettext
            except FileNotFoundError:
                continue
    return gettext.gettext

_ = _setup_i18n()


def parse_color(value):
    """Convert a color (list, hex, name) to normalized [R, G, B, A] (0.0-1.0)"""
    if isinstance(value, (list, tuple)):
        if len(value) == 3:
            return [float(value[0]), float(value[1]), float(value[2]), 1.0]
        return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]

    if isinstance(value, str):
        value = value.strip()
        if value.startswith('#'):
            hex_str = value[1:]
            if len(hex_str) == 3:
                hex_str = ''.join(c * 2 for c in hex_str)
            if len(hex_str) == 6:
                r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                return [r / 255, g / 255, b / 255, 1.0]
            if len(hex_str) == 8:
                r, g, b, a = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), int(hex_str[6:8], 16)
                return [r / 255, g / 255, b / 255, a / 255]

    return [1.0, 1.0, 1.0, 1.0]


def normalize_config_colors(config):
    """Normalize all config colors to [R, G, B, A]"""
    colors = config.get('colors', {})
    for key in ('background', 'primary', 'secondary'):
        if key in colors:
            colors[key] = parse_color(colors[key])
    if 'gradient' in colors:
        colors['gradient'] = [parse_color(c) for c in colors['gradient']]
    bg = config.get('background', {})
    if isinstance(bg, dict):
        if 'color' in bg:
            bg['color'] = parse_color(bg['color'])
        if 'border_color' in bg:
            bg['border_color'] = parse_color(bg['border_color'])
