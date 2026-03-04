"""AnimationDrawMixin — shared Cairo drawing logic."""

import math
import cairo

from .utils import _


class AnimationDrawMixin:
    """Mixin containing all shared drawing logic between
    SpeechAnimation (overlay) and AnimationPreview (chooser)."""

    def _get_gradient_colors(self):
        """Return the gradient color list (or fallback primary->secondary)"""
        gradient = self.config['colors'].get('gradient')
        if gradient and len(gradient) >= 2:
            return gradient
        return [self.config['colors']['primary'], self.config['colors']['secondary']]

    def _build_cairo_gradient(self, width, opacity_mult=1.0):
        """Build a horizontal cairo.LinearGradient with gradient colors"""
        colors = self._get_gradient_colors()
        pattern = cairo.LinearGradient(0, 0, width, 0)
        for i, color in enumerate(colors):
            offset = i / max(1, len(colors) - 1)
            pattern.add_color_stop_rgba(offset, color[0], color[1], color[2], color[3] * opacity_mult)
        return pattern

    def _get_color_at(self, t):
        """Return the interpolated color at position t (0.0-1.0) in the gradient"""
        colors = self._get_gradient_colors()
        if len(colors) == 1:
            return colors[0]
        t = max(0.0, min(1.0, t))
        pos = t * (len(colors) - 1)
        idx = int(pos)
        frac = pos - idx
        if idx >= len(colors) - 1:
            return colors[-1]
        c1 = colors[idx]
        c2 = colors[idx + 1]
        return [
            c1[0] + (c2[0] - c1[0]) * frac,
            c1[1] + (c2[1] - c1[1]) * frac,
            c1[2] + (c2[2] - c1[2]) * frac,
            c1[3] + (c2[3] - c1[3]) * frac,
        ]

    def _draw_rounded_rect(self, cr, x, y, w, h, radius):
        """Draw a rounded rectangle (Cairo path)"""
        radius = min(radius, w / 2, h / 2)
        cr.new_path()
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.arc(x + w - radius, y + radius, radius, 3 * math.pi / 2, 0)
        cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        cr.close_path()

    def _get_content_bounds(self, width, height):
        """Return (x, y, w, h) of the animation content area"""
        anim_type = self.config['animation_type']

        if anim_type in ('equalizer', 'soundwave'):
            return (0, 0, width, height)

        if anim_type in ('circular', 'circular-wave', 'circular-bars'):
            max_radius = height * 0.45
            cx, cy = width / 2, height / 2
            return (cx - max_radius, cy - max_radius,
                    max_radius * 2, max_radius * 2)

        # wave, soundwave-curve, particles
        return (0, 0, width, height)

    def _get_cartouche_bounds(self, width, height):
        """Return (x, y, w, h, radius) of the cartouche, or None if disabled"""
        bg_config = self.config.get('background', {})
        if not bg_config.get('enabled', False):
            return None
        padding = bg_config.get('padding', 10)
        cx, cy, cw, ch = self._get_content_bounds(width, height)
        bx = max(0, cx - padding)
        by = max(0, cy - padding)
        bw = min(width, cx + cw + padding) - bx
        bh = min(height, cy + ch + padding) - by
        radius = min(bw, bh) / 2
        return (bx, by, bw, bh, radius)

    def _get_draw_area(self, width, height):
        """Return (x, y, w, h) of the effective drawing area.
        Always computes the inset (even if the cartouche is hidden)
        so the animation size stays consistent."""
        cx, cy, cw, ch = self._get_content_bounds(width, height)
        padding = self.config.get('background', {}).get('padding', 10)
        bx = max(0, cx - padding)
        by = max(0, cy - padding)
        bw = min(width, cx + cw + padding) - bx
        bh = min(height, cy + ch + padding) - by
        radius = min(bw, bh) / 2
        inset = radius * 0.3
        return (bx + inset, by + inset, bw - inset * 2, bh - inset * 2)

    def _draw_background_cartouche(self, cr, width, height):
        """Draw the semi-transparent capsule background if configured"""
        bounds = self._get_cartouche_bounds(width, height)
        if bounds is None:
            return
        bx, by, bw, bh, radius = bounds
        bg_config = self.config.get('background', {})
        color = bg_config.get('color', [0.2, 0.2, 0.25, 0.85])
        cr.set_source_rgba(color[0], color[1], color[2], color[3])
        self._draw_rounded_rect(cr, bx, by, bw, bh, radius)
        cr.fill()
        # Border (inward)
        border_width = bg_config.get('border_width', 0)
        if border_width > 0:
            border_color = bg_config.get('border_color', [1.0, 1.0, 1.0, 0.5])
            cr.set_source_rgba(border_color[0], border_color[1], border_color[2], border_color[3])
            cr.set_line_width(border_width)
            inset = border_width / 2
            self._draw_rounded_rect(cr, bx + inset, by + inset,
                                    bw - inset * 2, bh - inset * 2,
                                    max(0, radius - inset))
            cr.stroke()
        self._draw_rounded_rect(cr, bx, by, bw, bh, radius)
        cr.clip()

    def _get_audio_boost(self, base_value, silent_min, active_mult):
        """Return the value modulated by audio if enabled"""
        if self.audio_enabled:
            return base_value * (silent_min + self.audio_level * active_mult)
        return base_value

    def _has_gradient(self):
        """Check if a multi-color gradient is configured"""
        return 'gradient' in self.config['colors'] and \
               len(self.config['colors'].get('gradient', [])) >= 2

    def _interpolate_primary_secondary(self, t_color):
        """Interpolate between primary and secondary at position t_color (0.0-1.0)"""
        primary = self.config['colors']['primary']
        secondary = self.config['colors']['secondary']
        r = primary[0] * (1 - t_color) + secondary[0] * t_color
        g = primary[1] * (1 - t_color) + secondary[1] * t_color
        b = primary[2] * (1 - t_color) + secondary[2] * t_color
        a = primary[3] * (1 - t_color) + secondary[3] * t_color
        return r, g, b, a

    def draw_equalizer(self, cr, width, height):
        """Draw the equalizer bar animation"""
        bar_count = self.config['animation']['bar_count']
        bar_spacing = self.config['animation']['bar_spacing']

        dx, dy, dw, dh = self._get_draw_area(width, height)

        # bar_width computed to fill available area
        total_spacing = (bar_count - 1) * bar_spacing
        bar_width = max(1, (dw - total_spacing) / bar_count)

        for i, value in enumerate(self.bars):
            x = dx + i * (bar_width + bar_spacing)
            t = i / bar_count
            envelope = math.sin(t * math.pi)
            bar_height = min(dh - 4, max(3, value * envelope * dh * 0.8))
            y = dy + (dh - bar_height) / 2

            color = self._get_color_at(t)
            cr.set_source_rgba(color[0], color[1], color[2], color[3])
            cr.rectangle(x, y, bar_width, bar_height)
            cr.fill()

    def draw_wave(self, cr, width, height, num_points=200):
        """Draw flowing wave curves with gradient and fill support"""
        dx, dy, dw, dh = self._get_draw_area(width, height)
        cy = dy + dh / 2
        base_intensity = self.config['animation']['intensity']
        intensity = self._get_audio_boost(base_intensity, 0.05, 2.5)
        freq = self.config['animation'].get('wave_frequency', 1.0)
        wave_count = self.config['animation'].get('wave_count', 8)
        fill_wave = self.config['animation'].get('fill_wave', False)
        fill_opacity = self.config['animation'].get('fill_opacity', 0.3)
        has_gradient = self._has_gradient()

        for w in range(wave_count):
            phase_offset = w * 0.4

            wave_points = []
            half_h = dh / 2
            for i in range(num_points + 1):
                t = i / num_points
                x = dx + t * dw

                envelope = math.sin(t * math.pi)

                wave1 = math.sin(t * math.pi * 3 * freq + self.frame * 0.08 + phase_offset) * 0.5
                wave2 = math.sin(t * math.pi * 5 * freq + self.frame * 0.12 + phase_offset * 0.7) * 0.3
                wave3 = math.sin(t * math.pi * 7 * freq - self.frame * 0.06 + phase_offset * 0.5) * 0.2

                combined = (wave1 + wave2 + wave3) * intensity * envelope
                amplitude = half_h * 0.8 * combined
                amplitude = max(-half_h + 2, min(half_h - 2, amplitude))
                y = cy + amplitude
                wave_points.append((x, y))

            # Fill between curve and center line
            if fill_wave:
                cr.move_to(wave_points[0][0], cy)
                for x, y in wave_points:
                    cr.line_to(x, y)
                cr.line_to(wave_points[-1][0], cy)
                cr.close_path()

                if has_gradient:
                    wave_opacity = fill_opacity * (1.0 - w * 0.15)
                    cr.set_source(self._build_cairo_gradient(width, opacity_mult=max(0.05, wave_opacity)))
                else:
                    t_color = w / max(1, wave_count - 1)
                    r, g, b, _a = self._interpolate_primary_secondary(t_color)
                    cr.set_source_rgba(r, g, b, fill_opacity * (1.0 - w * 0.15))
                cr.fill()

            # Draw the curve line
            cr.move_to(wave_points[0][0], wave_points[0][1])
            for x, y in wave_points[1:]:
                cr.line_to(x, y)

            line_width = max(1.0, 2.5 - (w / max(1, wave_count)) * 1.5)
            cr.set_line_width(line_width)
            if has_gradient:
                cr.set_source(self._build_cairo_gradient(width))
            else:
                t_color = w / max(1, wave_count - 1)
                r, g, b, a = self._interpolate_primary_secondary(t_color)
                cr.set_source_rgba(r, g, b, a * (1 - t_color * 0.3))

            cr.stroke()

    def draw_circular(self, cr, width, height):
        """Draw concentric circular waves (dynamic spawn)"""
        cx, cy = width / 2, height / 2

        circle_count = self.config['animation'].get('circle_count', 12)
        max_radius = height * 0.4
        base_speed = self.config['animation'].get('circle_speed', 2.0)
        direction = self.config['animation'].get('circle_direction', 'outward')

        if self.audio_enabled:
            # Volume -> circle emission rate
            emit_rate = self.audio_level * 0.5
        else:
            # Without audio: regular emission
            emit_rate = base_speed * circle_count / 500.0

        # Accumulate and spawn new circles
        self._spawn_acc += emit_rate
        color_idx = 0
        while self._spawn_acc >= 1.0:
            self._spawn_acc -= 1.0
            self.circles.append({
                'radius': 0.0,
                'color_t': (self.frame * 0.05 + color_idx * 0.1) % 1.0,
            })
            color_idx += 1

        # Grow each circle
        grow = base_speed * 1.5
        for c in self.circles:
            c['radius'] += grow

        # Remove out-of-bounds circles
        self.circles = [c for c in self.circles if c['radius'] <= max_radius]

        for c in self.circles:
            r = c['radius']
            t = r / max_radius  # 0 au centre, 1 au bord

            if direction == 'inward':
                draw_radius = max_radius - r
                fade = 1 - t
            elif direction == 'ping-pong':
                draw_radius = max_radius - abs(max_radius - r * 2)
                fade = 1.0 - abs(t - 0.5) * 2
                fade = max(0, fade)
            else:  # outward
                draw_radius = r
                fade = 1 - t

            if draw_radius < 2:
                continue

            alpha = max(0, fade) ** 1.3 * 0.9

            color = self._get_color_at(c['color_t'])
            cr.set_source_rgba(color[0], color[1], color[2], alpha * color[3])
            cr.set_line_width(1.0 + fade * 1.5)
            cr.arc(cx, cy, draw_radius, 0, 2 * math.pi)
            cr.stroke()

    def draw_circular_wave(self, cr, width, height, num_points=180):
        """Draw a vibrating circle with sinusoidal deformation on the circumference"""
        cx, cy = width / 2, height / 2
        base_radius = height * 0.3
        intensity = self.config['animation'].get('intensity', 1.0)
        wave_freq = self.config['animation'].get('wave_frequency', 6.0)
        wave_count = self.config['animation'].get('wave_count', 3)
        fill_opacity = self.config['animation'].get('fill_opacity', 0.15)

        audio_boost = 1.0
        if self.audio_enabled:
            audio_boost = 0.2 + self.audio_level * 3.0

        has_gradient = self._has_gradient()

        for w in range(wave_count):
            phase_offset = w * 0.7
            amplitude = base_radius * 0.25 * intensity * audio_boost * (1.0 - w * 0.2)

            wave_points = []
            for i in range(num_points):
                theta = (i / num_points) * 2 * math.pi
                deform = math.sin(theta * wave_freq + self.frame * 0.08 + phase_offset) * 0.5
                deform += math.sin(theta * wave_freq * 2.3 + self.frame * 0.12 + phase_offset * 0.7) * 0.3
                deform += math.sin(theta * wave_freq * 0.7 - self.frame * 0.06 + phase_offset * 1.3) * 0.2
                r = base_radius + amplitude * deform
                x = cx + r * math.cos(theta)
                y = cy + r * math.sin(theta)
                wave_points.append((x, y))

            # Semi-transparent fill
            if fill_opacity > 0:
                cr.move_to(wave_points[0][0], wave_points[0][1])
                for x, y in wave_points[1:]:
                    cr.line_to(x, y)
                cr.close_path()
                if has_gradient:
                    pat = cairo.RadialGradient(cx, cy, 0, cx, cy, base_radius * 1.3)
                    colors = self._get_gradient_colors()
                    op = max(0.05, fill_opacity * (1.0 - w * 0.3))
                    for idx, color in enumerate(colors):
                        offset = idx / max(1, len(colors) - 1)
                        pat.add_color_stop_rgba(offset, color[0], color[1], color[2], color[3] * op)
                    cr.set_source(pat)
                else:
                    primary = self.config['colors']['primary']
                    cr.set_source_rgba(primary[0], primary[1], primary[2],
                                       primary[3] * fill_opacity * (1.0 - w * 0.3))
                cr.fill()

            # Outline: draw segment by segment with gradient color on theta
            line_w = max(1.0, 2.5 - w * 0.5)
            cr.set_line_width(line_w)
            opacity_mult = max(0.3, 1.0 - w * 0.25)
            for i in range(num_points):
                x1, y1 = wave_points[i]
                x2, y2 = wave_points[(i + 1) % num_points]
                t = i / num_points
                color = self._get_color_at(t)
                cr.set_source_rgba(color[0], color[1], color[2], color[3] * opacity_mult)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()

    def draw_circular_bars(self, cr, width, height):
        """Draw radial bars emanating from a central circle"""
        cx, cy = width / 2, height / 2
        bar_count = self.config['animation'].get('bar_count', 60)
        bar_width = self.config['animation'].get('bar_width', 3)
        base_radius = height * 0.2
        max_bar_len = height * 0.25
        intensity = self.config['animation'].get('intensity', 1.0)
        wave_freq = self.config['animation'].get('wave_frequency', 2.0)

        audio_boost = 1.0
        if self.audio_enabled:
            audio_boost = 0.15 + self.audio_level * 3.0

        rotation = self.config['animation'].get('bars_rotation', 0) * math.pi / 180

        for i in range(bar_count):
            theta = (i / bar_count) * 2 * math.pi + rotation
            t = i / bar_count

            envelope = 0.5 + 0.5 * math.sin(t * math.pi * 2)
            wave1 = math.sin(t * math.pi * 4 * wave_freq + self.frame * 0.1) * 0.5
            wave2 = math.sin(t * math.pi * 7 * wave_freq + self.frame * 0.15) * 0.3
            wave3 = math.sin(t * math.pi * 11 * wave_freq - self.frame * 0.08) * 0.2
            combined = abs(wave1 + wave2 + wave3) * intensity * audio_boost
            bar_len = max(2, combined * max_bar_len * (0.3 + envelope * 0.7))

            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            x1 = cx + base_radius * cos_t
            y1 = cy + base_radius * sin_t
            x2 = cx + (base_radius + bar_len) * cos_t
            y2 = cy + (base_radius + bar_len) * sin_t

            color = self._get_color_at(t)
            cr.set_source_rgba(color[0], color[1], color[2], color[3])
            cr.set_line_width(bar_width)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

    def draw_particles(self, cr, width, height):
        """Draw particles"""
        primary = self.config['colors']['primary']

        for p in self.particles:
            x = p['x'] * width
            y = p['y'] * height
            alpha = p['life'] * primary[3]

            cr.set_source_rgba(primary[0], primary[1], primary[2], alpha)
            cr.arc(x, y, p['size'], 0, 2 * math.pi)
            cr.fill()

    def draw_soundwave(self, cr, width, height):
        """Draw an audio waveform with vertical bars"""
        dx, dy, dw, dh = self._get_draw_area(width, height)
        cy = dy + dh / 2
        bar_count = self.config['animation'].get('bar_count', 60)
        bar_spacing = self.config['animation'].get('bar_spacing', 2)
        base_intensity = self.config['animation']['intensity']
        freq = self.config['animation'].get('wave_frequency', 2.0)

        intensity = self._get_audio_boost(base_intensity, 0.05, 2.5)

        # bar_width computed to fill available area
        total_spacing = (bar_count - 1) * bar_spacing
        bar_width = max(1, (dw - total_spacing) / bar_count)

        for i in range(bar_count):
            t = i / bar_count
            x = dx + i * (bar_width + bar_spacing)

            envelope = math.sin(t * math.pi)

            wave1 = math.sin(t * math.pi * 4 * freq + self.frame * 0.1) * 0.5
            wave2 = math.sin(t * math.pi * 7 * freq + self.frame * 0.15) * 0.3
            wave3 = math.sin(t * math.pi * 11 * freq - self.frame * 0.08) * 0.2

            combined = abs(wave1 + wave2 + wave3) * intensity * envelope
            bar_height = min(dh - 4, max(2, combined * dh * 0.8))

            y = cy - bar_height / 2

            color = self._get_color_at(t)
            cr.set_source_rgba(color[0], color[1], color[2], color[3])
            cr.rectangle(x, y, bar_width, bar_height)
            cr.fill()

    def draw_soundwave_curve(self, cr, width, height, num_points=200):
        """Draw a symmetric waveform with smooth curves (top/bottom mirror)"""
        dx, dy, dw, dh = self._get_draw_area(width, height)
        cy = dy + dh / 2
        base_intensity = self.config['animation']['intensity']
        freq = self.config['animation'].get('wave_frequency', 2.0)
        fill_opacity = self.config['animation'].get('fill_opacity', 0.3)
        wave_count = self.config['animation'].get('wave_count', 1)
        has_gradient = self._has_gradient()

        intensity = self._get_audio_boost(base_intensity, 0.05, 2.5)

        for w in range(wave_count):
            phase_offset = w * 0.4

            wave_points = []
            for i in range(num_points + 1):
                t = i / num_points
                x = dx + t * dw
                envelope = math.sin(t * math.pi)
                wave1 = math.sin(t * math.pi * 4 * freq + self.frame * 0.1 + phase_offset) * 0.5
                wave2 = math.sin(t * math.pi * 7 * freq + self.frame * 0.15 + phase_offset * 0.7) * 0.3
                wave3 = math.sin(t * math.pi * 11 * freq - self.frame * 0.08 + phase_offset * 0.5) * 0.2
                combined = abs(wave1 + wave2 + wave3) * intensity * envelope
                amp = min((dh - 4) / 2, max(1, combined * dh * 0.4))
                wave_points.append((x, amp))

            # Fill: upper curve then lower curve (mirror)
            cr.move_to(wave_points[0][0], cy - wave_points[0][1])
            for x, amp in wave_points[1:]:
                cr.line_to(x, cy - amp)
            for x, amp in reversed(wave_points):
                cr.line_to(x, cy + amp)
            cr.close_path()

            if has_gradient:
                wave_opacity = fill_opacity * (1.0 - w * 0.15)
                cr.set_source(self._build_cairo_gradient(width, opacity_mult=max(0.05, wave_opacity)))
            else:
                t_color = w / max(1, wave_count - 1)
                r, g, b, _a = self._interpolate_primary_secondary(t_color)
                cr.set_source_rgba(r, g, b, fill_opacity * (1.0 - w * 0.15))
            cr.fill()

            # Upper outline
            cr.move_to(wave_points[0][0], cy - wave_points[0][1])
            for x, amp in wave_points[1:]:
                cr.line_to(x, cy - amp)
            line_width = max(1.0, 2.5 - (w / max(1, wave_count)) * 1.5)
            cr.set_line_width(line_width)
            if has_gradient:
                cr.set_source(self._build_cairo_gradient(width))
            else:
                t_color = w / max(1, wave_count - 1)
                r, g, b, a = self._interpolate_primary_secondary(t_color)
                cr.set_source_rgba(r, g, b, a * (1 - t_color * 0.3))
            cr.stroke()

            # Lower outline (mirror)
            cr.move_to(wave_points[0][0], cy + wave_points[0][1])
            for x, amp in wave_points[1:]:
                cr.line_to(x, cy + amp)
            cr.set_line_width(line_width)
            if has_gradient:
                cr.set_source(self._build_cairo_gradient(width))
            else:
                cr.set_source_rgba(r, g, b, a * (1 - t_color * 0.3))
            cr.stroke()

    def dispatch_draw(self, cr, width, height):
        """Dispatch drawing to the method matching the animation type"""
        anim_type = self.config['animation_type']

        if anim_type == 'equalizer':
            self.draw_equalizer(cr, width, height)
        elif anim_type == 'wave':
            self.draw_wave(cr, width, height)
        elif anim_type == 'circular':
            self.draw_circular(cr, width, height)
        elif anim_type == 'particles':
            self.draw_particles(cr, width, height)
        elif anim_type == 'soundwave':
            self.draw_soundwave(cr, width, height)
        elif anim_type == 'soundwave-curve':
            self.draw_soundwave_curve(cr, width, height)
        elif anim_type == 'circular-wave':
            self.draw_circular_wave(cr, width, height)
        elif anim_type == 'circular-bars':
            self.draw_circular_bars(cr, width, height)
