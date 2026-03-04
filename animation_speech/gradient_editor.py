"""GradientEditor — widget for editing gradient color stops."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from .utils import _


class GradientEditor(Gtk.Box):
    """Widget for editing gradient colors"""

    def __init__(self, colors, on_change):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.on_change = on_change
        self.color_buttons = []
        self._build(colors)

    def _build(self, colors):
        # Clear
        for child in self.get_children():
            self.remove(child)
        self.color_buttons = []

        for i, rgba in enumerate(colors):
            btn = Gtk.ColorButton()
            gdk_rgba = Gdk.RGBA()
            gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba
            btn.set_rgba(gdk_rgba)
            btn.set_use_alpha(True)
            btn.set_title(_("Gradient stop {n}").format(n=i+1))
            btn.connect('color-set', lambda b: self._emit_change())
            self.color_buttons.append(btn)
            self.pack_start(btn, False, False, 0)

        add_btn = Gtk.Button(label="+")
        add_btn.set_tooltip_text(_("Add a color"))
        add_btn.connect('clicked', self._on_add)
        self.pack_start(add_btn, False, False, 4)

        if len(self.color_buttons) > 2:
            rm_btn = Gtk.Button(label="\u2212")
            rm_btn.set_tooltip_text(_("Remove last color"))
            rm_btn.connect('clicked', self._on_remove)
            self.pack_start(rm_btn, False, False, 0)

        self.show_all()

    def _on_add(self, button):
        colors = self.get_colors()
        colors.append(list(colors[-1]))
        self._build(colors)
        self._emit_change()

    def _on_remove(self, button):
        colors = self.get_colors()
        if len(colors) > 2:
            colors.pop()
            self._build(colors)
            self._emit_change()

    def get_colors(self):
        result = []
        for btn in self.color_buttons:
            rgba = btn.get_rgba()
            result.append([rgba.red, rgba.green, rgba.blue, rgba.alpha])
        return result

    def set_colors(self, colors):
        self._build(colors)

    def _emit_change(self):
        self.on_change(self.get_colors())
