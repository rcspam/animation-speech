#!/bin/bash
# Script de création du paquet .deb pour animation-speech
# Usage: ./build-deb.sh

set -e

VERSION="1.2.0"
PACKAGE="animation-speech"
ARCH="all"
BUILD_DIR="build"
PACKAGE_DIR="${BUILD_DIR}/${PACKAGE}_${VERSION}_${ARCH}"

# Répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Construction du paquet ${PACKAGE}_${VERSION}_${ARCH}.deb ==="
echo ""

# Nettoyage
echo "Nettoyage..."
rm -rf "${SCRIPT_DIR}/${BUILD_DIR}"

# Création de la structure
echo "Création de la structure du paquet..."
mkdir -p "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN"
mkdir -p "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/bin"
mkdir -p "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/${PACKAGE}"
mkdir -p "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/${PACKAGE}/config.examples"

# Fichier control
echo "Création du fichier control..."
cat > "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN/control" << 'EOF'
Package: animation-speech
Version: 1.2.0
Section: graphics
Priority: optional
Architecture: all
Depends: python3, python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, python3-yaml, libgtk-layer-shell0, gir1.2-gtklayershell-0.1
Recommends: python3-pyaudio
Maintainer: Rapha <rapha@local>
Description: Animation de parole pour Wayland
 Overlay transparent configurable qui affiche une animation
 lors de la parole. Utilise GTK3 et gtk-layer-shell pour
 s'afficher au-dessus des autres fenetres sous Wayland.
 Controle par signaux UNIX (SIGUSR1/SIGUSR2).
 Supporte la modulation par microphone (necessite python3-pyaudio).
 Types: wave, equalizer, circular, particles, soundwave,
 soundwave-curve, circular-wave, circular-bars.
 Selecteur visuel interactif avec --choose.
Homepage: https://github.com/rapha/animation-speech
EOF

# Script postinst
echo "Création du script postinst..."
cat > "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Créer le répertoire de configuration utilisateur si nécessaire
echo "Installation terminée."
echo ""
echo "Usage:"
echo "  animation-speech              # Lancer avec config par défaut"
echo "  animation-speech --choose     # Sélecteur visuel interactif"
echo "  animation-speech --list       # Lister les configs disponibles"
echo "  animation-speech <config>     # Lancer avec une config spécifique"
echo ""
echo "Contrôle:"
echo "  animation-speech-ctl start    # Démarrer l'animation"
echo "  animation-speech-ctl stop     # Arrêter l'animation"
echo "  animation-speech-ctl quit     # Quitter l'application"
echo ""

exit 0
EOF
chmod 755 "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN/postinst"

# Script postrm
echo "Création du script postrm..."
cat > "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

# Supprimer le fichier PID s'il existe
rm -f "${XDG_RUNTIME_DIR:-/tmp}/speech-animation.pid" 2>/dev/null || true

exit 0
EOF
chmod 755 "${SCRIPT_DIR}/${PACKAGE_DIR}/DEBIAN/postrm"

# Copie des fichiers
echo "Copie des fichiers..."

# Builder le zipapp
echo "Construction du zipapp..."
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/animation_speech"
cp "${PROJECT_DIR}"/animation_speech/*.py "$TMPDIR/animation_speech/"
printf 'from animation_speech.main import main\nmain()\n' > "$TMPDIR/__main__.py"
python3 -m zipapp "$TMPDIR" -o "${SCRIPT_DIR}/${BUILD_DIR}/animation-speech.pyz" \
    -p '/usr/bin/env python3'
rm -rf "$TMPDIR"
cp "${SCRIPT_DIR}/${BUILD_DIR}/animation-speech.pyz" \
   "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/bin/animation-speech"
chmod 755 "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/bin/animation-speech"

# Script de contrôle (version adaptée au paquet)
cp "${SCRIPT_DIR}/animation-speech-ctl" \
   "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/bin/animation-speech-ctl"
chmod 755 "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/bin/animation-speech-ctl"

# Configuration par défaut (utilise config.examples/default.yaml)
cp "${PROJECT_DIR}/config.examples/default.yaml" \
   "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/${PACKAGE}/config.yaml"

# Exemples de configuration (y compris sous-répertoires)
if [ -d "${PROJECT_DIR}/config.examples" ]; then
    cp -r "${PROJECT_DIR}/config.examples/"* \
       "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/${PACKAGE}/config.examples/" 2>/dev/null || true
fi

# Locales (.mo uniquement, chemin FHS standard)
if [ -d "${PROJECT_DIR}/locales" ]; then
    echo "Copie des locales..."
    for lang_dir in "${PROJECT_DIR}"/locales/*/LC_MESSAGES; do
        if [ -d "$lang_dir" ]; then
            lang=$(basename "$(dirname "$lang_dir")")
            mkdir -p "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/locale/${lang}/LC_MESSAGES"
            cp "$lang_dir"/*.mo \
               "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share/locale/${lang}/LC_MESSAGES/" 2>/dev/null || true
        fi
    done
fi

# Ajuster les permissions
find "${SCRIPT_DIR}/${PACKAGE_DIR}" -type d -exec chmod 755 {} \;
find "${SCRIPT_DIR}/${PACKAGE_DIR}/usr/share" -type f -exec chmod 644 {} \;

echo "Construction du paquet .deb..."
cd "${SCRIPT_DIR}"
dpkg-deb --build "${PACKAGE_DIR}"

# Déplacer le .deb à la racine du projet
mv "${BUILD_DIR}/${PACKAGE}_${VERSION}_${ARCH}.deb" "${PROJECT_DIR}/"

echo ""
echo "=== Paquet créé avec succès ==="
echo "Fichier: ${PROJECT_DIR}/${PACKAGE}_${VERSION}_${ARCH}.deb"
echo ""
echo "Installation:"
echo "  sudo dpkg -i ${PACKAGE}_${VERSION}_${ARCH}.deb"
echo ""
echo "En cas de dépendances manquantes:"
echo "  sudo apt-get install -f"
echo ""

# Nettoyage optionnel
read -p "Supprimer les fichiers temporaires ? [o/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    rm -rf "${SCRIPT_DIR}/${BUILD_DIR}"
    echo "Fichiers temporaires supprimés."
fi
