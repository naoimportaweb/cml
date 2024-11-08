#!/bin/bash

export BLUE='\033[1;94m'
export GREEN='\033[1;92m'
export RED='\033[1;91m'
export RESETCOLOR='\033[1;00m'

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root/Por favor, execute como root"
    exit
fi

if [ "$#" -ne 1 ]; then
    echo "Informe o site."
    exit
fi

if [ -d /opt/cml/ ] ; then
    echo "Existe uma versão anterior"
else
    mkdir /opt/cml
fi

apt update -y
apt install python3-pip -y
apt install libxcb-* -y

# para DEBIAN precisa do --break-system-packages para os outros OSs não
if [ ! -f /etc/pip.conf ] ; then
    touch /etc/pip.conf
    echo '[global]' > /etc/pip.conf
    echo 'break-system-packages = true' >> /etc/pip.conf
fi
pip3 install requests
pip3 install PySide6
pip3 install pycryptodome
pip3 install pyspellchecker
pip3 install beautifulsoup4

wget -O /tmp/client.tar.gz $1/cml/webpage/downloads/client.tar.gz
tar xzvf /tmp/client.tar.gz -C /opt/cml/ --strip-components=1

chmod +x /opt/cml/application.py

if [ ! -f /bin/cml ] ; then
    ln -s /opt/cml/application.py /bin/cml
fi

if [ -d /home/$SUDO_USER/.local/share/applications ] ; then
    echo "Ok, existe o diretório de aplicativos."
else
    mkdir /home/$SUDO_USER/.local/share/applications
fi

cp /opt/cml/resources/cml.desktop /home/$SUDO_USER/.local/share/applications

cml &



