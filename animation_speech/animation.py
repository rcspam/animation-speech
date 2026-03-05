"""SpeechAnimation (overlay) and AnimationPreview (chooser thumbnail)."""

import os
import math
import random
import signal
import struct
import subprocess
import threading
import traceback

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell, GLib, Gdk
import cairo
import yaml

from .draw_mixin import AnimationDrawMixin
from .utils import _, parse_color, normalize_config_colors
from .constants import VALID_ANIMATION_TYPES, VALID_POSITIONS

# Optional import for audio capture
try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class SpeechAnimation(AnimationDrawMixin):
    def __init__(self, config_path='config.yaml', cli_overrides=None):
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR', '/tmp')
        self.pid_file = os.path.join(runtime_dir, 'speech-animation.pid')
        self.window = None

        # Create PID file first
        self.create_pid_file()

        try:
            self.load_config(config_path)

            # Apply command-line overrides
            if cli_overrides:
                self.apply_cli_overrides(cli_overrides)

            # Command to execute on Escape (enables exclusive keyboard grab)
            self.on_escape_cmd = (cli_overrides or {}).get('on_escape_cmd')

            self.is_animating = False
            self.frame = 0
            self.bars = []
            self.particles = []
            self.circles = []
            self._spawn_acc = 0.0

            # Microphone audio level (0.0 to 1.0)
            self.audio_level = 0.0
            self.audio_enabled = False
            self.audio_thread = None
            self.audio_running = False

            # Initialize data based on animation type
            if self.config['animation_type'] == 'equalizer':
                bar_count = self.config['animation']['bar_count']
                self.bars = [0.0] * bar_count
                self.target_bars = [0.0] * bar_count
            elif self.config['animation_type'] == 'particles':
                self.particles = []

            self.setup_window()
            self.setup_signals()

            # Start audio capture if enabled
            if self.config.get('audio', {}).get('enabled', False):
                self.start_audio_capture()
        except Exception as e:
            # On error, clean up PID file
            self.cleanup_pid_file()
            raise

    def create_pid_file(self):
        """Create the PID file at startup"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            print(_("PID file created: {path}").format(path=self.pid_file))
        except Exception as e:
            print(_("Cannot create PID file: {error}").format(error=e))
            self.pid_file = None

    def cleanup_pid_file(self):
        """Remove the PID file"""
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except Exception:
                pass

    def start_audio_capture(self):
        """Start audio capture from microphone"""
        if not AUDIO_AVAILABLE:
            print(_("pyaudio not installed - audio capture disabled"))
            print(_("  Install with: sudo apt install -y python3-pyaudio || pip install pyaudio"))
            return

        self.audio_enabled = True
        self.audio_running = True
        self.audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_thread.start()
        print(_("Audio capture enabled"))

    def stop_audio_capture(self):
        """Stop audio capture"""
        self.audio_running = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1.0)
            self.audio_thread = None
        self.audio_enabled = False

    def _audio_loop(self):
        """Audio capture loop (in a separate thread)"""
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        audio_config = self.config.get('audio', {})
        sensitivity = audio_config.get('sensitivity', 1.5)
        smoothing = audio_config.get('smoothing', 0.3)

        try:
            p = pyaudio.PyAudio()

            device_index = audio_config.get('device_index', None)

            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            print(_("Microphone opened (sensitivity: {val})").format(val=sensitivity))

            while self.audio_running:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    samples = struct.unpack(f'{CHUNK}h', data)
                    rms = math.sqrt(sum(s * s for s in samples) / CHUNK)
                    level = min(1.0, (rms / 32767.0) * sensitivity * 10)
                    self.audio_level = self.audio_level * (1 - smoothing) + level * smoothing
                except Exception:
                    pass

            stream.stop_stream()
            stream.close()
            p.terminate()

        except Exception as e:
            print(_("Audio capture error: {error}").format(error=e))
            self.audio_enabled = False

    def load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        normalize_config_colors(self.config)

        # Validate animation type
        anim_type = self.config.get('animation_type', 'wave')
        if anim_type not in VALID_ANIMATION_TYPES:
            print(_("Unknown animation type: '{type}' (valid: {valid}). Using 'wave'.").format(
                type=anim_type, valid=', '.join(VALID_ANIMATION_TYPES)))
            self.config['animation_type'] = 'wave'

    def apply_cli_overrides(self, overrides):
        """Apply configuration overrides from command line"""
        if overrides.get('width') is not None:
            self.config['width'] = overrides['width']
        if overrides.get('height') is not None:
            self.config['height'] = overrides['height']
        if overrides.get('margin_top') is not None:
            self.config['layer']['margin']['top'] = overrides['margin_top']
        if overrides.get('margin_bottom') is not None:
            self.config['layer']['margin']['bottom'] = overrides['margin_bottom']
        if overrides.get('margin_left') is not None:
            self.config['layer']['margin']['left'] = overrides['margin_left']
        if overrides.get('margin_right') is not None:
            self.config['layer']['margin']['right'] = overrides['margin_right']
        if overrides.get('position'):
            self.config['position'] = overrides['position']
        if overrides.get('speed') is not None:
            self.config['animation']['circle_speed'] = overrides['speed']
        if overrides.get('count') is not None:
            self.config['animation']['wave_count'] = overrides['count']
            self.config['animation']['circle_count'] = overrides['count']
        if overrides.get('audio'):
            if 'audio' not in self.config:
                self.config['audio'] = {}
            self.config['audio']['enabled'] = True
        if overrides.get('audio_sensitivity') is not None:
            if 'audio' not in self.config:
                self.config['audio'] = {}
            self.config['audio']['sensitivity'] = overrides['audio_sensitivity']
        if overrides.get('bg_enabled') is not None:
            if 'background' not in self.config:
                self.config['background'] = {'color': [0.2, 0.2, 0.25, 0.85], 'padding': 10}
            self.config['background']['enabled'] = overrides['bg_enabled']
        if overrides.get('bg_opacity') is not None:
            if 'background' not in self.config:
                self.config['background'] = {'enabled': True, 'color': [0.2, 0.2, 0.25, 0.85], 'padding': 10}
            self.config['background']['color'][3] = max(0.0, min(1.0, overrides['bg_opacity']))
            self.config['background']['enabled'] = True

    def setup_window(self):
        """Set up GTK3 window with layer shell"""
        print(_("=== Overlay configuration ==="))
        print(_("Type: {type}").format(type=self.config['animation_type']))
        print(_("Position: {pos}").format(pos=self.config.get('position', 'bottom')))
        print(_("Dimensions: {w}x{h}px").format(w=self.config['width'], h=self.config['height']))
        margins = self.config['layer']['margin']
        print(_("Margins: top={top}px, bottom={bottom}px, left={left}px, right={right}px").format(
              top=margins['top'], bottom=margins['bottom'],
              left=margins['left'], right=margins['right']))
        print()
        print(_("Creating transparent overlay..."))
        self.window = Gtk.Window()

        # Initialize layer shell
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, "animation-speech-overlay")
        print(_("Layer shell enabled"))

        # Configure layer (overlay = on top of everything)
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)

        # Position from config
        position = self.config.get('position', 'bottom')
        self.setup_layer_position(position)

        # No exclusive zone
        GtkLayerShell.set_exclusive_zone(self.window, 0)

        # Keyboard mode: EXCLUSIVE if on-escape is configured, otherwise NONE
        if self.on_escape_cmd:
            GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
            print(_("Exclusive keyboard grab (Escape to cancel)"))
        else:
            GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)

        # Window size
        self.window.set_default_size(
            self.config['width'],
            self.config['height']
        )

        if self.on_escape_cmd:
            # Let clicks through but keep keyboard focus
            self.window.input_shape_combine_region(cairo.Region())
            self.window.connect('key-press-event', self.on_key_press)
        else:
            # IMPORTANT: Let mouse clicks pass through the window
            self.window.input_shape_combine_region(cairo.Region())
            self.window.set_accept_focus(False)

        # Make window transparent
        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
            print(_("Transparency enabled"))

        self.window.set_app_paintable(True)
        self.window.set_decorated(False)

        # Drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(self.config['width'], self.config['height'])
        self.drawing_area.connect('draw', self.on_draw)
        self.window.add(self.drawing_area)

        # Animation timer
        fps = self.config['animation']['fps']
        GLib.timeout_add(1000 // fps, self.update_animation)

        self.window.show_all()
        print(_("Overlay displayed ({w}x{h})").format(w=self.config['width'], h=self.config['height']))

    def setup_layer_position(self, position):
        """Configure layer shell position"""
        # Reset all anchors
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, False)

        if position == 'bottom':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
        elif position == 'top':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        elif position == 'left':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'right':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)
        elif position == 'center':
            pass
        elif position == 'manual':
            # Anchored top-left, positioned via top/left margins
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'top-left':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'top-right':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)
        elif position == 'bottom-left':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        elif position == 'bottom-right':
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)

        # Margins from config
        margins = self.config['layer']['margin']
        margin_bottom = margins['bottom']
        # Minimum margin for bottom positions (space for dock)
        if position in ('bottom', 'bottom-left', 'bottom-right'):
            margin_bottom = max(margin_bottom, 80)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, max(margins['top'], 10))
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, margin_bottom)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, max(margins['left'], 10))
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.RIGHT, max(margins['right'], 10))

    def setup_signals(self):
        """Set up UNIX signals for start/stop"""
        signal.signal(signal.SIGUSR1, self.start_animation)
        signal.signal(signal.SIGUSR2, self.stop_animation)

        # Handlers for clean exit
        signal.signal(signal.SIGTERM, self.cleanup_and_exit)
        signal.signal(signal.SIGINT, self.cleanup_and_exit)

        print(_("\nPID: {pid}").format(pid=os.getpid()))
        if self.pid_file:
            print(_("PID file: {path}").format(path=self.pid_file))
        print(_("Send 'kill -SIGUSR1 {pid}' to start").format(pid=os.getpid()))
        print(_("Send 'kill -SIGUSR2 {pid}' to stop\n").format(pid=os.getpid()))

    def cleanup_and_exit(self, signum, frame):
        """Clean up and exit gracefully"""
        signame = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT' if signum == signal.SIGINT else f'Signal {signum}'
        print(_("\n{signal} received, cleaning up...").format(signal=signame))

        # Stop audio capture
        if self.audio_enabled:
            self.stop_audio_capture()
            print(_("Audio capture stopped"))

        # Stop animation
        self.is_animating = False

        # Destroy window to release screen area
        if self.window:
            try:
                print(_("Destroying window..."))
                self.window.hide()
                self.window.destroy()
                self.window = None
            except Exception as e:
                print(_("Error destroying window: {error}").format(error=e))

        # Remove PID file
        pid_file = self.pid_file
        self.cleanup_pid_file()
        if pid_file:
            print(_("PID file removed: {path}").format(path=pid_file))

        print(_("Cleanup complete, goodbye!"))

        # Quit via GLib.idle_add to avoid issues in signal handler
        GLib.idle_add(Gtk.main_quit)

    def on_key_press(self, widget, event):
        """Handle key presses (Escape to cancel)"""
        if event.keyval == Gdk.KEY_Escape:
            print(_("Escape pressed, executing cancel command..."))
            subprocess.Popen(self.on_escape_cmd, shell=True)
            self.cleanup_and_exit(signal.SIGTERM, None)
        return True  # Consume all key events

    def start_animation(self, signum, frame):
        """Start animation (SIGUSR1 signal)"""
        print(_("Animation started"))
        self.is_animating = True

    def stop_animation(self, signum, frame):
        """Stop animation (SIGUSR2 signal)"""
        print(_("Animation stopped"))
        self.is_animating = False

    def update_animation(self):
        """Update animation state"""
        if self.is_animating:
            self.frame += 1

            if self.config['animation_type'] == 'equalizer':
                self.update_equalizer()
            elif self.config['animation_type'] == 'particles':
                self.update_particles()

        self.drawing_area.queue_draw()
        return True

    def update_equalizer(self):
        """Update equalizer bars"""
        smoothing = self.config['animation']['smoothing']
        base_intensity = self.config['animation']['intensity']

        if self.audio_enabled:
            intensity = base_intensity * (0.05 + self.audio_level * 3.0)
        else:
            intensity = base_intensity

        for i in range(len(self.target_bars)):
            if random.random() < 0.3:
                self.target_bars[i] = random.random() * intensity

        for i in range(len(self.bars)):
            self.bars[i] += (self.target_bars[i] - self.bars[i]) * smoothing

    def update_particles(self):
        """Update particles"""
        if self.audio_enabled:
            spawn_rate = 0.05 + self.audio_level * 0.9
            size_mult = 0.2 + self.audio_level * 3.0
            speed_mult = 0.3 + self.audio_level * 2.0
        else:
            spawn_rate = 0.5
            size_mult = 1.0
            speed_mult = 1.0

        if self.is_animating and random.random() < spawn_rate:
            self.particles.append({
                'x': random.random(),
                'y': 0.5,
                'vx': (random.random() - 0.5) * 0.02 * speed_mult,
                'vy': (random.random() - 0.5) * 0.02 * speed_mult,
                'life': 1.0,
                'size': (random.random() * 5 + 2) * size_mult
            })

        self.particles = [p for p in self.particles if p['life'] > 0]
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 0.02

    def on_draw(self, widget, cr):
        """Cairo drawing function"""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Transparent background
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw only if active
        if self.is_animating:
            cr.save()
            self._draw_background_cartouche(cr, width, height)
            self.dispatch_draw(cr, width, height)
            cr.restore()

    def run(self):
        """Run the application"""
        try:
            Gtk.main()
        except KeyboardInterrupt:
            print(_("\nKeyboard interrupt (Ctrl+C), stopping..."))
        except Exception as e:
            print(_("\nUnexpected error: {error}").format(error=e))
            traceback.print_exc()
        finally:
            print(_("Final cleanup..."))

            if self.window:
                try:
                    self.window.hide()
                    self.window.destroy()
                    self.window = None
                except Exception:
                    pass

            while Gtk.events_pending():
                Gtk.main_iteration()

            self.cleanup_pid_file()

            if Gtk.main_level() > 0:
                Gtk.main_quit()


class AnimationPreview(AnimationDrawMixin):
    """Miniature animation preview for the chooser"""

    def __init__(self, config_path):
        self.config_path = config_path
        self.name = os.path.basename(config_path).rsplit('.', 1)[0]
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        normalize_config_colors(self.config)
        self.frame = 0
        self.is_animating = True
        self.audio_enabled = False
        self.audio_level = 0.0
        # Equalizer state
        bar_count = self.config.get('animation', {}).get('bar_count', 20)
        self.bars = [0.0] * bar_count
        self.target_bars = [0.0] * bar_count
        # Particles state
        self.particles = []
        # Circular spawn state
        self.circles = []
        self._spawn_acc = 0.0

    def update_config(self, config_dict):
        """Update config and reset internal state"""
        self.config = config_dict
        normalize_config_colors(self.config)
        self.name = config_dict.get('_name', self.name)
        # Reset states
        bar_count = self.config.get('animation', {}).get('bar_count', 20)
        self.bars = [0.0] * bar_count
        self.target_bars = [0.0] * bar_count
        self.particles = []
        self.circles = []
        self._spawn_acc = 0.0
        self.frame = 0

    def update(self):
        self.frame += 1
        anim_type = self.config['animation_type']
        if anim_type == 'equalizer':
            smoothing = self.config['animation'].get('smoothing', 0.3)
            base_intensity = self.config['animation'].get('intensity', 1.0)
            if self.audio_enabled:
                intensity = base_intensity * (0.05 + self.audio_level * 3.0)
            else:
                intensity = base_intensity
            for i in range(len(self.target_bars)):
                if random.random() < 0.3:
                    self.target_bars[i] = random.random() * intensity
            for i in range(len(self.bars)):
                self.bars[i] += (self.target_bars[i] - self.bars[i]) * smoothing
        elif anim_type == 'particles':
            if self.audio_enabled:
                spawn_rate = 0.05 + self.audio_level * 0.9
                size_mult = 0.2 + self.audio_level * 3.0
                speed_mult = 0.3 + self.audio_level * 2.0
            else:
                spawn_rate = 0.5
                size_mult = 1.0
                speed_mult = 1.0
            if random.random() < spawn_rate:
                self.particles.append({
                    'x': random.random(), 'y': 0.5,
                    'vx': (random.random()-0.5)*0.02 * speed_mult,
                    'vy': (random.random()-0.5)*0.02 * speed_mult,
                    'life': 1.0, 'size': (random.random()*5+2) * size_mult
                })
            self.particles = [p for p in self.particles if p['life'] > 0]
            for p in self.particles:
                p['x'] += p['vx']; p['y'] += p['vy']; p['life'] -= 0.02

    def draw(self, cr, width, height):
        # Black background for preview
        cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        # Rounded background if configured (with clip)
        self._draw_background_cartouche(cr, width, height)

        # Draw with fewer points for preview
        anim_type = self.config['animation_type']
        if anim_type == 'wave':
            self.draw_wave(cr, width, height, num_points=100)
        elif anim_type == 'soundwave-curve':
            self.draw_soundwave_curve(cr, width, height, num_points=100)
        elif anim_type == 'circular-wave':
            self.draw_circular_wave(cr, width, height, num_points=120)
        else:
            self.dispatch_draw(cr, width, height)
        cr.restore()
