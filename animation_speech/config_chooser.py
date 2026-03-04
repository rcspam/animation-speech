"""ConfigChooser — visual configuration selector with animated previews."""

import os
import copy
import math
import struct
import subprocess
import threading
import tempfile
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import yaml

from .utils import _, normalize_config_colors
from .constants import VALID_POSITIONS, COLOR_PALETTES
from .config_editor import ConfigEditor
from .animation import AnimationPreview, AUDIO_AVAILABLE

# Conditional import for audio
try:
    import pyaudio
except ImportError:
    pass


class ConfigChooser:
    """Visual configuration chooser with animated previews"""

    CELL_WIDTH = 180
    CELL_HEIGHT = 80
    LABEL_HEIGHT = 20

    def __init__(self, filter_name=None):
        self.previews = []
        self.selected_path = None
        self.selected_cell = None
        self.selected_index = -1
        self.filter_name = filter_name
        self._audio_running = False
        self._audio_thread = None
        self._audio_level = 0.0
        self.all_configs = self._collect_configs(filter_name)
        self._build_previews()
        self._setup_window()

    def _collect_configs(self, filter_name):
        """Collect all available configs (audio and non-audio)"""
        from .main import list_available_configs
        configs = list_available_configs()
        result = []
        for name, (location, path) in sorted(configs.items()):
            if name in ('config', 'README'):
                continue
            if filter_name and filter_name.lower() not in name.lower():
                continue
            result.append((name, path))
        return result

    def _build_previews(self):
        """Build previews"""
        self.previews = []
        for name, path in self.all_configs:
            try:
                preview = AnimationPreview(path)
                # Activer l'audio sur les previews qui ont audio.enabled
                if preview.config.get('audio', {}).get('enabled', False):
                    preview.audio_enabled = True
                self.previews.append(preview)
            except Exception:
                pass

    def _setup_window(self):
        self.window = Gtk.Window(title=_("Configuration editor \u2014 animation-speech"))
        self.window.set_default_size(1200, 700)
        self.window.connect('destroy', self._on_window_destroy)
        self.window.connect('key-press-event', self._on_key_press)

        # Dark theme + styles
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            window { background-color: #1e1e2e; }
            label { color: #cdd6f4; }
            .title-label { color: #cdd6f4; font-weight: bold; }
            .section-label { color: #89b4fa; font-weight: bold; }
            .selected-label { color: #a6e3a1; font-weight: bold; }
            checkbutton label { color: #cdd6f4; }
            frame { border-color: #45475a; }
            frame > label { color: #89b4fa; }
            .cell-selected { border: 2px solid rgba(137, 180, 250, 0.6); border-radius: 8px; background-color: rgba(137, 180, 250, 0.08); }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Split panel
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_position(420)

        # --- Left panel: grid ---
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.set_margin_top(12)
        left_box.set_margin_bottom(12)
        left_box.set_margin_start(12)
        left_box.set_margin_end(6)

        title = Gtk.Label(label=_("Configurations"))
        title.get_style_context().add_class('title-label')
        left_box.pack_start(title, False, False, 0)

        # Info + audio checkbox
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.info_label = Gtk.Label(label=_("{count} configs").format(count=len(self.previews)))
        info_box.pack_start(self.info_label, False, False, 0)

        self.audio_check = Gtk.CheckButton(label=_("Audio"))
        self.audio_check.set_sensitive(AUDIO_AVAILABLE)
        self.audio_check.set_tooltip_text(_("Enable microphone for audio previews"))
        self.audio_check.connect('toggled', self._on_audio_toggled)
        info_box.pack_end(self.audio_check, False, False, 0)

        # Muted mic warning
        self.mute_warning = Gtk.Label()
        self.mute_warning.set_markup('<span foreground="#f38ba8" weight="bold">{text}</span>'.format(
            text=GLib.markup_escape_text(_("Mic muted!"))))
        self.mute_warning.set_no_show_all(True)
        info_box.pack_end(self.mute_warning, False, False, 0)

        left_box.pack_start(info_box, False, False, 0)

        # Scale control (GTK/KDE Wayland compatibility)
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        scale_label = Gtk.Label(label=_("Scale:"))
        scale_box.pack_start(scale_label, False, False, 0)
        self.ui_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.75, 2.5, 0.05)
        self.ui_scale.set_value(1.0)
        self.ui_scale.set_draw_value(False)
        self.ui_scale.set_size_request(120, -1)
        # Magnetic marks
        for v in (0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
            self.ui_scale.add_mark(v, Gtk.PositionType.BOTTOM, None)
        self._scale_updating = False
        self.ui_scale.connect('value-changed', self._on_ui_scale_changed)
        scale_box.pack_start(self.ui_scale, True, True, 0)
        self.ui_scale_spin = Gtk.SpinButton.new_with_range(0.75, 2.5, 0.05)
        self.ui_scale_spin.set_value(1.0)
        self.ui_scale_spin.set_digits(2)
        self.ui_scale_spin.connect('value-changed', self._on_ui_scale_spin_changed)
        scale_box.pack_start(self.ui_scale_spin, False, False, 0)
        left_box.pack_start(scale_box, False, False, 0)

        # Grille scrollable
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_column_spacing(6)
        self.flowbox.set_row_spacing(6)

        for preview in self.previews:
            cell = self._create_cell(preview)
            self.flowbox.add(cell)

        scrolled.add(self.flowbox)
        left_box.pack_start(scrolled, True, True, 0)

        # Bouton Nouveau
        new_btn = Gtk.Button(label=_("+ New"))
        new_btn.connect('clicked', self._on_new_config)
        left_box.pack_start(new_btn, False, False, 0)

        self.paned.pack1(left_box, resize=False, shrink=False)

        # --- Right panel: editor (empty initially) ---
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box.set_margin_top(12)
        self.right_box.set_margin_bottom(12)
        self.right_box.set_margin_start(6)
        self.right_box.set_margin_end(12)

        # Placeholder
        self.placeholder = Gtk.Label(label=_("Click a configuration\n   to edit it"))
        self.placeholder.set_halign(Gtk.Align.CENTER)
        self.placeholder.set_valign(Gtk.Align.CENTER)
        self.right_box.pack_start(self.placeholder, True, True, 0)

        self.editor = None
        self.paned.pack2(self.right_box, resize=True, shrink=False)

        self.window.add(self.paned)

        # Timer animation 30fps
        GLib.timeout_add(33, self._update_all)

        self.window.show_all()

        # Enable audio after show_all so the warning is visible
        if AUDIO_AVAILABLE:
            self.audio_check.set_active(True)

    def _create_cell(self, preview):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(4)
        box.set_margin_end(4)

        # Zone de dessin
        drawing_area = Gtk.DrawingArea()
        drawing_area.set_size_request(self.CELL_WIDTH, self.CELL_HEIGHT)
        drawing_area.connect('draw', lambda w, cr, p=preview: self._on_draw_preview(w, cr, p))
        box.pack_start(drawing_area, True, True, 0)

        # Label avec le nom
        label = Gtk.Label(label=preview.name)
        label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        box.pack_start(label, False, False, 2)

        # Rendre cliquable via EventBox
        event_box = Gtk.EventBox()
        event_box.add(box)
        event_box.connect('button-press-event',
                          lambda w, e, p=preview, eb=event_box: self._on_click(p, eb))
        # Curseur main au survol
        event_box.connect('realize',
                          lambda w: w.get_window().set_cursor(
                              Gdk.Cursor.new_from_name(w.get_display(), 'pointer')))

        return event_box

    def _start_audio(self):
        """Start audio capture for previews"""
        if self._audio_running:
            return
        self._audio_running = True
        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._audio_thread.start()

    def _stop_audio(self):
        """Stop audio capture"""
        self._audio_running = False
        if self._audio_thread:
            self._audio_thread.join(timeout=1.0)
            self._audio_thread = None
        # Disable audio on all previews
        self._audio_level = 0.0
        for preview in self.previews:
            if preview.audio_enabled:
                preview.audio_level = 0.0

    def _on_audio_toggled(self, button):
        """Toggle audio capture for previews"""
        if button.get_active():
            self._check_mute_state()
            self._start_audio()
            self._start_mute_monitor()
        else:
            self._stop_audio()
            self._stop_mute_monitor()
            self.mute_warning.hide()

    def _check_mute_state(self):
        """Check mute state and show/hide warning"""
        if self._is_mic_muted():
            self.mute_warning.show()
        else:
            self.mute_warning.hide()

    def _is_mic_muted(self):
        """Check if default mic is muted (pactl then amixer fallback)"""
        env = os.environ.copy()
        env['LANG'] = 'C'
        # PulseAudio / PipeWire
        try:
            result = subprocess.run(
                ['pactl', 'get-source-mute', '@DEFAULT_SOURCE@'],
                capture_output=True, text=True, timeout=1, env=env)
            if result.returncode == 0:
                return 'yes' in result.stdout.lower()
        except Exception:
            pass
        # Fallback ALSA pur
        try:
            result = subprocess.run(
                ['amixer', 'get', 'Capture'],
                capture_output=True, text=True, timeout=1, env=env)
            if result.returncode == 0:
                return '[off]' in result.stdout.lower()
        except Exception:
            pass
        return False

    def _start_mute_monitor(self):
        """Start pactl subscribe to detect mute changes instantly"""
        self._pactl_proc = None
        self._mute_poll_timer = None
        try:
            env = os.environ.copy()
            env['LANG'] = 'C'
            self._pactl_proc = subprocess.Popen(
                ['pactl', 'subscribe'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, env=env)
            self._pactl_thread = threading.Thread(target=self._mute_monitor_loop, daemon=True)
            self._pactl_thread.start()
        except Exception:
            # Fallback : polling toutes les 2s (ALSA pur sans pactl)
            self._mute_poll_timer = GLib.timeout_add(2000, self._mute_poll_tick)

    def _mute_poll_tick(self):
        """Polling fallback for systems without pactl subscribe"""
        if not self._audio_running:
            return False
        self._check_mute_state()
        return True

    def _stop_mute_monitor(self):
        """Stop pactl subscribe monitor or polling"""
        if hasattr(self, '_pactl_proc') and self._pactl_proc:
            self._pactl_proc.terminate()
            self._pactl_proc = None
        if hasattr(self, '_mute_poll_timer') and self._mute_poll_timer:
            GLib.source_remove(self._mute_poll_timer)
            self._mute_poll_timer = None

    def _mute_monitor_loop(self):
        """Read pactl events and recheck mute on each source change"""
        try:
            for line in self._pactl_proc.stdout:
                if not self._audio_running:
                    break
                if 'source' in line.lower():
                    GLib.idle_add(self._check_mute_state)
        except Exception:
            pass

    def _audio_loop(self):
        """Audio capture loop for previews."""
        CHUNK = 1024
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16, channels=1, rate=44100,
                input=True, frames_per_buffer=CHUNK
            )
            while self._audio_running:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    samples = struct.unpack(f'{CHUNK}h', data)
                    rms = math.sqrt(sum(s * s for s in samples) / CHUNK)
                    level = min(1.0, (rms / 32767.0) * 1.5 * 10)
                    self._audio_level = self._audio_level * 0.7 + level * 0.3
                except Exception:
                    pass
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            self._audio_running = False

    def _on_window_destroy(self, *args):
        self._stop_audio()
        self._stop_mute_monitor()
        if self.editor:
            self.editor.destroy_overlay()
        Gtk.main_quit()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.window.destroy()
            return True
        # Keyboard navigation in the list (only if focus is in the left panel)
        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right):
            focused = self.window.get_focus()
            if focused and self.editor and focused.is_ancestor(self.editor):
                return False
            if not self.previews:
                return False
            cols = self.flowbox.get_max_children_per_line()
            idx = self.selected_index
            if event.keyval == Gdk.KEY_Up:
                idx = max(0, idx - 1)
            elif event.keyval == Gdk.KEY_Down:
                idx = min(len(self.previews) - 1, idx + 1)
            elif event.keyval == Gdk.KEY_Left:
                idx = max(0, idx - cols)
            elif event.keyval == Gdk.KEY_Right:
                idx = min(len(self.previews) - 1, idx + cols)
            if idx != self.selected_index:
                self._select_by_index(idx)
            return True
        return False

    def _select_by_index(self, idx):
        """Select a preview by its index and scroll to it."""
        if idx < 0 or idx >= len(self.previews):
            return
        preview = self.previews[idx]
        # Find the corresponding cell (event_box) in the flowbox
        children = self.flowbox.get_children()
        if idx < len(children):
            flowbox_child = children[idx]
            cell = flowbox_child.get_child()  # the event_box
            self._on_click(preview, cell)
            # Scroll to make the cell visible
            alloc = flowbox_child.get_allocation()
            adj = self.flowbox.get_parent().get_vadjustment()
            if adj:
                visible_top = adj.get_value()
                visible_bottom = visible_top + adj.get_page_size()
                if alloc.y < visible_top:
                    adj.set_value(alloc.y)
                elif alloc.y + alloc.height > visible_bottom:
                    adj.set_value(alloc.y + alloc.height - adj.get_page_size())

    def _on_ui_scale_changed(self, scale):
        """Change GTK DPI to scale the entire interface."""
        if self._scale_updating:
            return
        self._scale_updating = True
        value = scale.get_value()
        # Snap: round to nearest notch if close
        snaps = (0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5)
        for s in snaps:
            if abs(value - s) < 0.03:
                value = s
                scale.set_value(value)
                break
        self.ui_scale_spin.set_value(value)
        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-xft-dpi', int(96 * value * 1024))
        self._scale_updating = False

    def _on_ui_scale_spin_changed(self, spin):
        """Synchronize the scale slider with the SpinButton."""
        if self._scale_updating:
            return
        self._scale_updating = True
        value = spin.get_value()
        self.ui_scale.set_value(value)
        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-xft-dpi', int(96 * value * 1024))
        self._scale_updating = False

    def _on_draw_preview(self, widget, cr, preview):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        try:
            preview.draw(cr, width, height)
        except Exception:
            pass

    def _update_all(self):
        # Distribute audio level to audio-enabled previews
        level = self._audio_level
        for preview in self.previews:
            if preview.audio_enabled:
                preview.audio_level = level
            preview.update()
        self.flowbox.queue_draw()
        if self.editor is not None:
            self.editor.update_tick()
        return True

    def _on_click(self, preview, cell=None):
        """Load the selected config into the editor."""
        # Mark the selected cell
        if self.selected_cell:
            self.selected_cell.get_style_context().remove_class('cell-selected')
        if cell:
            cell.get_style_context().add_class('cell-selected')
            self.selected_cell = cell
        # Track index for keyboard navigation
        try:
            self.selected_index = self.previews.index(preview)
        except ValueError:
            pass

        with open(preview.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        normalize_config_colors(config_dict)
        config_dict['_name'] = preview.name

        if self.editor is None:
            self.right_box.remove(self.placeholder)
            self.editor = ConfigEditor(
                config_dict, preview.config_path,
                on_position_changed_cb=self._move_chooser_avoid_overlay,
                on_delete_cb=self._on_config_deleted,
                on_save_cb=self._on_config_saved)
            self.right_box.pack_start(self.editor, True, True, 0)
            self.right_box.show_all()
        else:
            self.editor.load_from_config(config_dict, preview.config_path)
        GLib.timeout_add(300, self._move_chooser_avoid_overlay)

    def _on_new_config(self, button):
        """Create a blank config in the editor."""
        default_config = {
            '_name': _("New"),
            'animation_type': 'wave',
            'position': 'top',
            'width': 800,
            'height': 60,
            'colors': {
                'background': [0.0, 0.0, 0.0, 0.0],
                'primary': [0.93, 0.53, 0.59, 0.9],
                'secondary': [0.55, 0.84, 0.79, 0.9],
                'gradient': [list(c) for c in COLOR_PALETTES['Catppuccin']['gradient']],
            },
            'background': {
                'enabled': True,
                'color': [0.2, 0.2, 0.25, 0.85],
                'padding': 10,
            },
            'animation': {
                'fps': 60,
                'smoothing': 0.3,
                'intensity': 1.0,
                'wave_frequency': 3.0,
                'wave_count': 1,
                'fill_wave': True,
                'fill_opacity': 0.3,
                'bar_count': 20,
                'bar_width': 15,
                'bar_spacing': 5,
            },
            'audio': {'enabled': False, 'sensitivity': 1.5, 'smoothing': 0.3},
            'layer': {
                'layer': 'overlay', 'exclusive_zone': 0,
                'margin': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
            },
        }

        if self.editor is None:
            self.right_box.remove(self.placeholder)
            self.editor = ConfigEditor(
                default_config,
                on_position_changed_cb=self._move_chooser_avoid_overlay,
                on_delete_cb=self._on_config_deleted,
                on_save_cb=self._on_config_saved)
            self.right_box.pack_start(self.editor, True, True, 0)
            self.right_box.show_all()
        else:
            self.editor.load_from_config(default_config)
        GLib.timeout_add(300, self._move_chooser_avoid_overlay)

    def _on_config_deleted(self, deleted_path):
        """Update the list after a config is deleted."""
        self.previews = [p for p in self.previews if
                         os.path.abspath(p.config_path) != os.path.abspath(deleted_path)]
        self._rebuild_flowbox()

    def _on_config_saved(self, saved_path, config):
        """Update the preview in the list after saving."""
        abs_path = os.path.abspath(saved_path)
        found = False
        for preview in self.previews:
            if os.path.abspath(preview.config_path) == abs_path:
                preview.update_config(copy.deepcopy(config))
                preview.name = os.path.basename(saved_path).rsplit('.', 1)[0]
                preview.audio_enabled = config.get('audio', {}).get('enabled', False)
                found = True
                break
        if not found:
            # New file (Save As) -> add a preview
            new_preview = AnimationPreview(saved_path)
            new_preview.audio_enabled = config.get('audio', {}).get('enabled', False)
            self.previews.append(new_preview)
        self._rebuild_flowbox()
        # Re-select the saved cell
        for child in self.flowbox.get_children():
            event_box = child.get_child()
            if event_box and hasattr(event_box, 'get_children'):
                box = event_box.get_children()[0] if event_box.get_children() else None
                if box and hasattr(box, 'get_children'):
                    children = box.get_children()
                    if len(children) >= 2:
                        label = children[1]
                        name = os.path.basename(saved_path).rsplit('.', 1)[0]
                        if label.get_text() == name:
                            event_box.get_style_context().add_class('cell-selected')
                            self.selected_cell = event_box
                            break

    def _rebuild_flowbox(self):
        """Rebuild the flowbox with current previews."""
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)
        for preview in self.previews:
            cell = self._create_cell(preview)
            self.flowbox.add(cell)
        self.flowbox.show_all()
        self.info_label.set_text(_("{count} configs").format(count=len(self.previews)))

    # --- Window movement to avoid overlay ---

    def _detect_compositor(self):
        """Detect the Wayland compositor (kde or gnome)."""
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        if 'kde' in desktop or 'plasma' in desktop:
            return 'kde'
        elif 'gnome' in desktop:
            return 'gnome'
        return None

    def _compute_chooser_position(self, overlay_position, screen_w, screen_h, win_w, win_h):
        """Compute x, y to place the chooser on the opposite side of the overlay."""
        margin = 50
        if overlay_position == 'bottom':
            return (screen_w - win_w) // 2, margin
        elif overlay_position == 'top':
            return (screen_w - win_w) // 2, screen_h - win_h - margin
        elif overlay_position in ('left', 'right'):
            return (screen_w - win_w) // 2, (screen_h - win_h) // 2
        elif overlay_position == 'center':
            return (screen_w - win_w) // 2, margin
        else:  # top-left, top-right, bottom-left, bottom-right, manual
            return (screen_w - win_w) // 2, (screen_h - win_h) // 2

    def _move_window_kwin(self, x, y):
        """Move the window via KWin scripting D-Bus."""
        title = self.window.get_title()
        if not title:
            return
        script_content = f'''
var windows = workspace.windowList();
for (var i = 0; i < windows.length; i++) {{
    var w = windows[i];
    if (w.caption.includes("{title}")) {{
        w.frameGeometry = {{x: {x}, y: {y}, width: w.width, height: w.height}};
        break;
    }}
}}
'''
        script_name = f'move-chooser-{int(time.time() * 1000)}'
        try:
            fd, script_path = tempfile.mkstemp(suffix='.js', prefix='kwin-move-')
            with os.fdopen(fd, 'w') as f:
                f.write(script_content)

            # Load the script via qdbus6
            result = subprocess.run(
                ['qdbus6', 'org.kde.KWin', '/Scripting', 'loadScript',
                 script_path, script_name],
                capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return

            script_id = result.stdout.strip()

            # Execute the script
            subprocess.run(
                ['qdbus6', 'org.kde.KWin', f'/Scripting/Script{script_id}', 'run'],
                capture_output=True, text=True, timeout=5)

            # Unload the script
            subprocess.run(
                ['qdbus6', 'org.kde.KWin', f'/Scripting/Script{script_id}',
                 'stop'],
                capture_output=True, text=True, timeout=5)
            subprocess.run(
                ['qdbus6', 'org.kde.KWin', '/Scripting', 'unloadScript',
                 script_name],
                capture_output=True, text=True, timeout=5)
        except Exception as e:
            print(_("KWin move failed: {error}").format(error=e))
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def _move_window_gnome(self, x, y):
        """Move the window via GNOME Shell D-Bus Eval."""
        title = self.window.get_title()
        if not title:
            return
        js = (
            'global.get_window_actors().forEach(function(actor) {'
            '  var mw = actor.meta_window;'
            f'  if (mw && mw.title && mw.title.includes("{title}")) {{'
            '    var r = mw.get_frame_rect();'
            f'    mw.move_resize_frame(false, {x}, {y}, r.width, r.height);'
            '  }'
            '});'
        )
        try:
            subprocess.run(
                ['gdbus', 'call', '--session',
                 '--dest', 'org.gnome.Shell',
                 '--object-path', '/org/gnome/Shell',
                 '--method', 'org.gnome.Shell.Eval', js],
                capture_output=True, text=True, timeout=5)
        except Exception as e:
            print(_("GNOME move failed: {error}").format(error=e))

    def _move_chooser_avoid_overlay(self):
        """Move the chooser window to avoid overlapping with the overlay."""
        compositor = self._detect_compositor()
        if not compositor:
            return False

        position = self.editor.config.get('position', 'top') if self.editor else 'top'
        display = self.window.get_display()
        monitor = display.get_monitor_at_window(self.window.get_window()) \
            if self.window.get_window() else display.get_primary_monitor() \
            or display.get_monitor(0)
        geom = monitor.get_geometry()
        screen_w, screen_h = geom.width, geom.height
        win_w, win_h = self.window.get_size()

        x, y = self._compute_chooser_position(position, screen_w, screen_h, win_w, win_h)

        if compositor == 'kde':
            self._move_window_kwin(x, y)
        elif compositor == 'gnome':
            self._move_window_gnome(x, y)
        return False

    def run(self):
        Gtk.main()
