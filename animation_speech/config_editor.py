"""ConfigEditor — right-panel editor with overlay preview."""

import os
import copy
import math
import struct
import threading
import yaml

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell, GLib, Gdk, GObject
import cairo

from .utils import _, parse_color, normalize_config_colors
from .constants import (VALID_ANIMATION_TYPES, VALID_POSITIONS,
                        COLOR_PALETTES, PARAM_VISIBILITY, CIRCULAR_TYPES)
from .gradient_editor import GradientEditor
from .animation import AnimationPreview, AUDIO_AVAILABLE

# Conditional import for audio
try:
    import pyaudio
except ImportError:
    pass


class ConfigEditor(Gtk.Box):
    """Configuration editor panel with live preview"""

    def __init__(self, config_dict, config_path=None, on_position_changed_cb=None, on_delete_cb=None, on_save_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.config = copy.deepcopy(config_dict)
        self.config_path = config_path
        self.on_position_changed_cb = on_position_changed_cb
        self.on_delete_cb = on_delete_cb
        self.on_save_cb = on_save_cb
        # Ensure config has a layer section
        if 'layer' not in self.config:
            self.config['layer'] = {
                'layer': 'overlay', 'exclusive_zone': 0,
                'margin': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
            }
        # Force square dimensions for circular types
        if self.config.get('animation_type') in CIRCULAR_TYPES:
            side = min(self.config.get('width', 200), self.config.get('height', 200))
            self.config['width'] = side
            self.config['height'] = side
        self.preview = AnimationPreview.__new__(AnimationPreview)
        # Initialize preview manually with our config
        self.preview.config = copy.deepcopy(self.config)
        normalize_config_colors(self.preview.config)
        self.preview.config_path = config_path or ''
        self.preview.name = self.config.get('_name', _("New"))
        self.preview.frame = 0
        self.preview.is_animating = True
        self.preview.audio_enabled = False
        self.preview.audio_level = 0.0
        bar_count = self.preview.config.get('animation', {}).get('bar_count', 20)
        self.preview.bars = [0.0] * bar_count
        self.preview.target_bars = [0.0] * bar_count
        self.preview.particles = []
        self.preview.circles = []
        self.preview._spawn_acc = 0.0

        self.overlay_window = None
        self._conditional_widgets = {}
        self._audio_running = False
        self._audio_thread = None
        self._build_ui()
        self._install_scroll_blockers(self)
        self._setup_overlay()

        # Start audio capture if enabled in config
        if self.config.get('audio', {}).get('enabled', False):
            self._start_audio_capture()

    def _build_ui(self):
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        # -- Header --
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = self.config.get('_name', os.path.basename(self.config_path or _("New")))
        self.header_label = Gtk.Label(label=_("Edit: {name}").format(name=name))
        self.header_label.get_style_context().add_class('title-label')
        self.header_label.set_halign(Gtk.Align.START)
        header.pack_start(self.header_label, True, True, 0)

        save_btn = Gtk.Button(label=_("Save as\u2026"))
        save_btn.connect('clicked', self._on_save)
        header.pack_end(save_btn, False, False, 0)

        self.save_current_btn = Gtk.Button(label=_("Save"))
        self.save_current_btn.connect('clicked', self._on_save_current)
        self.save_current_btn.set_sensitive(bool(self.config_path))
        header.pack_end(self.save_current_btn, False, False, 0)

        self.default_btn = Gtk.Button(label=_("Default"))
        self.default_btn.set_tooltip_text(_("Set as default configuration"))
        self.default_btn.connect('clicked', self._on_set_default)
        self.default_btn.set_sensitive(bool(self.config_path))
        header.pack_end(self.default_btn, False, False, 0)

        self.delete_btn = Gtk.Button(label=_("Delete"))
        self.delete_btn.get_style_context().add_class('destructive-action')
        self.delete_btn.connect('clicked', self._on_delete)
        self.delete_btn.set_sensitive(bool(self.config_path))
        header.pack_end(self.delete_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

        # -- YAML file path --
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        path_label = Gtk.Label(label=_("File:"))
        path_label.set_halign(Gtk.Align.START)
        path_box.pack_start(path_label, False, False, 0)
        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(os.path.abspath(self.config_path) if self.config_path else '')
        self.path_entry.set_editable(False)
        self.path_entry.set_can_focus(True)
        path_box.pack_start(self.path_entry, True, True, 0)
        self.pack_start(path_box, False, False, 2)

        # -- Preview info --
        self.preview_info = Gtk.Label(label=_("Preview displayed as overlay on desktop"))
        self.preview_info.set_halign(Gtk.Align.CENTER)
        self.preview_info.get_style_context().add_class('section-label')
        self.pack_start(self.preview_info, False, False, 4)

        # -- Scrollable controls --
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        controls_box.pack_start(self._build_type_section(), False, False, 0)
        controls_box.pack_start(self._build_colors_section(), False, False, 0)
        controls_box.pack_start(self._build_animation_section(), False, False, 0)
        controls_box.pack_start(self._build_cartouche_section(), False, False, 0)
        controls_box.pack_start(self._build_audio_section(), False, False, 0)

        scrolled.add(controls_box)
        self.pack_start(scrolled, True, True, 0)
        self._scrolled = scrolled

        # Apply initial visibility
        anim_type = self.config.get('animation_type', 'wave')
        self._update_param_visibility(anim_type)
        # Initial visibility of X/Y sliders (manual mode)
        is_manual = self.config.get('position') == 'manual'
        for w in self._conditional_widgets.get('_manual_pos', []):
            w.set_no_show_all(not is_manual)
            w.set_visible(is_manual)

    # --- Type & Dimensions section ---

    def _build_type_section(self):
        frame = Gtk.Frame(label=_(" Type & Dimensions "))
        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        row = 0
        grid.attach(Gtk.Label(label=_("Type"), halign=Gtk.Align.END), 0, row, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        for t in VALID_ANIMATION_TYPES:
            self.type_combo.append_text(t)
        self.type_combo.set_active(list(VALID_ANIMATION_TYPES).index(
            self.config.get('animation_type', 'wave')))
        self.type_combo.connect('changed', self._on_type_changed)
        grid.attach(self.type_combo, 1, row, 2, 1)

        row += 1
        grid.attach(Gtk.Label(label=_("Position"), halign=Gtk.Align.END), 0, row, 1, 1)
        self.pos_combo = Gtk.ComboBoxText()
        for p in VALID_POSITIONS:
            self.pos_combo.append_text(p)
        cur_pos = self.config.get('position', 'bottom')
        if cur_pos in VALID_POSITIONS:
            self.pos_combo.set_active(list(VALID_POSITIONS).index(cur_pos))
        self.pos_combo.connect('changed', self._on_position_changed)
        grid.attach(self.pos_combo, 1, row, 2, 1)

        # Largeur / Hauteur (types non-circulaires)
        row += 1
        self._lbl_width = Gtk.Label(label=_("Width"), halign=Gtk.Align.END)
        grid.attach(self._lbl_width, 0, row, 1, 1)
        self.width_spin = Gtk.SpinButton.new_with_range(50, 3000, 10)
        self.width_spin.set_value(self.config.get('width', 800))
        self.width_spin.connect('value-changed', lambda s: self._update_config(
            'width', int(s.get_value())))
        grid.attach(self.width_spin, 1, row, 1, 1)
        self._conditional_widgets.setdefault('_dim_wh', []).extend(
            [self._lbl_width, self.width_spin])

        row += 1
        self._lbl_height = Gtk.Label(label=_("Height"), halign=Gtk.Align.END)
        grid.attach(self._lbl_height, 0, row, 1, 1)
        self.height_spin = Gtk.SpinButton.new_with_range(20, 1000, 10)
        self.height_spin.set_value(self.config.get('height', 60))
        self.height_spin.connect('value-changed', lambda s: self._update_config(
            'height', int(s.get_value())))
        grid.attach(self.height_spin, 1, row, 1, 1)
        self._conditional_widgets.setdefault('_dim_wh', []).extend(
            [self._lbl_height, self.height_spin])

        # Radius (circular types) — sets width = height = radius * 2
        row += 1
        self._lbl_radius = Gtk.Label(label=_("Radius"), halign=Gtk.Align.END)
        grid.attach(self._lbl_radius, 0, row, 1, 1)
        cur_radius = min(self.config.get('width', 200), self.config.get('height', 200)) // 2
        self.radius_spin = Gtk.SpinButton.new_with_range(20, 500, 5)
        self.radius_spin.set_value(cur_radius)
        self.radius_spin.connect('value-changed', self._on_radius_changed)
        grid.attach(self.radius_spin, 1, row, 1, 1)
        self._conditional_widgets.setdefault('_dim_radius', []).extend(
            [self._lbl_radius, self.radius_spin])

        # Position X / Y (mode manuel uniquement)
        margins = self.config.get('layer', {}).get('margin', {})

        self._manual_pos_updating = False

        row += 1
        self._lbl_pos_x = Gtk.Label(label=_("Position X"), halign=Gtk.Align.END)
        grid.attach(self._lbl_pos_x, 0, row, 1, 1)
        self.pos_x_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 3840, 50)
        self.pos_x_scale.set_value(margins.get('left', 0))
        self.pos_x_scale.set_draw_value(False)
        self.pos_x_scale.connect('value-changed', self._on_manual_scale_changed)
        grid.attach(self.pos_x_scale, 1, row, 1, 1)
        self.pos_x_spin = Gtk.SpinButton.new_with_range(0, 5000, 50)
        self.pos_x_spin.set_value(margins.get('left', 0))
        self.pos_x_spin.connect('value-changed', self._on_manual_spin_changed)
        grid.attach(self.pos_x_spin, 2, row, 1, 1)
        self._conditional_widgets.setdefault('_manual_pos', []).extend(
            [self._lbl_pos_x, self.pos_x_scale, self.pos_x_spin])

        row += 1
        self._lbl_pos_y = Gtk.Label(label=_("Position Y"), halign=Gtk.Align.END)
        grid.attach(self._lbl_pos_y, 0, row, 1, 1)
        self.pos_y_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 2160, 50)
        self.pos_y_scale.set_value(margins.get('top', 0))
        self.pos_y_scale.set_draw_value(False)
        self.pos_y_scale.connect('value-changed', self._on_manual_scale_changed)
        grid.attach(self.pos_y_scale, 1, row, 1, 1)
        self.pos_y_spin = Gtk.SpinButton.new_with_range(0, 5000, 50)
        self.pos_y_spin.set_value(margins.get('top', 0))
        self.pos_y_spin.connect('value-changed', self._on_manual_spin_changed)
        grid.attach(self.pos_y_spin, 2, row, 1, 1)
        self._conditional_widgets.setdefault('_manual_pos', []).extend(
            [self._lbl_pos_y, self.pos_y_scale, self.pos_y_spin])

        frame.add(grid)
        return frame

    # --- Colors section ---

    def _build_colors_section(self):
        frame = Gtk.Frame(label=_(" Colors "))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(8)

        # Palettes
        palette_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        palette_box.pack_start(Gtk.Label(label=_("Palettes:"), halign=Gtk.Align.START), False, False, 0)
        for name in COLOR_PALETTES:
            btn = Gtk.Button(label=name)
            btn.connect('clicked', self._on_palette_clicked, name)
            palette_box.pack_start(btn, False, False, 0)
        vbox.pack_start(palette_box, False, False, 0)

        # Primary & Secondary & Background
        color_grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        colors = self.config.get('colors', {})

        color_grid.attach(Gtk.Label(label=_("Primary"), halign=Gtk.Align.END), 0, 0, 1, 1)
        self.primary_btn = self._make_color_button(
            colors.get('primary', [0.3, 0.8, 1.0, 0.9]),
            lambda rgba: self._update_color('primary', rgba))
        color_grid.attach(self.primary_btn, 1, 0, 1, 1)

        color_grid.attach(Gtk.Label(label=_("Secondary"), halign=Gtk.Align.END), 0, 1, 1, 1)
        self.secondary_btn = self._make_color_button(
            colors.get('secondary', [0.6, 0.4, 1.0, 0.7]),
            lambda rgba: self._update_color('secondary', rgba))
        color_grid.attach(self.secondary_btn, 1, 1, 1, 1)

        color_grid.attach(Gtk.Label(label=_("Background"), halign=Gtk.Align.END), 0, 2, 1, 1)
        self.bg_color_btn = self._make_color_button(
            colors.get('background', [0.0, 0.0, 0.0, 0.0]),
            lambda rgba: self._update_color('background', rgba))
        color_grid.attach(self.bg_color_btn, 1, 2, 1, 1)
        vbox.pack_start(color_grid, False, False, 0)

        # Gradient
        grad_label = Gtk.Label(label=_("Gradient:"), halign=Gtk.Align.START)
        vbox.pack_start(grad_label, False, False, 0)
        gradient_colors = colors.get('gradient', [
            colors.get('primary', [0.3, 0.8, 1.0, 0.9]),
            colors.get('secondary', [0.6, 0.4, 1.0, 0.7]),
        ])
        self.gradient_editor = GradientEditor(gradient_colors, self._on_gradient_changed)
        vbox.pack_start(self.gradient_editor, False, False, 0)

        frame.add(vbox)
        return frame

    # --- Animation params section ---

    def _build_animation_section(self):
        frame = Gtk.Frame(label=_(" Animation "))
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        anim = self.config.get('animation', {})
        row = 0

        row = self._add_slider_row(grid, row, "FPS", 'fps',
            anim.get('fps', 60), 10, 120, 1, 0)
        row = self._add_slider_row(grid, row, _("Intensity"), 'intensity',
            anim.get('intensity', 1.0), 0.1, 3.0, 0.1, 1)
        row = self._add_slider_row(grid, row, "Smoothing", 'smoothing',
            anim.get('smoothing', 0.3), 0.0, 1.0, 0.05, 2)
        row = self._add_slider_row(grid, row, _("Frequency"), 'wave_frequency',
            anim.get('wave_frequency', 3.0), 0.5, 10.0, 0.1, 1)
        row = self._add_slider_row(grid, row, _("Bar count"), 'bar_count',
            anim.get('bar_count', 20), 5, 100, 1, 0)
        row = self._add_slider_row(grid, row, _("Bar width"), 'bar_width',
            anim.get('bar_width', 15), 1, 30, 1, 0)
        row = self._add_slider_row(grid, row, "Rotation", 'bars_rotation',
            anim.get('bars_rotation', 0), 0, 360, 1, 0)
        row = self._add_slider_row(grid, row, _("Spacing"), 'bar_spacing',
            anim.get('bar_spacing', 5), 0, 20, 1, 0)
        row = self._add_slider_row(grid, row, _("Circle count"), 'circle_count',
            anim.get('circle_count', 12), 3, 30, 1, 0)
        row = self._add_slider_row(grid, row, _("Speed"), 'circle_speed',
            anim.get('circle_speed', 2.0), 0.1, 8.0, 0.1, 1)

        # Concentric circles direction
        dir_label = Gtk.Label(label=_("Direction"), xalign=0)
        grid.attach(dir_label, 0, row, 1, 1)
        dir_combo = Gtk.ComboBoxText()
        directions = [('outward', _('Outward')), ('inward', _('Inward')), ('ping-pong', _('Ping-pong'))]
        current_dir = anim.get('circle_direction', 'outward')
        for idx, (val, label) in enumerate(directions):
            dir_combo.append(val, label)
            if val == current_dir:
                dir_combo.set_active(idx)
        dir_combo.connect('changed', lambda c: self._update_anim('circle_direction', c.get_active_id()))
        grid.attach(dir_combo, 1, row, 2, 1)
        self._conditional_widgets.setdefault('circle_direction', []).extend([dir_label, dir_combo])
        row += 1

        row = self._add_slider_row(grid, row, _("Wave count"), 'wave_count',
            anim.get('wave_count', 1), 1, 5, 1, 0)

        # Fill wave checkbox
        fill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fill_check = Gtk.CheckButton(label=_("Fill curve"))
        fill_check.set_active(anim.get('fill_wave', False))
        fill_check.connect('toggled', lambda c: self._update_anim('fill_wave', c.get_active()))
        fill_box.pack_start(fill_check, False, False, 0)
        grid.attach(fill_box, 0, row, 3, 1)
        self._conditional_widgets.setdefault('fill_wave', []).append(fill_box)
        row += 1

        row = self._add_slider_row(grid, row, _("Fill opacity"), 'fill_opacity',
            anim.get('fill_opacity', 0.3), 0.0, 1.0, 0.05, 2)

        frame.add(grid)
        return frame

    # --- Cartouche section ---

    def _build_cartouche_section(self):
        frame = Gtk.Frame(label=_(" Cartouche (rounded background) "))
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        bg = self.config.get('background', {})
        row = 0

        check = Gtk.CheckButton(label=_("Enabled"))
        check.set_active(bg.get('enabled', False))
        check.connect('toggled', lambda c: self._update_bg('enabled', c.get_active()))
        grid.attach(check, 0, row, 3, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Color"), halign=Gtk.Align.END), 0, row, 1, 1)
        self.cart_color_btn = self._make_color_button(
            bg.get('color', [0.2, 0.2, 0.25, 0.85]),
            lambda rgba: self._update_bg('color', [rgba.red, rgba.green, rgba.blue, rgba.alpha]))
        grid.attach(self.cart_color_btn, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Padding"), halign=Gtk.Align.END), 0, row, 1, 1)
        pad_spin = Gtk.SpinButton.new_with_range(0, 30, 1)
        pad_spin.set_value(bg.get('padding', 10))
        pad_spin.connect('value-changed', lambda s: self._update_bg('padding', int(s.get_value())))
        grid.attach(pad_spin, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Border"), halign=Gtk.Align.END), 0, row, 1, 1)
        bw_spin = Gtk.SpinButton.new_with_range(0, 10, 0.5)
        bw_spin.set_value(bg.get('border_width', 0))
        bw_spin.set_digits(1)
        bw_spin.connect('value-changed', lambda s: self._update_bg('border_width', round(s.get_value(), 1)))
        grid.attach(bw_spin, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=_("Border color"), halign=Gtk.Align.END), 0, row, 1, 1)
        self.border_color_btn = self._make_color_button(
            bg.get('border_color', [1.0, 1.0, 1.0, 0.5]),
            lambda rgba: self._update_bg('border_color', [rgba.red, rgba.green, rgba.blue, rgba.alpha]))
        grid.attach(self.border_color_btn, 1, row, 1, 1)

        frame.add(grid)
        return frame

    # --- Audio section ---

    def _build_audio_section(self):
        frame = Gtk.Frame(label=_(" Audio (microphone) "))
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        audio = self.config.get('audio', {})
        row = 0

        check = Gtk.CheckButton(label=_("Enabled"))
        check.set_active(audio.get('enabled', False))
        check.connect('toggled', lambda c: self._update_audio('enabled', c.get_active()))
        if not AUDIO_AVAILABLE:
            check.set_sensitive(False)
            check.set_active(False)
        grid.attach(check, 0, row, 3, 1)
        row += 1

        if not AUDIO_AVAILABLE:
            warn = Gtk.Label(label=_("pyaudio not installed (sudo apt install python3-pyaudio)"))
            warn.set_halign(Gtk.Align.START)
            ctx = warn.get_style_context()
            css = Gtk.CssProvider()
            css.load_from_data(b"label { color: #cc6600; font-style: italic; font-size: 0.85em; }")
            ctx.add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            grid.attach(warn, 0, row, 3, 1)
            row += 1

        grid.attach(Gtk.Label(label=_("Sensitivity"), halign=Gtk.Align.END), 0, row, 1, 1)
        sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 5.0, 0.1)
        sens_scale.set_value(audio.get('sensitivity', 1.5))
        sens_scale.set_hexpand(True)
        sens_spin = Gtk.SpinButton.new_with_range(0.1, 5.0, 0.1)
        sens_spin.set_value(audio.get('sensitivity', 1.5))
        sens_spin.set_digits(1)
        self._link_scale_spin(sens_scale, sens_spin,
            lambda v: self._update_audio('sensitivity', v))
        grid.attach(sens_scale, 1, row, 1, 1)
        grid.attach(sens_spin, 2, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Smoothing", halign=Gtk.Align.END), 0, row, 1, 1)
        sm_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        sm_scale.set_value(audio.get('smoothing', 0.3))
        sm_scale.set_hexpand(True)
        sm_spin = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.05)
        sm_spin.set_value(audio.get('smoothing', 0.3))
        sm_spin.set_digits(2)
        self._link_scale_spin(sm_scale, sm_spin,
            lambda v: self._update_audio('smoothing', v))
        grid.attach(sm_scale, 1, row, 1, 1)
        grid.attach(sm_spin, 2, row, 1, 1)

        frame.add(grid)
        return frame

    # --- Helper methods ---

    def _make_color_button(self, rgba_list, on_change):
        btn = Gtk.ColorButton()
        gdk_rgba = Gdk.RGBA()
        gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba_list[:4]
        btn.set_rgba(gdk_rgba)
        btn.set_use_alpha(True)
        btn.connect('color-set', lambda b: on_change(b.get_rgba()))
        return btn

    def _add_slider_row(self, grid, row, label, param_name, value, vmin, vmax, step, digits):
        lbl = Gtk.Label(label=label, halign=Gtk.Align.END)
        grid.attach(lbl, 0, row, 1, 1)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, vmin, vmax, step)
        scale.set_value(value)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        grid.attach(scale, 1, row, 1, 1)

        spin = Gtk.SpinButton.new_with_range(vmin, vmax, step)
        spin.set_value(value)
        spin.set_digits(digits)
        grid.attach(spin, 2, row, 1, 1)

        if digits == 0:
            self._link_scale_spin(scale, spin, lambda v: self._update_anim(param_name, int(v)))
        else:
            self._link_scale_spin(scale, spin, lambda v: self._update_anim(param_name, round(v, digits)))

        if param_name in PARAM_VISIBILITY:
            widgets = [lbl, scale, spin]
            self._conditional_widgets.setdefault(param_name, []).extend(widgets)

        return row + 1

    def _link_scale_spin(self, scale, spin, on_change):
        updating = [False]
        def on_scale(s):
            if updating[0]:
                return
            updating[0] = True
            spin.set_value(s.get_value())
            on_change(s.get_value())
            updating[0] = False
        def on_spin(s):
            if updating[0]:
                return
            updating[0] = True
            scale.set_value(s.get_value())
            on_change(s.get_value())
            updating[0] = False
        scale.connect('value-changed', on_scale)
        spin.connect('value-changed', on_spin)

    # --- Config update callbacks ---

    def _update_config(self, key, value):
        self.config[key] = value
        if key in ('width', 'height', 'position') and self.config.get('position') == 'manual':
            self._clamp_manual_pos()
        self._sync_preview()

    @staticmethod
    def _propagate_scroll(widget, event):
        """Block scroll on Scale and redirect to parent ScrolledWindow"""
        GObject.signal_stop_emission_by_name(widget, 'scroll-event')
        parent = widget.get_parent()
        while parent and not isinstance(parent, Gtk.ScrolledWindow):
            parent = parent.get_parent()
        if parent:
            adj = parent.get_vadjustment()
            if event.direction == Gdk.ScrollDirection.SMOOTH:
                ok, dx, dy = event.get_scroll_deltas()
                delta = dy * 50
            elif event.direction == Gdk.ScrollDirection.DOWN:
                delta = 50
            else:
                delta = -50
            adj.set_value(adj.get_value() + delta)
        return True

    # Shared lists across all instances for the global GDK filter
    _block_widgets = []
    _scrolled_ref = None
    _gdk_filter_installed = False

    @classmethod
    def _install_scroll_blockers(cls, container):
        """Block scroll on Scale, SpinButton, ComboBox.
        Scale: signal_stop_emission_by_name in an instance handler.
        SpinButton/ComboBox: global GDK filter with pointer position detection
        (on Wayland, scroll-event goes to Window, not the widget)."""
        BLOCK_TYPES = (Gtk.SpinButton, Gtk.ComboBox, Gtk.ComboBoxText)

        # Update shared list (new ConfigEditor = new widgets)
        cls._block_widgets.clear()
        cls._scrolled_ref = getattr(container, '_scrolled', None)

        def _walk(widget):
            if isinstance(widget, Gtk.Scale):
                widget.connect('scroll-event', cls._propagate_scroll)
            elif isinstance(widget, BLOCK_TYPES):
                cls._block_widgets.append(widget)
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    _walk(child)
        _walk(container)

        # Install GDK filter only once
        if not cls._gdk_filter_installed:
            def _gdk_event_filter(event, data=None):
                if event.type == Gdk.EventType.SCROLL and cls._block_widgets:
                    for w in cls._block_widgets:
                        if not w.get_visible() or not w.get_mapped():
                            continue
                        toplevel = w.get_toplevel()
                        alloc = w.get_allocation()
                        ret = w.translate_coordinates(toplevel, 0, 0)
                        if ret is None:
                            continue
                        wx, wy = ret
                        if wx <= event.x <= wx + alloc.width and wy <= event.y <= wy + alloc.height:
                            if cls._scrolled_ref:
                                adj = cls._scrolled_ref.get_vadjustment()
                                if event.direction == Gdk.ScrollDirection.SMOOTH:
                                    _ok, _dx, dy = event.get_scroll_deltas()
                                    delta = dy * 50
                                elif event.direction == Gdk.ScrollDirection.DOWN:
                                    delta = 50
                                else:
                                    delta = -50
                                adj.set_value(adj.get_value() + delta)
                            return  # Ne PAS dispatcher — bloque le SpinButton/ComboBox
                Gtk.main_do_event(event)

            cls._gdk_filter_ref = _gdk_event_filter
            Gdk.Event.handler_set(_gdk_event_filter, None)
            cls._gdk_filter_installed = True


    def _update_anim(self, key, value):
        if 'animation' not in self.config:
            self.config['animation'] = {}
        self.config['animation'][key] = value
        self._sync_preview()

    def _update_color(self, key, rgba):
        if 'colors' not in self.config:
            self.config['colors'] = {}
        if isinstance(rgba, Gdk.RGBA):
            self.config['colors'][key] = [rgba.red, rgba.green, rgba.blue, rgba.alpha]
        else:
            self.config['colors'][key] = list(rgba)
        self._sync_preview()

    def _update_bg(self, key, value):
        if 'background' not in self.config:
            self.config['background'] = {'enabled': True, 'color': [0.2, 0.2, 0.25, 0.85], 'padding': 10}
        self.config['background'][key] = value
        self._sync_preview()

    def _update_audio(self, key, value):
        if 'audio' not in self.config:
            self.config['audio'] = {}
        self.config['audio'][key] = value
        if key == 'enabled':
            if value:
                self._start_audio_capture()
            else:
                self._stop_audio_capture()

    def _start_audio_capture(self):
        """Start audio capture from microphone"""
        if not AUDIO_AVAILABLE or self._audio_running:
            return
        self.preview.audio_enabled = True
        self._audio_running = True
        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._audio_thread.start()

    def _stop_audio_capture(self):
        """Stop audio capture"""
        self._audio_running = False
        if self._audio_thread:
            self._audio_thread.join(timeout=1.0)
            self._audio_thread = None
        self.preview.audio_enabled = False
        self.preview.audio_level = 0.0

    def _audio_loop(self):
        """Audio capture loop (separate thread), rereads config each frame"""
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        try:
            p = pyaudio.PyAudio()
            device_index = self.config.get('audio', {}).get('device_index', None)
            stream = p.open(
                format=FORMAT, channels=CHANNELS, rate=RATE,
                input=True, input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            while self._audio_running:
                try:
                    audio_config = self.config.get('audio', {})
                    sensitivity = audio_config.get('sensitivity', 1.5)
                    smoothing = audio_config.get('smoothing', 0.3)
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    samples = struct.unpack(f'{CHUNK}h', data)
                    rms = math.sqrt(sum(s * s for s in samples) / CHUNK)
                    level = min(1.0, (rms / 32767.0) * sensitivity * 10)
                    self.preview.audio_level = (
                        self.preview.audio_level * (1 - smoothing) + level * smoothing
                    )
                except Exception:
                    pass

            stream.stop_stream()
            stream.close()
            p.terminate()

        except Exception as e:
            print(_("Audio capture error (editor): {error}").format(error=e))
            self.preview.audio_enabled = False
            self._audio_running = False

    def _on_gradient_changed(self, colors):
        if 'colors' not in self.config:
            self.config['colors'] = {}
        self.config['colors']['gradient'] = colors
        self._sync_preview()

    def _on_palette_clicked(self, button, palette_name):
        palette = COLOR_PALETTES[palette_name]
        self.config['colors']['primary'] = list(palette['primary'])
        self.config['colors']['secondary'] = list(palette['secondary'])
        self.config['colors']['gradient'] = [list(c) for c in palette['gradient']]
        self._set_color_button(self.primary_btn, palette['primary'])
        self._set_color_button(self.secondary_btn, palette['secondary'])
        self.gradient_editor.set_colors(palette['gradient'])
        self._sync_preview()

    def _on_type_changed(self, combo):
        anim_type = combo.get_active_text()
        self.config['animation_type'] = anim_type
        # Si on passe en circulaire, forcer width=height depuis le rayon
        if anim_type in CIRCULAR_TYPES:
            radius = int(self.radius_spin.get_value())
            self.config['width'] = radius * 2
            self.config['height'] = radius * 2
        self._update_param_visibility(anim_type)
        self._sync_preview()

    def _on_position_changed(self, combo):
        position = combo.get_active_text()
        self._update_config('position', position)
        self._apply_overlay_position()
        # Show/hide X/Y sliders
        is_manual = (position == 'manual')
        for w in self._conditional_widgets.get('_manual_pos', []):
            w.set_no_show_all(not is_manual)
            w.set_visible(is_manual)
        if self.on_position_changed_cb:
            self.on_position_changed_cb()

    def _on_manual_scale_changed(self, scale):
        """Sync SpinButtons from sliders"""
        if self._manual_pos_updating:
            return
        self._manual_pos_updating = True
        self.pos_x_spin.set_value(self.pos_x_scale.get_value())
        self.pos_y_spin.set_value(self.pos_y_scale.get_value())
        self._apply_manual_pos()
        self._manual_pos_updating = False

    def _on_manual_spin_changed(self, spin):
        """Sync sliders from SpinButtons"""
        if self._manual_pos_updating:
            return
        self._manual_pos_updating = True
        self.pos_x_scale.set_value(self.pos_x_spin.get_value())
        self.pos_y_scale.set_value(self.pos_y_spin.get_value())
        self._apply_manual_pos()
        self._manual_pos_updating = False

    def _apply_manual_pos(self):
        """Update layer-shell margins from X/Y controls"""
        if 'layer' not in self.config:
            self.config['layer'] = {'margin': {}}
        if 'margin' not in self.config['layer']:
            self.config['layer']['margin'] = {}
        self.config['layer']['margin']['left'] = int(self.pos_x_spin.get_value())
        self.config['layer']['margin']['top'] = int(self.pos_y_spin.get_value())
        self._clamp_manual_pos()
        self._sync_preview()

    def _clamp_manual_pos(self):
        """Clamp manual position so the overlay stays on screen"""
        if not self.overlay_window or self.config.get('position') != 'manual':
            return
        screen_w = self.overlay_window.get_allocated_width()
        screen_h = self.overlay_window.get_allocated_height()
        anim_w = self.config.get('width', 800)
        anim_h = self.config.get('height', 60)
        # Wait for compositor to resize to fullscreen
        if screen_w <= anim_w or screen_h <= anim_h:
            return
        max_x = screen_w - anim_w
        max_y = screen_h - anim_h
        margins = self.config.get('layer', {}).get('margin', {})
        margins['left'] = min(margins.get('left', 0), max_x)
        margins['top'] = min(margins.get('top', 0), max_y)
        # Update controls without feedback loop
        self._manual_pos_updating = True
        self.pos_x_spin.set_range(0, max_x)
        self.pos_x_scale.set_range(0, max_x)
        self.pos_y_spin.set_range(0, max_y)
        self.pos_y_scale.set_range(0, max_y)
        self.pos_x_spin.set_value(margins['left'])
        self.pos_x_scale.set_value(margins['left'])
        self.pos_y_spin.set_value(margins['top'])
        self.pos_y_scale.set_value(margins['top'])
        self._manual_pos_updating = False

    def _on_radius_changed(self, spin):
        radius = int(spin.get_value())
        self.config['width'] = radius * 2
        self.config['height'] = radius * 2
        if self.config.get('position') == 'manual':
            self._clamp_manual_pos()
        self._sync_preview()

    def _set_color_button(self, btn, rgba_list):
        gdk_rgba = Gdk.RGBA()
        gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba_list[:4]
        btn.set_rgba(gdk_rgba)

    def _update_param_visibility(self, anim_type):
        for param_name, widgets in self._conditional_widgets.items():
            if param_name == '_manual_pos':
                continue  # Handled by _on_position_changed
            visible = anim_type in PARAM_VISIBILITY.get(param_name, set())
            for w in widgets:
                w.set_no_show_all(not visible)
                w.set_visible(visible)

    def _sync_preview(self):
        """Update preview config without resetting animation"""
        old_type = self.preview.config.get('animation_type')
        old_bar_count = self.preview.config.get('animation', {}).get('bar_count', 20)
        new_config = copy.deepcopy(self.config)
        normalize_config_colors(new_config)
        new_type = new_config.get('animation_type')
        new_bar_count = new_config.get('animation', {}).get('bar_count', 20)

        self.preview.config = new_config
        self.preview.name = new_config.get('_name', self.preview.name)

        # Reset only if type changes or bar count changes
        if new_type != old_type:
            self.preview.frame = 0
            self.preview.particles = []
        if new_bar_count != old_bar_count:
            self.preview.bars = [0.0] * new_bar_count
            self.preview.target_bars = [0.0] * new_bar_count

        # Update overlay (size and position)
        self._update_overlay_geometry()

    # --- Overlay preview sur le bureau ---

    def _setup_overlay(self):
        """Create transparent overlay window for real-time preview"""
        self.overlay_window = Gtk.Window()
        GtkLayerShell.init_for_window(self.overlay_window)
        GtkLayerShell.set_namespace(self.overlay_window, "animation-speech-overlay")
        GtkLayerShell.set_layer(self.overlay_window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(
            self.overlay_window, GtkLayerShell.KeyboardMode.NONE)

        w = self.config.get('width', 800)
        h = self.config.get('height', 60)
        is_manual = (self.config.get('position') == 'manual')

        if not is_manual:
            self.overlay_window.set_default_size(w, h)

        # Click-through + pas de focus
        self.overlay_window.input_shape_combine_region(cairo.Region())
        self.overlay_window.set_accept_focus(False)

        # Transparence
        screen = self.overlay_window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.overlay_window.set_visual(visual)
        self.overlay_window.set_app_paintable(True)
        self.overlay_window.set_decorated(False)

        # Zone de dessin
        self.overlay_da = Gtk.DrawingArea()
        if not is_manual:
            self.overlay_da.set_size_request(w, h)
        self.overlay_da.connect('draw', self._on_draw_overlay)
        self.overlay_da.connect('size-allocate', self._on_overlay_size_allocate)
        self.overlay_window.add(self.overlay_da)

        # Position layer-shell
        self._apply_overlay_position()
        self.overlay_window.show_all()

    def _apply_overlay_position(self):
        """Apply position and layer-shell margins on the overlay"""
        if not self.overlay_window:
            return
        position = self.config.get('position', 'bottom')

        # Reset toutes les ancres
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT,
                     GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self.overlay_window, edge, False)

        if position == 'bottom':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.BOTTOM, True)
        elif position == 'top':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.TOP, True)
        elif position == 'left':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'right':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.RIGHT, True)
        elif position == 'center':
            pass
        elif position == 'manual':
            # Fullscreen surface, position via Cairo translate in _on_draw_overlay
            for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                         GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                GtkLayerShell.set_anchor(self.overlay_window, edge, True)
        elif position == 'top-left':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'top-right':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.RIGHT, True)
        elif position == 'bottom-left':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'bottom-right':
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self.overlay_window, GtkLayerShell.Edge.RIGHT, True)

        # Marges
        margins = self.config.get('layer', {}).get('margin', {})
        if position == 'manual':
            # Fullscreen mode: all margins zero (position via Cairo translate)
            for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                         GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                GtkLayerShell.set_margin(self.overlay_window, edge, 0)
        else:
            margin_bottom = margins.get('bottom', 0)
            if position in ('bottom', 'bottom-left', 'bottom-right'):
                margin_bottom = max(margin_bottom, 80)
            GtkLayerShell.set_margin(self.overlay_window,
                                     GtkLayerShell.Edge.TOP, max(margins.get('top', 0), 10))
            GtkLayerShell.set_margin(self.overlay_window,
                                     GtkLayerShell.Edge.BOTTOM, margin_bottom)
            GtkLayerShell.set_margin(self.overlay_window,
                                     GtkLayerShell.Edge.LEFT, max(margins.get('left', 0), 10))
            GtkLayerShell.set_margin(self.overlay_window,
                                     GtkLayerShell.Edge.RIGHT, max(margins.get('right', 0), 10))

        GtkLayerShell.set_exclusive_zone(self.overlay_window, 0)

    def _update_overlay_geometry(self):
        """Update overlay size (without touching anchors/margins)"""
        if not self.overlay_window:
            return
        is_manual = (self.config.get('position') == 'manual')
        if is_manual:
            self.overlay_da.set_size_request(-1, -1)
        else:
            w = self.config.get('width', 800)
            h = self.config.get('height', 60)
            self.overlay_window.resize(w, h)
            self.overlay_da.set_size_request(w, h)
        self.overlay_da.queue_draw()

    def _on_draw_overlay(self, widget, cr):
        """Draw the preview in the overlay at full size"""
        alloc_w = widget.get_allocated_width()
        alloc_h = widget.get_allocated_height()
        # Transparent background (toute la surface)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if self.config.get('position') == 'manual':
            margins = self.config.get('layer', {}).get('margin', {})
            anim_w = self.config.get('width', 800)
            anim_h = self.config.get('height', 60)
            off_x = min(margins.get('left', 0), max(0, alloc_w - anim_w))
            off_y = min(margins.get('top', 0), max(0, alloc_h - anim_h))
            cr.save()
            cr.translate(off_x, off_y)
            cr.rectangle(0, 0, anim_w, anim_h)
            cr.clip()
            self.preview._draw_background_cartouche(cr, anim_w, anim_h)
            self.preview.dispatch_draw(cr, anim_w, anim_h)
            cr.restore()
        else:
            cr.save()
            self.preview._draw_background_cartouche(cr, alloc_w, alloc_h)
            self.preview.dispatch_draw(cr, alloc_w, alloc_h)
            cr.restore()

    def _on_overlay_size_allocate(self, widget, allocation):
        """Clamp manual position when overlay changes size."""
        if self.config.get('position') == 'manual':
            self._clamp_manual_pos()

    def destroy_overlay(self):
        """Destroy the overlay window"""
        self._stop_audio_capture()
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None

    def update_tick(self):
        self.preview.update()
        if self.overlay_window:
            self.overlay_da.queue_draw()

    # --- Save ---

    def _on_save_current(self, button):
        if not self.config_path:
            return
        self._write_yaml(self.config_path)
        self.header_label.set_text(_("Saved: {name}").format(name=os.path.basename(self.config_path)))
        self.header_label.get_style_context().add_class('selected-label')
        if self.on_save_cb:
            self.on_save_cb(self.config_path, self.config)

    def _on_save(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Save configuration"),
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT,
        )
        dialog.set_do_overwrite_confirmation(True)

        if self.config_path and os.path.exists(os.path.dirname(self.config_path)):
            dialog.set_current_folder(os.path.dirname(os.path.abspath(self.config_path)))
        else:
            config_dir = os.path.expanduser('~/.config/animation-speech')
            os.makedirs(config_dir, exist_ok=True)
            dialog.set_current_folder(config_dir)

        anim_type = self.config.get('animation_type', 'wave')
        dialog.set_current_name(f"{anim_type}-custom.yaml")

        filt = Gtk.FileFilter()
        filt.set_name(_("YAML files"))
        filt.add_pattern("*.yaml")
        filt.add_pattern("*.yml")
        dialog.add_filter(filt)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            if not path.endswith(('.yaml', '.yml')):
                path += '.yaml'
            self._write_yaml(path)
            self.config_path = path
            self.header_label.set_text(_("Saved: {path}").format(path=path))
            self.header_label.get_style_context().add_class('selected-label')
            self.path_entry.set_text(os.path.abspath(path))
            self.delete_btn.set_sensitive(True)
            self.save_current_btn.set_sensitive(True)
            self.default_btn.set_sensitive(True)
            if self.on_save_cb:
                self.on_save_cb(path, self.config)

        dialog.destroy()

    def _on_delete(self, button):
        if not self.config_path or not os.path.exists(self.config_path):
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Delete this file?"),
        )
        dialog.format_secondary_text(os.path.abspath(self.config_path))
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            deleted_path = self.config_path
            os.remove(deleted_path)
            self.header_label.set_text(_("Deleted: {name}").format(name=os.path.basename(deleted_path)))
            self.path_entry.set_text('')
            self.delete_btn.set_sensitive(False)
            self.save_current_btn.set_sensitive(False)
            self.default_btn.set_sensitive(False)
            self.config_path = None
            if self.on_delete_cb:
                self.on_delete_cb(deleted_path)

    def _on_set_default(self, button):
        """Set current config as default via symlink"""
        if not self.config_path or not os.path.exists(self.config_path):
            return
        config_dir = os.path.expanduser('~/.config/animation-speech')
        os.makedirs(config_dir, exist_ok=True)
        default_path = os.path.join(config_dir, 'config.yaml')
        source = os.path.abspath(self.config_path)

        # Already the default
        if os.path.islink(default_path) and os.readlink(default_path) == source:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(), modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("This config is already the default."),
            )
            dialog.run()
            dialog.destroy()
            return

        # Confirmation
        msg = _("Set as default config?\n\n{name}").format(name=os.path.basename(source))
        if os.path.exists(default_path):
            if os.path.islink(default_path):
                old_target = os.readlink(default_path)
                msg += _("\n\nReplaces: {name}").format(name=os.path.basename(old_target))
            else:
                msg += _("\n\nWill overwrite existing config.yaml")
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(), modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=msg,
        )
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return

        # Create symlink
        if os.path.exists(default_path) or os.path.islink(default_path):
            os.remove(default_path)
        os.symlink(source, default_path)
        self.default_btn.set_label(_("Default") + " \u2713")
        GLib.timeout_add(2000, lambda: self.default_btn.set_label(_("Default")) or False)

    def _write_yaml(self, path):
        out = {}
        out['animation_type'] = self.config.get('animation_type', 'wave')
        out['position'] = self.config.get('position', 'bottom')
        out['width'] = self.config.get('width', 800)
        out['height'] = self.config.get('height', 60)

        colors = self.config.get('colors', {})
        out['colors'] = {}
        for key in ('background', 'primary', 'secondary'):
            if key in colors:
                out['colors'][key] = self._rgba_to_hex(colors[key])
        if 'gradient' in colors:
            out['colors']['gradient'] = [self._rgba_to_hex(c) for c in colors['gradient']]

        bg = self.config.get('background', {})
        out['background'] = {
            'enabled': bg.get('enabled', False),
            'color': self._rgba_to_hex(bg.get('color', [0.2, 0.2, 0.25, 0.85])),
            'padding': bg.get('padding', 10),
            'border_width': bg.get('border_width', 0),
            'border_color': self._rgba_to_hex(bg.get('border_color', [1.0, 1.0, 1.0, 0.5])),
        }

        out['animation'] = {}
        anim = self.config.get('animation', {})
        for key in ('fps', 'smoothing', 'intensity', 'wave_frequency',
                     'bar_count', 'bar_width', 'bars_rotation', 'bar_spacing',
                     'circle_count', 'circle_direction', 'circle_spacing', 'circle_speed',
                     'wave_count', 'fill_wave', 'fill_opacity'):
            if key in anim:
                out['animation'][key] = anim[key]

        audio = self.config.get('audio', {})
        out['audio'] = {
            'enabled': audio.get('enabled', False),
            'sensitivity': audio.get('sensitivity', 1.5),
            'smoothing': audio.get('smoothing', 0.3),
        }

        layer = self.config.get('layer', {})
        margins = layer.get('margin', {})
        out['layer'] = {
            'layer': layer.get('layer', 'overlay'),
            'exclusive_zone': layer.get('exclusive_zone', 0),
            'margin': {
                'top': margins.get('top', 0),
                'bottom': margins.get('bottom', 0),
                'left': margins.get('left', 0),
                'right': margins.get('right', 0),
            },
        }

        with open(path, 'w') as f:
            f.write(f"# Configuration animation-speech\n")
            f.write("# " + _("Generated by the visual chooser") + "\n\n")
            yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _rgba_to_hex(rgba_list):
        r, g, b = int(rgba_list[0]*255), int(rgba_list[1]*255), int(rgba_list[2]*255)
        a = rgba_list[3] if len(rgba_list) > 3 else 1.0
        if abs(a - 1.0) < 0.01:
            return f"#{r:02x}{g:02x}{b:02x}"
        return f"#{r:02x}{g:02x}{b:02x}{int(a*255):02x}"

    def load_from_config(self, config_dict, config_path=None):
        self._stop_audio_capture()
        self.config = copy.deepcopy(config_dict)
        self.config_path = config_path
        if 'layer' not in self.config:
            self.config['layer'] = {
                'layer': 'overlay', 'exclusive_zone': 0,
                'margin': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
            }
        # Force square dimensions for circular types
        if self.config.get('animation_type') in CIRCULAR_TYPES:
            side = min(self.config.get('width', 200), self.config.get('height', 200))
            self.config['width'] = side
            self.config['height'] = side
        for child in self.get_children():
            self.remove(child)
        self._conditional_widgets = {}
        self.preview.update_config(copy.deepcopy(self.config))
        self._build_ui()
        self._install_scroll_blockers(self)
        self.show_all()
        self._update_overlay_geometry()
        self._apply_overlay_position()
        # Restart audio capture if enabled in new config
        if self.config.get('audio', {}).get('enabled', False):
            self._start_audio_capture()
