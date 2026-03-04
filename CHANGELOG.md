# Changelog

## v1.2.0 — 22 février 2026

### Refactoring majeur (audit de code)

✅ **Classe mixin `AnimationDrawMixin`**
- Extraction de ~500 lignes dupliquées entre `SpeechAnimation` et `AnimationPreview`
- Les 15 méthodes de dessin sont maintenant partagées via héritage
- Méthode `dispatch_draw()` centralise l'aiguillage par type d'animation
- Paramètre `num_points` pour les méthodes à résolution variable (wave, soundwave-curve, circular-wave)

✅ **Bugs corrigés**
- Variables mortes `primary`/`secondary` supprimées de `draw_equalizer` et `draw_soundwave`
- Défauts incohérents dans `_get_content_bounds` pour soundwave (20 barres→60 barres)
- `except:` nu → `except Exception:` dans `display_available_configs`
- `sys.exit(0)` dans signal handler → `GLib.idle_add(Gtk.main_quit)`
- `apply_cli_overrides` : `width`/`height` utilisent `is not None` (valeur 0 correctement traitée)
- `stop_audio_capture` : nettoyage de `self.audio_thread = None`

✅ **Améliorations**
- Validation du type d'animation au chargement (avertissement + fallback `wave`)
- Constante `VALID_ANIMATION_TYPES` pour les 8 types
- Méthodes utilitaires dans le mixin : `_get_audio_boost()`, `_has_gradient()`, `_interpolate_primary_secondary()`
- Imports `shutil` et `traceback` déplacés en tête de fichier

✅ **Nettoyage**
- Section `signals` inutilisée supprimée de `config.yaml`
- Commentaire types d'animation mis à jour (8 types)
- Fichiers hors-sujet supprimés : `ttt.sh`, `audio2ts2pdf.sh`, `audio2ts2pdf_robust.sh`, `setup_hf_token.sh`

✅ **Paquet Debian 1.2.0**
- Version bump 1.1.0 → 1.2.0
- Description complète (8 types + sélecteur `--choose`)
- Configs sous-répertoires (`no-audio/`, `kurve-*`) incluses via `cp -r`

## v1.1.0 — 16 février 2026

### Paquet Debian et nouvelles animations

✅ **Paquet Debian** (`animation-speech_1.1.0_all.deb`)
- Script de build `debian/build-deb.sh`
- Script de contrôle `animation-speech-ctl`

✅ **Nouveaux types d'animation**
- `soundwave` : Barres verticales style forme d'onde audio
- `soundwave-curve` : Forme d'onde symétrique avec courbes lisses
- `circular-wave` : Cercle ondulant
- `circular-bars` : Barres radiales

✅ **Modulation audio**
- Capture microphone via PyAudio (optionnel)
- Paramètres `-a`, `--sensitivity`
- Section `audio:` dans les configs YAML

✅ **Cartouche (fond arrondi)**
- Fond capsule semi-transparent optionnel
- Paramètres `--bg`, `--no-bg`, `--bg-opacity`

✅ **Sélecteur visuel** (`--choose`)
- Aperçus animés en grille
- Filtre par nom, checkbox audio
- Copie la config sélectionnée dans `~/.config/animation-speech/`

✅ **Couleurs multi-format**
- Hex (`#ED8796`, `#ED8796F2`), hex court (`#F00`), tableaux floats
- Gradients multi-couleurs

## v1.0.0 — 30 janvier 2025

### Version initiale

✅ **Fonctionnalités de base**
- Animation configurable via YAML
- Contrôle par signaux UNIX (SIGUSR1/SIGUSR2)
- 4 types d'animations : wave, equalizer, circular, particles
- Position et dimensions configurables
- Overlay Wayland via gtk-layer-shell
- Fichier PID pour le contrôle
- Scripts control.sh et stop.sh
