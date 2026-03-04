# Design : Éditeur de configuration intégré à --choose

**Date** : 2026-03-03
**Statut** : En attente d'approbation

## Objectif

Transformer le sélecteur `--choose` (actuellement read-only) en un éditeur de configuration complet avec preview live, permettant de créer et modifier des configs sans toucher au YAML.

## Layout : Split panel

```
┌──────────────────────────────────────────────────────────┐
│  Sélecteur de configuration - animation-speech           │
│──────────────────────────────────────────────────────────│
│  Grille configs    │   Éditer: wave-catppuccin           │
│  ┌───┐┌───┐┌───┐  │  ┌──────────────────────────────┐   │
│  │ ▶ ││ ▶ ││ ▶ │  │  │     Preview live (grand)     │   │
│  └───┘└───┘└───┘  │  └──────────────────────────────┘   │
│  ┌───┐┌───┐┌───┐  │  Type: [wave v] Position: [bottom]  │
│  │ ▶ ││ ▶ ││ ▶ │  │  Palettes: [Catppuccin][Rainbow]…  │
│  └───┘└───┘└───┘  │  Primary: [■]  Secondary: [■]       │
│  ┌───┐┌───┐┌───┐  │  Gradient: [■][■][■][■] [+][-]     │
│  │ ▶ ││ ▶ ││ ▶ │  │  Freq: ──●── [3.0]                 │
│  └───┘└───┘└───┘  │  Intensity: ─●── [0.8]              │
│                    │  Cartouche: [✓] Padding: [10]       │
│  [+ Nouveau]       │          [Enregistrer sous...]      │
│  [✓ Audio uniq.]   │                                     │
└──────────────────────────────────────────────────────────┘
```

- Fenêtre unique avec `Gtk.Paned` horizontal
- Gauche : grille FlowBox (rétrécie, ~3 colonnes) + bouton "Nouveau" + checkbox "Audio uniquement"
- Droite : panneau d'édition avec preview live + contrôles (caché tant qu'aucune config n'est sélectionnée)

## Nouvelles classes

### `ConfigEditor(Gtk.Box)`
Widget vertical scrollable contenant :
1. **Header** : nom de la config + bouton "Enregistrer sous..."
2. **Preview** : `AnimationPreview` en grand format (~600×120), animé à 30fps
3. **Sections de contrôles** regroupées par catégorie (voir ci-dessous)

### `GradientEditor(Gtk.Box)`
Widget horizontal pour éditer les stops du gradient :
- Rangée de `Gtk.ColorButton` (un par stop)
- Bouton [+] pour ajouter un stop
- Bouton [-] pour supprimer le dernier stop

### `ColorPaletteSelector(Gtk.FlowBox)`
Widget avec boutons pour appliquer des palettes prédéfinies d'un clic.

## Sections de contrôles

### Type & Position
- `animation_type` : ComboBox (wave, equalizer, circular, particles, soundwave, soundwave-curve, circular-wave, circular-bars)
- `position` : ComboBox (bottom, top, center, left, right, top-left, top-right, bottom-left, bottom-right)
- `width`, `height` : SpinButtons

### Couleurs
- **Palettes prédéfinies** : boutons qui appliquent un jeu complet (primary + secondary + gradient)
  - Catppuccin Macchiato (7 stops)
  - Rainbow (7 stops arc-en-ciel)
  - Neon (4 stops cyan/vert/magenta/jaune)
  - Monochrome (blanc → gris)
  - Grayscale Elegant (dégradé gris subtil)
- `primary` : Gtk.ColorButton avec alpha
- `secondary` : Gtk.ColorButton avec alpha
- `gradient` : GradientEditor (ColorButtons + ajouter/supprimer)

### Animation
- `fps` : Scale + SpinButton (10-120, défaut 60)
- `wave_frequency` : Scale + SpinButton (0.5-10.0, défaut 3.0)
- `intensity` : Scale + SpinButton (0.1-3.0, défaut 1.0)
- `smoothing` : Scale + SpinButton (0.0-1.0, défaut 0.3)
- `bar_count` : Scale + SpinButton (5-100, défaut 20) — visible seulement pour equalizer/soundwave/circular-bars
- `bar_width` : Scale + SpinButton (1-30, défaut 15) — idem
- `bar_spacing` : Scale + SpinButton (0-20, défaut 5) — idem
- `wave_count` : Scale + SpinButton (1-5, défaut 1) — visible seulement pour wave/soundwave-curve
- `fill_wave` : CheckButton — visible seulement pour wave/soundwave-curve
- `fill_opacity` : Scale + SpinButton (0.0-1.0) — visible si fill_wave activé

### Cartouche (fond arrondi)
- `enabled` : CheckButton
- `color` : Gtk.ColorButton avec alpha
- `padding` : Scale + SpinButton (0-30, défaut 10)

### Audio
- `enabled` : CheckButton
- `sensitivity` : Scale + SpinButton (0.1-5.0, défaut 1.5)
- `smoothing` : Scale + SpinButton (0.0-1.0, défaut 0.3)

## Affichage conditionnel

Les paramètres sont masqués/affichés selon le type d'animation sélectionné :

| Paramètre | wave | eq | circ | part | sw | sw-c | cw | cb |
|-----------|------|-----|------|------|----|------|----|----|
| wave_frequency | ✓ | | ✓ | | | ✓ | ✓ | ✓ |
| bar_count | | ✓ | | | ✓ | | | ✓ |
| bar_width | | ✓ | | | ✓ | | | ✓ |
| bar_spacing | | ✓ | | | ✓ | | | |
| wave_count | ✓ | | | | | ✓ | | |
| fill_wave | ✓ | | | | | ✓ | | |
| fill_opacity | ✓ | | | | | ✓ | | |

## Palettes prédéfinies

| Nom | Primary | Secondary | Gradient |
|-----|---------|-----------|----------|
| Catppuccin | #ED8796 | #8BD5CA | 7 stops Macchiato |
| Rainbow | #FF004D | #7028FF | 7 stops arc-en-ciel |
| Neon | #00FF88 | #FF00FF | 4 stops cyan/vert/magenta/jaune |
| Monochrome | #FFFFFF | #888888 | Blanc → Gris |
| Grayscale | #CCCCCC | #666666 | Dégradé gris subtil |

## Preview live

- Réutilise `AnimationPreview` existant en grand format
- Nouvelle méthode `update_config(config_dict)` pour mettre à jour la config à la volée
- Chaque changement de contrôle → reconstruit le dict config → appelle `update_config()` → le preview reflète instantanément
- Timer 30fps déjà en place dans ConfigChooser

## Sauvegarde

- Bouton "Enregistrer sous..." ouvre `Gtk.FileChooserDialog` en mode SAVE
- Répertoire par défaut : `~/.config/animation-speech/`
- Nom suggéré : `{type}-{palette}-custom.yaml`
- Format YAML propre avec commentaires explicatifs
- Filtre fichier : `*.yaml`

## Bouton "Nouveau"

- Dans la grille (panneau gauche), sous les previews
- Ouvre le panneau d'édition avec une config par défaut :
  - Type: wave, Position: bottom, 800×60
  - Couleurs: Catppuccin
  - Cartouche: activé
  - Audio: désactivé

## Modifications aux classes existantes

### `ConfigChooser`
- Layout : `Gtk.Paned` horizontal au lieu du simple VBox
- Panneau gauche : grille existante (réduite) + bouton Nouveau + checkbox Audio
- Panneau droit : `ConfigEditor` (caché initialement, affiché au clic)
- Le clic sur une config ne copie plus directement — il ouvre l'éditeur
- La fenêtre par défaut s'agrandit (~1200×700)

### `AnimationPreview`
- Nouvelle méthode `update_config(config_dict)` : met à jour `self.config`, réinitialise les états (bars, particles)

## Thème visuel

Style cohérent avec l'existant (fond sombre Catppuccin) :
- Fond : #1e1e2e
- Texte : #cdd6f4
- Accents : #a6e3a1 (sélection), #89b4fa (liens/boutons)
- Sections avec séparateurs et labels en gras
