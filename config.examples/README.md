# Exemples de configurations pour l'animation de parole

Ces fichiers de configuration YAML définissent différents styles visuels pour l'animation.

## 🎨 Configurations Monochromes (Style image)

### monochrome-bw.yaml
**Style:** Noir et blanc élégant, inspiré de l'image de forme d'onde
- Animation: Onde
- Position: Centre
- Dimensions: 1200x150px
- Couleurs: Noir profond (#1A1A1A) et gris foncé (#4D4D4D)
- Intensité: Moyenne-haute (1.2)
- **Idéal pour:** Enregistrements professionnels, style minimaliste

### grayscale-elegant.yaml
**Style:** Dégradé subtil de gris
- Animation: Onde
- Position: Bas de l'écran
- Dimensions: 1000x80px
- Couleurs: Gris anthracite (#333) et gris moyen (#808080)
- Intensité: Douce (0.9)
- **Idéal pour:** Style épuré et discret

## ⚡ Configurations Dynamiques

### wave-energetic.yaml
**Style:** Onde énergique et dynamique
- Animation: Onde
- Position: Centre
- Dimensions: 1400x120px
- Couleurs: Noir pur (#000) et gris (#595959)
- Intensité: Forte (1.8)
- **Idéal pour:** Présentations, contenus dynamiques

### wave-subtle.yaml
**Style:** Onde subtile et discrète
- Animation: Onde
- Position: Haut de l'écran
- Dimensions: 900x50px
- Couleurs: Gris clair semi-transparent
- Intensité: Faible (0.6)
- **Idéal pour:** Ne pas distraire, arrière-plan discret

## 🎵 Configurations Égaliseur

### equalizer-minimal.yaml
**Style:** Barres simples et épurées
- Animation: Égaliseur
- Position: Bas de l'écran
- Dimensions: 600x100px
- Barres: 30 barres de 12px (espacement 8px)
- Couleurs: Noir profond et gris foncé
- **Idéal pour:** Style rétro, lecteur audio

### equalizer-thin.yaml
**Style:** Barres fines et nombreuses
- Animation: Égaliseur
- Position: Bas de l'écran
- Dimensions: 1000x80px
- Barres: 60 barres de 8px (espacement 4px)
- Couleurs: Noir doux et gris moyen
- **Idéal pour:** Effet détaillé, analyse spectrale

## ✨ Configurations Particules

### particles-scattered.yaml
**Style:** Particules dispersées (comme l'image)
- Animation: Particules
- Position: Centre
- Dimensions: 800x300px
- Couleurs: Noir légèrement transparent et gris
- Intensité: Forte (1.5)
- **Idéal pour:** Effet artistique, style moderne

### particles.yaml (original)
**Style:** Particules colorées
- Animation: Particules
- Position: Centre
- Dimensions: 400x400px
- Couleurs: Rose et violet
- **Idéal pour:** Style ludique et coloré

## 🔄 Configurations Circulaires

### circular.yaml (original)
**Style:** Ondes circulaires concentriques
- Animation: Circulaire
- Position: Coin supérieur droit
- Dimensions: 200x200px
- Couleurs: Cyan et magenta
- **Idéal pour:** Indicateur compact, effet radar

### wave.yaml (original)
**Style:** Onde sobre bleue/violette
- Animation: Onde
- Position: Bas
- Dimensions: 800x60px
- Couleurs: Bleu clair et violet
- **Idéal pour:** Couleurs douces, usage général

### test-hex-colors.yaml
**Style:** Config de test pour le support multi-format de couleurs
- Animation: Soundwave
- Position: Bas
- Dimensions: 800x80px
- Couleurs: Dégradé Catppuccin en format hex + mélange avec tableau floats
- **Idéal pour:** Valider que les formats hex et les tableaux cohabitent

## 🚀 Utilisation

### Utiliser une configuration dans le script
Modifiez la ligne 79 de `audio2ts2pdf.sh`:

```bash
# Remplacer:
python3 ~/SOURCES/animation-speech/animation_speech.py ~/SOURCES/animation-speech/config.yaml -p center -w 1000 -H 100 &

# Par (exemple avec monochrome-bw):
python3 ~/SOURCES/animation-speech/animation_speech.py ~/SOURCES/animation-speech/config.examples/monochrome-bw.yaml &
```

**Note:** Quand vous utilisez un fichier de config complet, vous n'avez pas besoin des options `-p`, `-w`, `-H` car tout est défini dans le fichier.

### Tester une configuration manuellement

```bash
# Naviguer vers le dossier
cd ~/SOURCES/animation-speech

# Lancer avec une config spécifique
python3 animation-speech.py config.examples/monochrome-bw.yaml

# Dans un autre terminal, récupérer le PID et démarrer
kill -SIGUSR1 <PID>

# Arrêter
kill -SIGUSR2 <PID>
```

### Personnaliser une configuration

1. Copier un fichier exemple:
```bash
cp config.examples/monochrome-bw.yaml my-custom-config.yaml
```

2. Éditer les valeurs:
```yaml
width: 1200          # Largeur en pixels
height: 150          # Hauteur en pixels
position: center     # top, bottom, left, right, center, top-left, etc.
colors:
  primary: "#ED8796"               # Format hex (recommandé)
  secondary: "#8AADF4F2"           # Hex avec alpha
animation:
  fps: 60            # Images par seconde
  intensity: 1.2     # Multiplicateur d'amplitude
  smoothing: 0.25    # Interpolation (0-1, plus = plus lisse)
```

3. Utiliser votre config:
```bash
python3 animation-speech.py my-custom-config.yaml
```

## 🎨 Guide des couleurs

Les couleurs supportent **plusieurs formats**, utilisables librement et même mélangés dans un même fichier :

### Format hex (recommandé)

```yaml
colors:
  background: "#00000000"          # Transparent (#RRGGBBAA)
  primary: "#ED8796"               # Rouge Catppuccin (#RRGGBB, alpha=1.0)
  secondary: "#f5a97fF2"           # Peach avec alpha 0.95 (#RRGGBBAA)
  gradient:
    - "#ED8796F2"                  # Red
    - "#EED49FF2"                  # Yellow
    - "#A6DA95F2"                  # Green
    - "#F00"                       # Rouge vif (#RGB court, alpha=1.0)
```

| Format | Exemple | Alpha |
|--------|---------|-------|
| `#RRGGBB` | `"#ED8796"` | 1.0 par défaut |
| `#RRGGBBAA` | `"#ED8796F2"` | Inclus (F2 = 0.95) |
| `#RGB` | `"#F00"` | 1.0 par défaut |

### Format tableau floats (historique)

```yaml
colors:
  primary: [0.93, 0.53, 0.59, 0.95]    # [R, G, B, A] de 0.0 à 1.0
  secondary: [0.6, 0.4, 1.0]           # [R, G, B] → alpha=1.0
```

### Mélange des formats

Les deux formats cohabitent dans un même fichier :

```yaml
colors:
  background: "#00000000"                  # Hex
  primary: "#ED8796"                       # Hex
  gradient:
    - "#A6DA95F2"                          # Hex
    - [0.55, 0.84, 0.79, 0.95]            # Tableau floats
```

### Exemples de couleurs courantes

```yaml
# Hex                         # Tableau floats équivalent
"#000000"                     # [0.0, 0.0, 0.0, 1.0]     Noir opaque
"#FFFFFF"                     # [1.0, 1.0, 1.0, 1.0]     Blanc opaque
"#808080CC"                   # [0.5, 0.5, 0.5, 0.8]     Gris semi-transparent
"#FF0000E6"                   # [1.0, 0.0, 0.0, 0.9]     Rouge
"#00FF00E6"                   # [0.0, 1.0, 0.0, 0.9]     Vert
"#0000FFE6"                   # [0.0, 0.0, 1.0, 0.9]     Bleu
"#00000000"                   # [0.0, 0.0, 0.0, 0.0]     Transparent total
```

### Conversion alpha hex ↔ décimal

| Alpha | Hex | Décimal |
|-------|-----|---------|
| 100%  | `FF` | 1.0   |
| 95%   | `F2` | 0.95  |
| 90%   | `E6` | 0.9   |
| 80%   | `CC` | 0.8   |
| 70%   | `B3` | 0.7   |
| 50%   | `80` | 0.5   |
| 0%    | `00` | 0.0   |

## 📐 Guide des positions

- `bottom`: Bas de l'écran (pleine largeur)
- `top`: Haut de l'écran (pleine largeur)
- `left`: Gauche de l'écran (pleine hauteur)
- `right`: Droite de l'écran (pleine hauteur)
- `center`: Centre de l'écran (taille définie)
- `top-left`, `top-right`, `bottom-left`, `bottom-right`: Coins

## 💡 Conseils

### Pour un style comme l'image montrée:
- Utilisez `monochrome-bw.yaml` ou `particles-scattered.yaml`
- Privilégiez les couleurs noir/gris
- Réglez `intensity` entre 1.0 et 1.5
- Utilisez `position: center` pour centrer l'animation

### Pour ne pas distraire:
- Utilisez `wave-subtle.yaml`
- Réduisez `intensity` (0.5-0.8)
- Augmentez `smoothing` (0.3-0.5)
- Utilisez des couleurs claires et transparentes

### Pour un effet spectaculaire:
- Utilisez `wave-energetic.yaml`
- Augmentez `intensity` (1.5-2.0)
- Réduisez `smoothing` (0.1-0.2)
- Augmentez `fps` à 60

### Optimisation des performances:
- Réduisez `fps` à 30 pour moins de charge CPU
- Réduisez `width` et `height` pour moins de calculs
- Pour l'égaliseur, réduisez `bar_count`

## 📝 Structure complète d'un fichier de configuration

```yaml
# Type d'animation: equalizer, wave, circular, particles, soundwave,
#                   soundwave-curve, circular-wave, circular-bars
animation_type: wave

# Position: bottom, top, left, right, center, top-left, etc.
position: center

# Dimensions en pixels
width: 1000
height: 100

# Couleurs — format hex ou tableau floats, mélange possible
colors:
  background: "#00000000"            # Fond (généralement transparent)
  primary: "#ED8796"                 # Couleur principale
  secondary: "#8AADF4B3"            # Couleur secondaire avec alpha
  gradient:                          # Dégradé optionnel (2+ couleurs)
    - "#ED8796F2"
    - "#EED49FF2"
    - "#A6DA95F2"

# Cartouche de fond (optionnel)
background:
  enabled: true
  color: "#33333AD9"                 # Couleur du cartouche
  padding: 10

# Paramètres d'animation
animation:
  fps: 60                  # Images par seconde
  bar_count: 20            # Nombre de barres (equalizer, soundwave, circular-bars)
  bar_width: 15            # Largeur des barres (circular-bars)
  bars_rotation: 0         # Rotation en degrés (circular-bars, 0-360)
  bar_spacing: 5           # Espacement entre barres (equalizer, soundwave)
  smoothing: 0.3           # Interpolation (0-1)
  intensity: 1.0           # Multiplicateur d'amplitude
  wave_frequency: 2.0      # Fréquence des ondes
  circle_count: 12         # Nombre de cercles (circular)
  circle_speed: 2.0        # Vitesse des cercles (circular)
  circle_direction: outward # outward, inward, ping-pong (circular)
  wave_count: 1            # Nombre de courbes (wave, soundwave-curve)
  fill_wave: false         # Remplir les courbes (wave, soundwave-curve)
  fill_opacity: 0.3        # Opacité du remplissage

# Cartouche de fond (optionnel)
background:
  enabled: true
  color: "#33333AD9"
  padding: 10
  border_width: 0
  border_color: "#FFFFFF80"

# Modulation audio (optionnel)
audio:
  enabled: false
  sensitivity: 1.5
  smoothing: 0.3

# Signaux UNIX pour le contrôle
signals:
  start: SIGUSR1
  stop: SIGUSR2

# Configuration layer shell (Wayland)
layer:
  layer: overlay           # overlay = au-dessus de tout
  exclusive_zone: 0        # Pixels réservés (0 = aucun)
  margin:
    top: 0                 # Marge depuis le haut
    bottom: 0              # Marge depuis le bas
    left: 0                # Marge depuis la gauche
    right: 0               # Marge depuis la droite
```

## 🐛 Dépannage

### L'animation ne s'affiche pas
- Vérifiez que vous êtes sur Wayland: `echo $XDG_SESSION_TYPE`
- Vérifiez que gtk-layer-shell est installé
- Testez avec `position: center` au lieu d'ancrer aux bords

### L'animation est saccadée
- Réduisez `fps` à 30
- Réduisez les dimensions (`width`, `height`)
- Augmentez `smoothing` à 0.4-0.5

### L'animation est trop discrète
- Augmentez `intensity` (1.5-2.0)
- Augmentez l'opacité des couleurs (alpha hex `F2`/`FF` ou dernier nombre du tableau)
- Réduisez `smoothing` (0.1-0.2)

### L'animation est trop envahissante
- Réduisez `intensity` (0.5-0.8)
- Réduisez l'opacité des couleurs (alpha hex `80`/`B3`)
- Augmentez `smoothing` (0.4-0.5)
- Utilisez des couleurs plus claires
