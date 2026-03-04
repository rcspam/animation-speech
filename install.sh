#!/bin/bash
#
# Installation de l'animation speech (sans audio2ts2pdf.sh)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE="${1:-}"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_usage() {
    echo "Usage: $0 [--user|--system|--uninstall]"
    echo ""
    echo "Options:"
    echo "  --user       Installation utilisateur dans ~/.local (défaut)"
    echo "  --system     Installation système dans /usr/local (nécessite sudo)"
    echo "  --uninstall  Désinstaller"
    echo ""
    echo "Fichiers installés:"
    echo "  - animation-speech      : Script d'animation"
    echo "  - config.yaml           : Configuration par défaut"
    echo "  - config.examples/      : Exemples de configurations"
    echo ""
    echo "Note: audio2ts2pdf.sh n'est PAS installé, il reste dans son emplacement actuel"
}

install_user() {
    echo -e "${GREEN}Installation utilisateur${NC}"
    echo ""

    BIN_DIR="$HOME/.local/bin"
    SHARE_DIR="$HOME/.local/share/animation-speech"

    # Créer les répertoires
    mkdir -p "$BIN_DIR"
    mkdir -p "$SHARE_DIR"

    # Builder le zipapp si nécessaire
    PYZ="$SCRIPT_DIR/animation-speech.pyz"
    if [[ ! -f "$PYZ" ]]; then
        echo "  → Construction du zipapp..."
        TMPDIR=$(mktemp -d)
        mkdir -p "$TMPDIR/animation_speech"
        cp "$SCRIPT_DIR"/animation_speech/*.py "$TMPDIR/animation_speech/"
        printf 'from animation_speech.main import main\nmain()\n' > "$TMPDIR/__main__.py"
        python3 -m zipapp "$TMPDIR" -o "$PYZ" -p '/usr/bin/env python3'
        rm -rf "$TMPDIR"
    fi

    # Copier le zipapp comme exécutable
    echo "  → Installation de animation-speech dans $BIN_DIR"
    cp "$PYZ" "$BIN_DIR/animation-speech"
    chmod +x "$BIN_DIR/animation-speech"

    # Copier le script de contrôle
    for _ctl in "$SCRIPT_DIR/animation-speech-ctl" "$SCRIPT_DIR/debian/animation-speech-ctl"; do
        if [[ -f "$_ctl" ]]; then
            echo "  → Installation de animation-speech-ctl dans $BIN_DIR"
            cp "$_ctl" "$BIN_DIR/animation-speech-ctl"
            chmod +x "$BIN_DIR/animation-speech-ctl"
            break
        fi
    done

    # Copier les configs
    echo "  → Installation de config.yaml dans $SHARE_DIR"
    cp "$SCRIPT_DIR/config.yaml" "$SHARE_DIR/"

    if [[ -d "$SCRIPT_DIR/config.examples" ]]; then
        echo "  → Installation des exemples dans $SHARE_DIR/config.examples/"
        cp -r "$SCRIPT_DIR/config.examples" "$SHARE_DIR/"
    fi

    # Installer les locales (.mo uniquement)
    if [[ -d "$SCRIPT_DIR/locales" ]]; then
        echo "  → Installation des locales dans $SHARE_DIR/locales/"
        for lang_dir in "$SCRIPT_DIR"/locales/*/LC_MESSAGES; do
            if [[ -d "$lang_dir" ]]; then
                lang=$(basename "$(dirname "$lang_dir")")
                mkdir -p "$SHARE_DIR/locales/$lang/LC_MESSAGES"
                cp "$lang_dir"/*.mo "$SHARE_DIR/locales/$lang/LC_MESSAGES/" 2>/dev/null || true
            fi
        done
    fi

    echo ""
    echo -e "${GREEN}✓ Installation terminée${NC}"
    echo ""
    echo "Fichiers installés:"
    echo "  - $BIN_DIR/animation-speech"
    echo "  - $SHARE_DIR/config.yaml"
    echo "  - $SHARE_DIR/config.examples/"
    echo "  - $SHARE_DIR/locales/"
    echo ""
    echo -e "${YELLOW}Vérifier que ~/.local/bin est dans le PATH:${NC}"
    if echo "$PATH" | grep -q "$HOME/.local/bin"; then
        echo -e "${GREEN}  ✓ ~/.local/bin est dans le PATH${NC}"
    else
        echo -e "${RED}  ✗ ~/.local/bin n'est PAS dans le PATH${NC}"
        echo ""
        echo "  Ajoutez cette ligne dans ~/.bashrc ou ~/.zshrc:"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

install_system() {
    echo -e "${GREEN}Installation système${NC}"
    echo ""
    
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}Erreur: Installation système nécessite sudo${NC}"
        echo "Relancez avec: sudo $0 --system"
        exit 1
    fi
    
    BIN_DIR="/usr/local/bin"
    SHARE_DIR="/usr/local/share/animation-speech"
    
    # Créer les répertoires
    mkdir -p "$BIN_DIR"
    mkdir -p "$SHARE_DIR"
    
    # Builder le zipapp si nécessaire
    PYZ="$SCRIPT_DIR/animation-speech.pyz"
    if [[ ! -f "$PYZ" ]]; then
        echo "  → Construction du zipapp..."
        TMPDIR=$(mktemp -d)
        mkdir -p "$TMPDIR/animation_speech"
        cp "$SCRIPT_DIR"/animation_speech/*.py "$TMPDIR/animation_speech/"
        printf 'from animation_speech.main import main\nmain()\n' > "$TMPDIR/__main__.py"
        python3 -m zipapp "$TMPDIR" -o "$PYZ" -p '/usr/bin/env python3'
        rm -rf "$TMPDIR"
    fi

    # Copier le zipapp comme exécutable
    echo "  → Installation de animation-speech dans $BIN_DIR"
    cp "$PYZ" "$BIN_DIR/animation-speech"
    chmod +x "$BIN_DIR/animation-speech"

    # Copier le script de contrôle
    for _ctl in "$SCRIPT_DIR/animation-speech-ctl" "$SCRIPT_DIR/debian/animation-speech-ctl"; do
        if [[ -f "$_ctl" ]]; then
            echo "  → Installation de animation-speech-ctl dans $BIN_DIR"
            cp "$_ctl" "$BIN_DIR/animation-speech-ctl"
            chmod +x "$BIN_DIR/animation-speech-ctl"
            break
        fi
    done

    # Copier les configs
    echo "  → Installation de config.yaml dans $SHARE_DIR"
    cp "$SCRIPT_DIR/config.yaml" "$SHARE_DIR/"

    if [[ -d "$SCRIPT_DIR/config.examples" ]]; then
        echo "  → Installation des exemples dans $SHARE_DIR/config.examples/"
        cp -r "$SCRIPT_DIR/config.examples" "$SHARE_DIR/"
    fi

    # Installer les locales (.mo uniquement)
    if [[ -d "$SCRIPT_DIR/locales" ]]; then
        echo "  → Installation des locales dans $SHARE_DIR/locales/"
        for lang_dir in "$SCRIPT_DIR"/locales/*/LC_MESSAGES; do
            if [[ -d "$lang_dir" ]]; then
                lang=$(basename "$(dirname "$lang_dir")")
                mkdir -p "$SHARE_DIR/locales/$lang/LC_MESSAGES"
                cp "$lang_dir"/*.mo "$SHARE_DIR/locales/$lang/LC_MESSAGES/" 2>/dev/null || true
            fi
        done
    fi

    echo ""
    echo -e "${GREEN}✓ Installation terminée${NC}"
    echo ""
    echo "Fichiers installés:"
    echo "  - $BIN_DIR/animation-speech"
    echo "  - $SHARE_DIR/config.yaml"
    echo "  - $SHARE_DIR/config.examples/"
    echo "  - $SHARE_DIR/locales/"
}

uninstall_user() {
    echo -e "${YELLOW}Désinstallation utilisateur${NC}"
    echo ""
    
    BIN_DIR="$HOME/.local/bin"
    SHARE_DIR="$HOME/.local/share/animation-speech"
    
    for _f in "$BIN_DIR/animation-speech" "$BIN_DIR/animation-speech-ctl"; do
        if [[ -f "$_f" ]]; then
            rm "$_f"
            echo "  ✓ Supprimé: $_f"
        fi
    done

    if [[ -d "$SHARE_DIR" ]]; then
        rm -rf "$SHARE_DIR"
        echo "  ✓ Supprimé: $SHARE_DIR"
    fi

    echo ""
    echo -e "${GREEN}✓ Désinstallation terminée${NC}"
}

uninstall_system() {
    echo -e "${YELLOW}Désinstallation système${NC}"
    echo ""

    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}Erreur: Désinstallation système nécessite sudo${NC}"
        echo "Relancez avec: sudo $0 --uninstall --system"
        exit 1
    fi

    BIN_DIR="/usr/local/bin"
    SHARE_DIR="/usr/local/share/animation-speech"

    for _f in "$BIN_DIR/animation-speech" "$BIN_DIR/animation-speech-ctl"; do
        if [[ -f "$_f" ]]; then
            rm "$_f"
            echo "  ✓ Supprimé: $_f"
        fi
    done

    if [[ -d "$SHARE_DIR" ]]; then
        rm -rf "$SHARE_DIR"
        echo "  ✓ Supprimé: $SHARE_DIR"
    fi
    
    echo ""
    echo -e "${GREEN}✓ Désinstallation terminée${NC}"
}

# Main
case "$INSTALL_TYPE" in
    --user|"")
        install_user
        ;;
    --system)
        install_system
        ;;
    --uninstall)
        if [[ "${2:-}" == "--system" ]]; then
            uninstall_system
        else
            uninstall_user
        fi
        ;;
    --help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Option invalide: $INSTALL_TYPE${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
