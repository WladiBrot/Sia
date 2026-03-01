#!/bin/bash
# Installiert Autostart für LoRa Sender oder Receiver
# Verwendung: ./install-autostart.sh sender   (Sensor + Bild)
#             ./install-autostart.sh receiver  (Empfänger)

set -e

AUTOSTART_DIR="$HOME/.config/autostart"
SIA_PATH="$(cd "$(dirname "$0")/.." && pwd)"
FUNKMODUL_PATH="$SIA_PATH/Funkmodul"

mkdir -p "$AUTOSTART_DIR"
chmod +x "$FUNKMODUL_PATH/start.sh" 2>/dev/null || true

create_desktop() {
    local name="$1" comment="$2" arg="$3"
    cat > "$AUTOSTART_DIR/lora-${arg}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=${name}
Comment=${comment}
Exec=lxterminal -e "bash -c 'cd ${FUNKMODUL_PATH} && ./start.sh ${arg}; exec bash'"
Icon=utilities-terminal
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
}

case "$1" in
  sender)
    create_desktop "LoRa Sensor-Sender" "DHT22 und Anemometer Sender" "sender"
    create_desktop "LoRa Bild-Sender" "Kamera-Foto-Sender" "image"
    echo "✓ Sender-Autostart installiert (Sensor + Bild)."
    ;;
  receiver)
    create_desktop "LoRa Receiver" "Bild- und Sensor-Empfänger" "receiver"
    echo "✓ Receiver-Autostart installiert."
    ;;
  *)
    echo "Verwendung: $0 {sender|receiver}"
    echo "  sender   – Autostart für Sensor- und Bild-Sender"
    echo "  receiver – Autostart für den Empfänger"
    exit 1
    ;;
esac

echo "Beim nächsten Login öffnen sich die Debug-Konsolen."
