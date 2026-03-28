Name:           animation-speech
Version:        1.2.0
Release:        1%{?dist}
Summary:        Transparent speech animation overlay for Wayland
License:        GPL-3.0-or-later
URL:            https://github.com/rcspam/animation-speech
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

# ── Dépendances obligatoires ────────────────────────────────────────
Requires:       python3
Requires:       python3-gobject

%if 0%{?suse_version}
Requires:       python3-gobject-cairo
Requires:       gtk3
Requires:       python3-PyYAML
Requires:       gtk-layer-shell
Requires:       typelib-1_0-GtkLayerShell-0_1
Requires:       procps
Requires:       gettext-runtime
%else
# Fedora: cairo support is included in python3-gobject (no separate package)
Requires:       gtk3
Requires:       python3-pyyaml
Requires:       gtk-layer-shell
Requires:       procps-ng
Requires:       gettext
%endif

# ── Dépendances optionnelles (audio) ───────────────────────────────
%if 0%{?suse_version}
Recommends:     python3-PyAudio
%else
Recommends:     python3-pyaudio
%endif
Recommends:     pulseaudio-utils
Recommends:     alsa-utils

%description
Transparent overlay animation for Wayland compositors that displays
speech activity indicators. Uses GTK3 with gtk-layer-shell for true
transparent overlays. Controlled via UNIX signals (SIGUSR1/SIGUSR2).

Supports 8 animation types: wave, equalizer, circular, particles,
soundwave, soundwave-curve, circular-wave, circular-bars.
Includes a visual configuration selector (--choose).

Compatible with KDE Plasma, Sway, Hyprland, and other
wlr-layer-shell compositors. Not compatible with GNOME (Mutter).

%prep
%setup -q

%build
# Construire le zipapp
mkdir -p .zipapp-build/animation_speech
cp animation_speech/*.py .zipapp-build/animation_speech/
printf 'from animation_speech.main import main\nmain()\n' > .zipapp-build/__main__.py
python3 -m zipapp .zipapp-build -o animation-speech.pyz \
    -p '/usr/bin/env python3'
rm -rf .zipapp-build

# Compiler les locales
for lang in fr en; do
    pofile="locales/${lang}/LC_MESSAGES/%{name}.po"
    mofile="locales/${lang}/LC_MESSAGES/%{name}.mo"
    if [ -f "$pofile" ]; then
        msgfmt -o "$mofile" "$pofile"
    fi
done

%install
# Binaires
install -Dm 755 animation-speech.pyz %{buildroot}%{_bindir}/animation-speech
install -Dm 755 debian/animation-speech-ctl %{buildroot}%{_bindir}/animation-speech-ctl

# Config par défaut
install -Dm 644 config.examples/default.yaml %{buildroot}%{_datadir}/%{name}/config.yaml

# Exemples de configuration
mkdir -p %{buildroot}%{_datadir}/%{name}/config.examples
cp -r config.examples/* %{buildroot}%{_datadir}/%{name}/config.examples/

# Locales (chemin FHS standard)
for lang in fr en; do
    mofile="locales/${lang}/LC_MESSAGES/%{name}.mo"
    if [ -f "$mofile" ]; then
        install -Dm 644 "$mofile" \
            %{buildroot}%{_datadir}/locale/${lang}/LC_MESSAGES/%{name}.mo
    fi
done

%post
echo ""
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

%postun
# Nettoyage du fichier PID
rm -f "${XDG_RUNTIME_DIR:-/tmp}/speech-animation.pid" 2>/dev/null || true

%files
%license LICENSE
%doc README.md
%{_bindir}/animation-speech
%{_bindir}/animation-speech-ctl
%{_datadir}/%{name}/
%{_datadir}/locale/*/LC_MESSAGES/%{name}.mo
