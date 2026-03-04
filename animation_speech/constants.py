"""Constants, palettes, and parameter visibility rules."""

VALID_ANIMATION_TYPES = (
    'wave', 'equalizer', 'circular', 'particles',
    'soundwave', 'soundwave-curve', 'circular-wave', 'circular-bars',
)

VALID_POSITIONS = (
    'bottom', 'top', 'center', 'left', 'right',
    'top-left', 'top-right', 'bottom-left', 'bottom-right',
    'manual',
)

# Predefined color palettes (RGBA 0.0-1.0)
COLOR_PALETTES = {
    'Catppuccin': {
        'primary': [0.93, 0.53, 0.59, 0.9],
        'secondary': [0.55, 0.84, 0.79, 0.9],
        'gradient': [
            [0.93, 0.53, 0.59, 0.9],
            [0.93, 0.83, 0.62, 0.9],
            [0.65, 0.85, 0.58, 0.9],
            [0.55, 0.84, 0.79, 0.9],
            [0.54, 0.68, 0.96, 0.9],
            [0.96, 0.74, 0.90, 0.9],
            [0.96, 0.66, 0.50, 0.9],
        ],
    },
    'Rainbow': {
        'primary': [1.0, 0.0, 0.3, 0.9],
        'secondary': [0.44, 0.16, 1.0, 0.9],
        'gradient': [
            [1.0, 0.0, 0.3, 0.9],
            [1.0, 0.8, 0.0, 0.9],
            [0.0, 0.9, 0.3, 0.9],
            [0.0, 0.8, 1.0, 0.9],
            [0.3, 0.4, 1.0, 0.9],
            [0.7, 0.2, 1.0, 0.9],
            [1.0, 0.3, 0.7, 0.9],
        ],
    },
    'Neon': {
        'primary': [0.0, 1.0, 0.53, 0.9],
        'secondary': [1.0, 0.0, 1.0, 0.9],
        'gradient': [
            [0.0, 1.0, 1.0, 0.9],
            [0.0, 1.0, 0.53, 0.9],
            [1.0, 0.0, 1.0, 0.9],
            [1.0, 1.0, 0.0, 0.9],
        ],
    },
    'Monochrome': {
        'primary': [1.0, 1.0, 1.0, 0.9],
        'secondary': [0.53, 0.53, 0.53, 0.9],
        'gradient': [
            [1.0, 1.0, 1.0, 0.9],
            [0.8, 0.8, 0.8, 0.9],
            [0.53, 0.53, 0.53, 0.9],
        ],
    },
    'Grayscale': {
        'primary': [0.8, 0.8, 0.8, 0.9],
        'secondary': [0.4, 0.4, 0.4, 0.9],
        'gradient': [
            [0.8, 0.8, 0.8, 0.9],
            [0.6, 0.6, 0.6, 0.9],
            [0.4, 0.4, 0.4, 0.9],
        ],
    },
}

# Parameter visibility per animation type
CIRCULAR_TYPES = {'circular', 'circular-wave', 'circular-bars'}
NON_CIRCULAR_TYPES = set(VALID_ANIMATION_TYPES) - CIRCULAR_TYPES

PARAM_VISIBILITY = {
    'wave_frequency': {'wave', 'circular', 'soundwave-curve', 'circular-wave', 'circular-bars'},
    'bar_count':      {'equalizer', 'soundwave', 'circular-bars'},
    'bar_width':      {'circular-bars'},
    'bars_rotation':  {'circular-bars'},
    'bar_spacing':    {'equalizer', 'soundwave'},
    'circle_count':   {'circular'},
    'circle_speed':   {'circular'},
    'circle_direction': {'circular'},
    'wave_count':     {'wave', 'soundwave-curve'},
    'fill_wave':      {'wave', 'soundwave-curve'},
    'fill_opacity':   {'wave', 'soundwave-curve'},
    '_dim_wh':        NON_CIRCULAR_TYPES,
    '_dim_radius':    CIRCULAR_TYPES,
}
