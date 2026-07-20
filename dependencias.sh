#!/bin/bash
#
# dependencias.sh — instala SÓ as dependências para rodar o cliente CML a partir do
# código (python3 app/application.py). Não baixa nada do site nem exige login/servidor,
# ao contrário do app/install.sh (instalador do usuário final).
#
# Cobre o erro do PySide6 >= 6.5 no Debian 13:
#   qt.qpa.plugin: libxcb-cursor0 is needed to load the Qt xcb platform plugin.
# A lib de sistema libxcb-cursor0 não vem por dependência do pip.
#
# Uso:  ./dependencias.sh

set -euo pipefail

BLUE='\033[1;94m'; GREEN='\033[1;92m'; RESET='\033[0m'
info() { echo -e "${BLUE}==>${RESET} $*"; }
ok()   { echo -e "${GREEN}ok:${RESET} $*"; }

# sudo só se não formos root
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

# 1) Libs de sistema do plugin xcb do Qt6 (libxcb-cursor0 é a que falta no Debian 13;
#    as demais cobrem os outros plugins do xcb para não trombar no próximo import).
info "Libs de sistema do Qt/xcb (apt)…"
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
    python3 python3-pip \
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
    libxkbcommon-x11-0 libgl1 libegl1 libdbus-1-3 libfontconfig1
ok "Libs de sistema instaladas."

# 2) Dependências Python do cliente (mesma lista do app/install.sh).
#    --break-system-packages porque o Debian 13 marca o ambiente externally-managed (PEP 668).
info "Deps Python (pip)…"
python3 -m pip install --break-system-packages \
    requests PySide6 pycryptodome pyspellchecker beautifulsoup4 waybackpy
ok "Deps Python instaladas."

echo
ok "Pronto. Rode o cliente com:  python3 app/application.py"
