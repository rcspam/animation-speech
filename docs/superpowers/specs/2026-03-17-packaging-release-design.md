# Design — Paquets .deb, .rpm et .tar.gz pour la release v1.2.0

## Objectif

Fournir des paquets d'installation prêts à l'emploi (.deb, .rpm, .tar.gz) en assets de la release GitHub v1.2.0, avec des dépendances correctes et complètes.

## Artefacts produits

| Format | Fichier | Cible |
|--------|---------|-------|
| Debian | `animation-speech_1.2.0_all.deb` | Debian, Ubuntu, Mint |
| RPM | `animation-speech-1.2.0-1.noarch.rpm` | Fedora, openSUSE |
| Tarball | `animation-speech-1.2.0.tar.gz` | Toute distro (install.sh) |

## Dépendances complètes

### Imports Python analysés

- `gi` (PyGObject) — GTK3, GLib, Gdk, GObject, GtkLayerShell
- `cairo` (pycairo via gi) — dessin animations
- `yaml` (PyYAML) — config
- `pyaudio` — optionnel, modulation micro (try/except)
- stdlib : argparse, copy, gettext, math, os, random, signal, struct, subprocess, sys, tempfile, threading, time, traceback

### Commandes externes runtime

- `pactl` — détection mute micro (fallback amixer)
- `amixer` — fallback ALSA si pas de pactl
- `qdbus6` — déplacement fenêtre KDE (try/except, optionnel)
- `gdbus` — déplacement fenêtre GNOME (try/except, optionnel)
- `pgrep` — animation-speech-ctl : recherche PID
- `gettext` (commande shell) — i18n dans animation-speech-ctl

### Tableau des dépendances par paquet

| Composant | .deb (Depends) | RPM Fedora (Requires) | RPM openSUSE (Requires) |
|---|---|---|---|
| Python 3 | `python3` | `python3` | `python3` |
| PyGObject | `python3-gi` | `python3-gobject` | `python3-gobject` |
| Cairo bindings | `python3-gi-cairo` | `python3-gobject-cairo` | `python3-gobject-cairo` |
| GTK3 | `gir1.2-gtk-3.0` | `gtk3` | `gtk3` |
| PyYAML | `python3-yaml` | `python3-pyyaml` | `python3-PyYAML` |
| layer-shell lib | `libgtk-layer-shell0` | `gtk-layer-shell` | `gtk-layer-shell` |
| layer-shell typelib | `gir1.2-gtklayershell-0.1` | (inclus dans gtk-layer-shell) | `typelib-1_0-GtkLayerShell-0_1` |
| pgrep | `procps` | `procps-ng` | `procps` |
| gettext (shell) | `gettext-base` | `gettext` | `gettext-runtime` |

| Composant | .deb (Recommends) | RPM (Recommends) |
|---|---|---|
| PyAudio | `python3-pyaudio` | `python3-pyaudio` / `python3-PyAudio` (suse) |
| pactl | `pulseaudio-utils \| pipewire-pulse` | `pulseaudio-utils` |
| amixer | `alsa-utils` | `alsa-utils` |

## Fichiers à créer/modifier

### 1. `animation-speech.spec` (nouveau)

Fichier RPM spec universel Fedora + openSUSE :
- Conditionnel `%if 0%{?suse_version}` pour les noms de paquets openSUSE
- Construction zipapp identique au .deb
- Installation dans `/usr/bin/`, `/usr/share/animation-speech/`, `/usr/share/locale/`
- `%post` : message d'usage
- `%postun` : nettoyage PID file

### 2. `debian/build-deb.sh` (modifié)

- Ajouter `procps, gettext-base` aux Depends
- Ajouter `Recommends: python3-pyaudio, pulseaudio-utils | pipewire-pulse, alsa-utils`
- Supprimer le `read -p` interactif à la fin

### 3. `Makefile` (modifié)

Nouvelles cibles :
- `make deb` — appelle `debian/build-deb.sh`
- `make rpm` — `rpmbuild -bb` avec le .spec
- `make release` — construit tout + `gh release upload v1.2.0`

## Post-install / Post-remove

- **postinst/post** : affiche les instructions d'usage
- **postrm/postun** : supprime le PID file `${XDG_RUNTIME_DIR}/speech-animation.pid`
- Pas de service systemd, pas de cache à reconstruire
