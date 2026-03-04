#!/bin/bash
# Installation rapide de gtk4-layer-shell

echo "=== Installation de gtk4-layer-shell ==="
echo ""

# Détecter la distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "Impossible de détecter la distribution"
    exit 1
fi

case $DISTRO in
    ubuntu|debian|pop|linuxmint)
        echo "Installation pour Debian/Ubuntu..."
        sudo apt update
        sudo apt install -y gtk4-layer-shell gir1.2-gtk4layershell-1.0
        ;;
    arch|manjaro|endeavouros)
        echo "Installation pour Arch..."
        sudo pacman -S --needed gtk4-layer-shell
        ;;
    fedora)
        echo "Installation pour Fedora..."
        sudo dnf install -y gtk4-layer-shell
        ;;
    *)
        echo "Distribution: $DISTRO"
        echo "Veuillez installer manuellement gtk4-layer-shell"
        echo ""
        echo "Recherchez le paquet dans votre gestionnaire:"
        echo "  - Debian/Ubuntu: apt search gtk4-layer-shell"
        echo "  - Arch: pacman -Ss gtk4-layer-shell"
        echo "  - Fedora: dnf search gtk4-layer-shell"
        exit 1
        ;;
esac

echo ""
echo "✓ Installation terminée!"
echo ""
echo "Testez maintenant avec: ./animation_speech.py"
