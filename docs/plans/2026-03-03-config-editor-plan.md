# Éditeur de configuration --choose : Plan d'implémentation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformer le sélecteur `--choose` en un éditeur complet avec split panel (grille à gauche, éditeur avec preview live à droite).

**Architecture:** On modifie `ConfigChooser` pour utiliser un `Gtk.Paned` horizontal. Le panneau gauche garde la grille FlowBox existante + bouton "Nouveau". Le panneau droit est un nouveau widget `ConfigEditor` avec preview `AnimationPreview` en grand + contrôles (sliders, color pickers, combos). On ajoute aussi `GradientEditor` et des palettes prédéfinies.

**Tech Stack:** Python 3, GTK3 (gi.repository Gtk 3.0), Cairo, PyYAML

**Fichier unique modifié :** `animation-speech.py`

---

### Task 1: AnimationPreview.update_config()

Ajouter une méthode à `AnimationPreview` pour mettre à jour la config à la volée (nécessaire pour le live preview).

**Files:**
- Modify: `animation-speech.py:1054-1117` (classe `AnimationPreview`)

**Step 1: Ajouter la méthode `update_config` après `__init__`**

Insérer après la ligne `self.particles = []` (fin de `__init__`, ~ligne 1072) :

```python
def update_config(self, config_dict):
    """Met à jour la config et réinitialise les états internes"""
    self.config = config_dict
    normalize_config_colors(self.config)
    self.name = config_dict.get('_name', self.name)
    # Réinitialiser les états
    bar_count = self.config.get('animation', {}).get('bar_count', 20)
    self.bars = [0.0] * bar_count
    self.target_bars = [0.0] * bar_count
    self.particles = []
    self.frame = 0
```

**Step 2: Tester manuellement**

Lancer `./animation-speech.py --choose`, vérifier que rien n'est cassé (la grille existante doit fonctionner exactement comme avant).

**Step 3: Commit**

```bash
git add animation-speech.py
git commit -m "feat(preview): ajout update_config() pour le live preview"
```

---

### Task 2: Constantes et palettes prédéfinies

Ajouter les constantes de palettes et la table de visibilité conditionnelle des paramètres.

**Files:**
- Modify: `animation-speech.py` — après `VALID_ANIMATION_TYPES` (~ligne 74)

**Step 1: Ajouter les constantes**

Insérer après `VALID_ANIMATION_TYPES` (ligne 74) :

```python
VALID_POSITIONS = (
    'bottom', 'top', 'center', 'left', 'right',
    'top-left', 'top-right', 'bottom-left', 'bottom-right',
)

# Palettes de couleurs prédéfinies (RGBA 0.0-1.0)
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

# Visibilité des paramètres par type d'animation
# True = affiché, absent = masqué
PARAM_VISIBILITY = {
    'wave_frequency': {'wave', 'circular', 'soundwave-curve', 'circular-wave', 'circular-bars'},
    'bar_count':      {'equalizer', 'soundwave', 'circular-bars'},
    'bar_width':      {'equalizer', 'soundwave', 'circular-bars'},
    'bar_spacing':    {'equalizer', 'soundwave'},
    'wave_count':     {'wave', 'soundwave-curve'},
    'fill_wave':      {'wave', 'soundwave-curve'},
    'fill_opacity':   {'wave', 'soundwave-curve'},
}
```

**Step 2: Commit**

```bash
git add animation-speech.py
git commit -m "feat: constantes palettes et visibilité paramètres"
```

---

### Task 3: Widget GradientEditor

Widget pour éditer les stops du gradient (boutons couleur + ajouter/supprimer).

**Files:**
- Modify: `animation-speech.py` — insérer avant `class ConfigChooser` (~ligne 1119)

**Step 1: Écrire la classe GradientEditor**

```python
class GradientEditor(Gtk.Box):
    """Widget pour éditer les couleurs du gradient"""

    def __init__(self, colors, on_change):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.on_change = on_change
        self.color_buttons = []
        self._build(colors)

    def _build(self, colors):
        # Vider
        for child in self.get_children():
            self.remove(child)
        self.color_buttons = []

        for i, rgba in enumerate(colors):
            btn = Gtk.ColorButton()
            gdk_rgba = Gdk.RGBA()
            gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba
            btn.set_rgba(gdk_rgba)
            btn.set_use_alpha(True)
            btn.set_title(f"Gradient stop {i+1}")
            btn.connect('color-set', lambda b: self._emit_change())
            self.color_buttons.append(btn)
            self.pack_start(btn, False, False, 0)

        add_btn = Gtk.Button(label="+")
        add_btn.set_tooltip_text("Ajouter une couleur")
        add_btn.connect('clicked', self._on_add)
        self.pack_start(add_btn, False, False, 4)

        if len(self.color_buttons) > 2:
            rm_btn = Gtk.Button(label="−")
            rm_btn.set_tooltip_text("Supprimer la dernière couleur")
            rm_btn.connect('clicked', self._on_remove)
            self.pack_start(rm_btn, False, False, 0)

        self.show_all()

    def _on_add(self, button):
        colors = self.get_colors()
        colors.append(list(colors[-1]))  # duplique la dernière
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
```

**Step 2: Commit**

```bash
git add animation-speech.py
git commit -m "feat: widget GradientEditor pour édition du gradient"
```

---

### Task 4: Widget ConfigEditor

Le panneau d'édition principal avec preview live et tous les contrôles.

**Files:**
- Modify: `animation-speech.py` — insérer après `GradientEditor`, avant `class ConfigChooser`

**Step 1: Écrire la classe ConfigEditor**

C'est la pièce principale. Le widget est un `Gtk.Box` vertical scrollable contenant :
- Header (nom + bouton sauvegarder)
- Preview animé (DrawingArea ~600×120)
- Sections de contrôles regroupées par Frame

```python
class ConfigEditor(Gtk.Box):
    """Panneau d'édition de configuration avec preview live"""

    def __init__(self, config_dict, config_path=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.config = copy.deepcopy(config_dict)
        self.config_path = config_path
        self.preview = AnimationPreview.__new__(AnimationPreview)
        # Initialiser le preview manuellement avec notre config
        self.preview.config = copy.deepcopy(self.config)
        normalize_config_colors(self.preview.config)
        self.preview.config_path = config_path or ''
        self.preview.name = self.config.get('_name', 'Nouveau')
        self.preview.frame = 0
        self.preview.is_animating = True
        self.preview.audio_enabled = False
        self.preview.audio_level = 0.0
        bar_count = self.preview.config.get('animation', {}).get('bar_count', 20)
        self.preview.bars = [0.0] * bar_count
        self.preview.target_bars = [0.0] * bar_count
        self.preview.particles = []

        self._conditional_widgets = {}  # param_name -> widget to show/hide
        self._build_ui()

    def _build_ui(self):
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)

        # -- Header --
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = self.config.get('_name', os.path.basename(self.config_path or 'Nouveau'))
        self.header_label = Gtk.Label(label=f"Éditer : {name}")
        self.header_label.get_style_context().add_class('title-label')
        self.header_label.set_halign(Gtk.Align.START)
        header.pack_start(self.header_label, True, True, 0)

        save_btn = Gtk.Button(label="Enregistrer sous…")
        save_btn.connect('clicked', self._on_save)
        header.pack_end(save_btn, False, False, 0)
        self.pack_start(header, False, False, 0)

        # -- Preview --
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(-1, 120)
        self.drawing_area.connect('draw', self._on_draw_preview)
        self.pack_start(self.drawing_area, False, False, 4)

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

    # ─── Sections de contrôles ───────────────────────────

    def _build_type_section(self):
        frame = Gtk.Frame(label=" Type & Dimensions ")
        frame.get_label_widget().get_style_context().add_class('section-label')
        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        row = 0
        # Type d'animation
        grid.attach(Gtk.Label(label="Type", halign=Gtk.Align.END), 0, row, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        for t in VALID_ANIMATION_TYPES:
            self.type_combo.append_text(t)
        self.type_combo.set_active(list(VALID_ANIMATION_TYPES).index(
            self.config.get('animation_type', 'wave')))
        self.type_combo.connect('changed', self._on_type_changed)
        grid.attach(self.type_combo, 1, row, 2, 1)

        row += 1
        # Position
        grid.attach(Gtk.Label(label="Position", halign=Gtk.Align.END), 0, row, 1, 1)
        self.pos_combo = Gtk.ComboBoxText()
        for p in VALID_POSITIONS:
            self.pos_combo.append_text(p)
        cur_pos = self.config.get('position', 'bottom')
        if cur_pos in VALID_POSITIONS:
            self.pos_combo.set_active(list(VALID_POSITIONS).index(cur_pos))
        self.pos_combo.connect('changed', lambda c: self._update_config(
            'position', c.get_active_text()))
        grid.attach(self.pos_combo, 1, row, 2, 1)

        row += 1
        # Dimensions
        grid.attach(Gtk.Label(label="Largeur", halign=Gtk.Align.END), 0, row, 1, 1)
        self.width_spin = Gtk.SpinButton.new_with_range(50, 3000, 10)
        self.width_spin.set_value(self.config.get('width', 800))
        self.width_spin.connect('value-changed', lambda s: self._update_config(
            'width', int(s.get_value())))
        grid.attach(self.width_spin, 1, row, 1, 1)

        grid.attach(Gtk.Label(label="Hauteur", halign=Gtk.Align.END), 0, row + 1, 1, 1)
        self.height_spin = Gtk.SpinButton.new_with_range(20, 1000, 10)
        self.height_spin.set_value(self.config.get('height', 60))
        self.height_spin.connect('value-changed', lambda s: self._update_config(
            'height', int(s.get_value())))
        grid.attach(self.height_spin, 1, row + 1, 1, 1)

        frame.add(grid)
        return frame

    def _build_colors_section(self):
        frame = Gtk.Frame(label=" Couleurs ")
        frame.get_label_widget().get_style_context().add_class('section-label')
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(8)

        # Palettes
        palette_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        palette_box.pack_start(Gtk.Label(label="Palettes :", halign=Gtk.Align.START), False, False, 0)
        for name in COLOR_PALETTES:
            btn = Gtk.Button(label=name)
            btn.connect('clicked', self._on_palette_clicked, name)
            palette_box.pack_start(btn, False, False, 0)
        vbox.pack_start(palette_box, False, False, 0)

        # Primary & Secondary
        color_grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        colors = self.config.get('colors', {})

        color_grid.attach(Gtk.Label(label="Primary", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.primary_btn = self._make_color_button(
            colors.get('primary', [0.3, 0.8, 1.0, 0.9]),
            lambda rgba: self._update_color('primary', rgba))
        color_grid.attach(self.primary_btn, 1, 0, 1, 1)

        color_grid.attach(Gtk.Label(label="Secondary", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.secondary_btn = self._make_color_button(
            colors.get('secondary', [0.6, 0.4, 1.0, 0.7]),
            lambda rgba: self._update_color('secondary', rgba))
        color_grid.attach(self.secondary_btn, 1, 1, 1, 1)

        color_grid.attach(Gtk.Label(label="Background", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.bg_color_btn = self._make_color_button(
            colors.get('background', [0.0, 0.0, 0.0, 0.0]),
            lambda rgba: self._update_color('background', rgba))
        color_grid.attach(self.bg_color_btn, 1, 2, 1, 1)
        vbox.pack_start(color_grid, False, False, 0)

        # Gradient
        grad_label = Gtk.Label(label="Gradient :", halign=Gtk.Align.START)
        vbox.pack_start(grad_label, False, False, 0)
        gradient_colors = colors.get('gradient', [
            colors.get('primary', [0.3, 0.8, 1.0, 0.9]),
            colors.get('secondary', [0.6, 0.4, 1.0, 0.7]),
        ])
        self.gradient_editor = GradientEditor(gradient_colors, self._on_gradient_changed)
        vbox.pack_start(self.gradient_editor, False, False, 0)

        frame.add(vbox)
        return frame

    def _build_animation_section(self):
        frame = Gtk.Frame(label=" Animation ")
        frame.get_label_widget().get_style_context().add_class('section-label')
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        anim = self.config.get('animation', {})
        row = 0

        # FPS (toujours visible)
        row = self._add_slider_row(grid, row, "FPS", 'fps',
            anim.get('fps', 60), 10, 120, 1, 0)

        # Intensity (toujours visible)
        row = self._add_slider_row(grid, row, "Intensité", 'intensity',
            anim.get('intensity', 1.0), 0.1, 3.0, 0.1, 1)

        # Smoothing (toujours visible)
        row = self._add_slider_row(grid, row, "Smoothing", 'smoothing',
            anim.get('smoothing', 0.3), 0.0, 1.0, 0.05, 2)

        # Wave frequency (conditionnel)
        row = self._add_slider_row(grid, row, "Fréquence", 'wave_frequency',
            anim.get('wave_frequency', 3.0), 0.5, 10.0, 0.1, 1)

        # Bar count (conditionnel)
        row = self._add_slider_row(grid, row, "Nb barres", 'bar_count',
            anim.get('bar_count', 20), 5, 100, 1, 0)

        # Bar width (conditionnel)
        row = self._add_slider_row(grid, row, "Larg. barres", 'bar_width',
            anim.get('bar_width', 15), 1, 30, 1, 0)

        # Bar spacing (conditionnel)
        row = self._add_slider_row(grid, row, "Espacement", 'bar_spacing',
            anim.get('bar_spacing', 5), 0, 20, 1, 0)

        # Wave count (conditionnel)
        row = self._add_slider_row(grid, row, "Nb courbes", 'wave_count',
            anim.get('wave_count', 1), 1, 5, 1, 0)

        # Fill wave (conditionnel)
        fill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fill_check = Gtk.CheckButton(label="Remplissage courbe")
        fill_check.set_active(anim.get('fill_wave', False))
        fill_check.connect('toggled', lambda c: self._update_anim('fill_wave', c.get_active()))
        fill_box.pack_start(fill_check, False, False, 0)
        grid.attach(fill_box, 0, row, 3, 1)
        self._conditional_widgets.setdefault('fill_wave', []).append(fill_box)
        row += 1

        # Fill opacity (conditionnel)
        row = self._add_slider_row(grid, row, "Opacité remp.", 'fill_opacity',
            anim.get('fill_opacity', 0.3), 0.0, 1.0, 0.05, 2)

        frame.add(grid)
        return frame

    def _build_cartouche_section(self):
        frame = Gtk.Frame(label=" Cartouche (fond arrondi) ")
        frame.get_label_widget().get_style_context().add_class('section-label')
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        bg = self.config.get('background', {})
        row = 0

        check = Gtk.CheckButton(label="Activé")
        check.set_active(bg.get('enabled', False))
        check.connect('toggled', lambda c: self._update_bg('enabled', c.get_active()))
        grid.attach(check, 0, row, 3, 1)
        row += 1

        grid.attach(Gtk.Label(label="Couleur", halign=Gtk.Align.END), 0, row, 1, 1)
        self.cart_color_btn = self._make_color_button(
            bg.get('color', [0.2, 0.2, 0.25, 0.85]),
            lambda rgba: self._update_bg('color', [rgba.red, rgba.green, rgba.blue, rgba.alpha]))
        grid.attach(self.cart_color_btn, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label="Padding", halign=Gtk.Align.END), 0, row, 1, 1)
        pad_spin = Gtk.SpinButton.new_with_range(0, 30, 1)
        pad_spin.set_value(bg.get('padding', 10))
        pad_spin.connect('value-changed', lambda s: self._update_bg('padding', int(s.get_value())))
        grid.attach(pad_spin, 1, row, 1, 1)

        frame.add(grid)
        return frame

    def _build_audio_section(self):
        frame = Gtk.Frame(label=" Audio (microphone) ")
        frame.get_label_widget().get_style_context().add_class('section-label')
        grid = Gtk.Grid(column_spacing=8, row_spacing=4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)

        audio = self.config.get('audio', {})
        row = 0

        check = Gtk.CheckButton(label="Activé")
        check.set_active(audio.get('enabled', False))
        check.connect('toggled', lambda c: self._update_audio('enabled', c.get_active()))
        grid.attach(check, 0, row, 3, 1)
        row += 1

        grid.attach(Gtk.Label(label="Sensibilité", halign=Gtk.Align.END), 0, row, 1, 1)
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

    # ─── Helpers ─────────────────────────────────────────

    def _make_color_button(self, rgba_list, on_change):
        btn = Gtk.ColorButton()
        gdk_rgba = Gdk.RGBA()
        gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba_list
        btn.set_rgba(gdk_rgba)
        btn.set_use_alpha(True)
        btn.connect('color-set', lambda b: on_change(b.get_rgba()))
        return btn

    def _add_slider_row(self, grid, row, label, param_name, value, vmin, vmax, step, digits):
        """Ajoute une rangée label + scale + spin au grid. Retourne row+1."""
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

        self._link_scale_spin(scale, spin, lambda v: self._update_anim(param_name, v))

        # Enregistrer pour visibilité conditionnelle
        if param_name in PARAM_VISIBILITY:
            widgets = [lbl, scale, spin]
            self._conditional_widgets.setdefault(param_name, []).extend(widgets)

        return row + 1

    def _link_scale_spin(self, scale, spin, on_change):
        """Lie un Scale et un SpinButton bidirectionnellement"""
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

    # ─── Callbacks config ────────────────────────────────

    def _update_config(self, key, value):
        self.config[key] = value
        self._sync_preview()

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
        # Pas de sync preview pour l'audio (pas de micro dans le chooser)

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
        # Mettre à jour les boutons couleur
        self._set_color_button(self.primary_btn, palette['primary'])
        self._set_color_button(self.secondary_btn, palette['secondary'])
        self.gradient_editor.set_colors(palette['gradient'])
        self._sync_preview()

    def _on_type_changed(self, combo):
        anim_type = combo.get_active_text()
        self.config['animation_type'] = anim_type
        self._update_param_visibility(anim_type)
        self._sync_preview()

    def _set_color_button(self, btn, rgba_list):
        gdk_rgba = Gdk.RGBA()
        gdk_rgba.red, gdk_rgba.green, gdk_rgba.blue, gdk_rgba.alpha = rgba_list
        btn.set_rgba(gdk_rgba)

    def _update_param_visibility(self, anim_type):
        for param_name, widgets in self._conditional_widgets.items():
            visible = anim_type in PARAM_VISIBILITY.get(param_name, set())
            for w in widgets:
                w.set_visible(visible)

    def _sync_preview(self):
        self.preview.update_config(copy.deepcopy(self.config))

    def _on_draw_preview(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        self.preview.draw(cr, width, height)

    def update_tick(self):
        """Appelé par ConfigChooser à chaque frame"""
        self.preview.update()
        self.drawing_area.queue_draw()

    # ─── Sauvegarde ──────────────────────────────────────

    def _on_save(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Enregistrer la configuration",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT,
        )
        dialog.set_do_overwrite_confirmation(True)

        # Répertoire par défaut
        config_dir = os.path.expanduser('~/.config/animation-speech')
        os.makedirs(config_dir, exist_ok=True)
        dialog.set_current_folder(config_dir)

        # Nom suggéré
        anim_type = self.config.get('animation_type', 'wave')
        dialog.set_current_name(f"{anim_type}-custom.yaml")

        # Filtre YAML
        filt = Gtk.FileFilter()
        filt.set_name("Fichiers YAML")
        filt.add_pattern("*.yaml")
        filt.add_pattern("*.yml")
        dialog.add_filter(filt)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            if not path.endswith(('.yaml', '.yml')):
                path += '.yaml'
            self._write_yaml(path)
            self.header_label.set_text(f"✓ Sauvegardé → {path}")
            self.header_label.get_style_context().add_class('selected-label')

        dialog.destroy()

    def _write_yaml(self, path):
        """Écrit la config en YAML propre"""
        # Construire un dict propre (sans clés internes)
        out = {}
        out['animation_type'] = self.config.get('animation_type', 'wave')
        out['position'] = self.config.get('position', 'bottom')
        out['width'] = self.config.get('width', 800)
        out['height'] = self.config.get('height', 60)

        # Couleurs : convertir en hex pour lisibilité
        colors = self.config.get('colors', {})
        out['colors'] = {}
        for key in ('background', 'primary', 'secondary'):
            if key in colors:
                out['colors'][key] = self._rgba_to_hex(colors[key])
        if 'gradient' in colors:
            out['colors']['gradient'] = [self._rgba_to_hex(c) for c in colors['gradient']]

        # Background cartouche
        bg = self.config.get('background', {})
        if bg.get('enabled'):
            out['background'] = {
                'enabled': True,
                'color': self._rgba_to_hex(bg.get('color', [0.2, 0.2, 0.25, 0.85])),
                'padding': bg.get('padding', 10),
            }

        # Animation
        out['animation'] = {}
        anim = self.config.get('animation', {})
        for key in ('fps', 'smoothing', 'intensity', 'wave_frequency',
                     'bar_count', 'bar_width', 'bar_spacing',
                     'wave_count', 'fill_wave', 'fill_opacity'):
            if key in anim:
                out['animation'][key] = anim[key]

        # Audio
        audio = self.config.get('audio', {})
        if audio.get('enabled'):
            out['audio'] = {
                'enabled': True,
                'sensitivity': audio.get('sensitivity', 1.5),
                'smoothing': audio.get('smoothing', 0.3),
            }

        # Layer
        out['layer'] = {
            'layer': 'overlay',
            'exclusive_zone': 0,
            'margin': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
        }

        with open(path, 'w') as f:
            f.write(f"# Configuration animation-speech\n")
            f.write(f"# Générée par le sélecteur visuel\n\n")
            yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _rgba_to_hex(rgba_list):
        """Convertit [R,G,B,A] (0.0-1.0) en #RRGGBBAA"""
        r, g, b = int(rgba_list[0]*255), int(rgba_list[1]*255), int(rgba_list[2]*255)
        a = rgba_list[3] if len(rgba_list) > 3 else 1.0
        if abs(a - 1.0) < 0.01:
            return f"#{r:02x}{g:02x}{b:02x}"
        return f"#{r:02x}{g:02x}{b:02x}{int(a*255):02x}"

    def load_from_config(self, config_dict, config_path=None):
        """Charge une nouvelle config dans l'éditeur (appelé quand on clique sur une config dans la grille)"""
        self.config = copy.deepcopy(config_dict)
        self.config_path = config_path
        # Reconstruire l'UI
        for child in self.get_children():
            self.remove(child)
        self._conditional_widgets = {}
        # Réinitialiser le preview
        self.preview.update_config(copy.deepcopy(self.config))
        self._build_ui()
        # Appliquer la visibilité
        anim_type = self.config.get('animation_type', 'wave')
        self._update_param_visibility(anim_type)
        self.show_all()
        self._update_param_visibility(anim_type)
```

**Note importante :** il faut ajouter `import copy` en tête de fichier.

**Step 2: Ajouter l'import copy**

Ajouter `import copy` après `import shutil` (ligne 23).

**Step 3: Commit**

```bash
git add animation-speech.py
git commit -m "feat: widget ConfigEditor avec preview live et contrôles"
```

---

### Task 5: Refactoring de ConfigChooser (split panel)

Transformer `ConfigChooser` pour utiliser un `Gtk.Paned` avec la grille à gauche et `ConfigEditor` à droite.

**Files:**
- Modify: `animation-speech.py` — classe `ConfigChooser` (~ligne 1119+)

**Step 1: Réécrire `_setup_window` avec Gtk.Paned**

Remplacer la méthode `_setup_window` de `ConfigChooser` :

```python
def _setup_window(self):
    self.window = Gtk.Window(title="Sélecteur de configuration - animation-speech")
    self.window.set_default_size(1200, 700)
    self.window.connect('destroy', Gtk.main_quit)

    # Fond sombre + styles
    css = Gtk.CssProvider()
    css.load_from_data(b"""
        window { background-color: #1e1e2e; }
        label { color: #cdd6f4; font-size: 11px; }
        .title-label { color: #cdd6f4; font-size: 16px; font-weight: bold; }
        .section-label { color: #89b4fa; font-size: 12px; font-weight: bold; }
        .selected-label { color: #a6e3a1; font-weight: bold; }
        checkbutton label { color: #cdd6f4; font-size: 12px; }
        frame { border-color: #45475a; }
        frame > label { color: #89b4fa; }
        button { min-height: 28px; }
        spinbutton { min-width: 70px; }
    """)
    Gtk.StyleContext.add_provider_for_screen(
        self.window.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # Split panel
    self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    self.paned.set_position(420)

    # ─── Panneau gauche : grille ───
    left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    left_box.set_margin_top(12)
    left_box.set_margin_bottom(12)
    left_box.set_margin_start(12)
    left_box.set_margin_end(6)

    title = Gtk.Label(label="Configurations")
    title.get_style_context().add_class('title-label')
    left_box.pack_start(title, False, False, 0)

    # Info + checkbox
    info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    self.info_label = Gtk.Label(label=f"{len(self.previews)} configs")
    info_box.pack_start(self.info_label, False, False, 0)
    self.audio_check = Gtk.CheckButton(label="Audio")
    self.audio_check.set_active(False)
    self.audio_check.connect('toggled', self._on_audio_toggled)
    info_box.pack_start(self.audio_check, False, False, 0)
    left_box.pack_start(info_box, False, False, 0)

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
    new_btn = Gtk.Button(label="+ Nouveau")
    new_btn.connect('clicked', self._on_new_config)
    left_box.pack_start(new_btn, False, False, 0)

    self.paned.pack1(left_box, resize=False, shrink=False)

    # ─── Panneau droit : éditeur (vide au départ) ───
    self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.right_box.set_margin_top(12)
    self.right_box.set_margin_bottom(12)
    self.right_box.set_margin_start(6)
    self.right_box.set_margin_end(12)

    # Placeholder
    self.placeholder = Gtk.Label(label="← Cliquez sur une configuration\n   pour l'éditer")
    self.placeholder.set_halign(Gtk.Align.CENTER)
    self.placeholder.set_valign(Gtk.Align.CENTER)
    self.right_box.pack_start(self.placeholder, True, True, 0)

    self.editor = None
    self.paned.pack2(self.right_box, resize=True, shrink=False)

    self.window.add(self.paned)

    # Timer animation 30fps
    GLib.timeout_add(33, self._update_all)

    self.window.show_all()
```

**Step 2: Modifier `_on_click` pour ouvrir l'éditeur**

Remplacer `_on_click` :

```python
def _on_click(self, preview):
    """Charge la config sélectionnée dans l'éditeur"""
    with open(preview.config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    config_dict['_name'] = preview.name

    if self.editor is None:
        # Retirer le placeholder
        self.right_box.remove(self.placeholder)
        self.editor = ConfigEditor(config_dict, preview.config_path)
        self.right_box.pack_start(self.editor, True, True, 0)
        anim_type = config_dict.get('animation_type', 'wave')
        self.editor._update_param_visibility(anim_type)
        self.right_box.show_all()
        self.editor._update_param_visibility(anim_type)
    else:
        self.editor.load_from_config(config_dict, preview.config_path)
```

**Step 3: Ajouter `_on_new_config`**

```python
def _on_new_config(self, button):
    """Crée une config vierge dans l'éditeur"""
    default_config = {
        '_name': 'Nouveau',
        'animation_type': 'wave',
        'position': 'bottom',
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
    }

    if self.editor is None:
        self.right_box.remove(self.placeholder)
        self.editor = ConfigEditor(default_config)
        self.right_box.pack_start(self.editor, True, True, 0)
        self.editor._update_param_visibility('wave')
        self.right_box.show_all()
        self.editor._update_param_visibility('wave')
    else:
        self.editor.load_from_config(default_config)
```

**Step 4: Mettre à jour `_update_all` pour inclure l'éditeur**

```python
def _update_all(self):
    for preview in self.previews:
        preview.update()
    self.flowbox.queue_draw()
    if self.editor is not None:
        self.editor.update_tick()
    return True
```

**Step 5: Réduire CELL_WIDTH pour le panneau rétréci**

Modifier les constantes de la classe :
```python
CELL_WIDTH = 180
CELL_HEIGHT = 80
LABEL_HEIGHT = 20
```

**Step 6: Commit**

```bash
git add animation-speech.py
git commit -m "feat: ConfigChooser split panel avec éditeur intégré"
```

---

### Task 6: Tests manuels et ajustements

**Step 1: Lancer et tester**

```bash
cd /home/rapha/SOURCES/RAPHA_STT/animation-speech
./animation-speech.py --choose
```

Vérifier :
- [ ] La grille s'affiche à gauche avec les previews animés
- [ ] Cliquer sur une config ouvre le panneau d'édition à droite
- [ ] Le preview live dans l'éditeur s'anime
- [ ] Changer le type d'animation masque/affiche les bons paramètres
- [ ] Les sliders mettent à jour le preview en temps réel
- [ ] Les color pickers fonctionnent
- [ ] Les palettes appliquent les bonnes couleurs
- [ ] Le gradient editor ajoute/supprime des stops
- [ ] Le bouton "Nouveau" crée une config vierge
- [ ] "Enregistrer sous…" ouvre le dialogue et sauve un YAML valide
- [ ] Le YAML sauvé peut être rechargé : `./animation-speech.py <fichier-sauvé>`

**Step 2: Corriger les bugs trouvés**

**Step 3: Commit final**

```bash
git add animation-speech.py
git commit -m "fix: ajustements éditeur de configuration"
```

---

## Ordre des dépendances

```
Task 1 (update_config) ──┐
Task 2 (constantes)   ───┼──→ Task 3 (GradientEditor) ──→ Task 4 (ConfigEditor) ──→ Task 5 (ConfigChooser refactor) ──→ Task 6 (tests)
                          │
                          └──→ (palettes utilisées par Task 4)
```

## Risques identifiés

1. **Performance** : beaucoup de previews animés + l'éditeur — surveiller le CPU à 30fps
2. **GTK3 styling** : le CSS GTK3 est limité, les Frames/Grids peuvent avoir un look austère
3. **Taille du fichier** : `animation-speech.py` est déjà ~1575 lignes, on ajoute ~500 lignes — acceptable mais à surveiller
