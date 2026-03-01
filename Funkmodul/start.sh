#!/bin/bash
cd "$(dirname "$0")"

case "$1" in
  sender)
    echo "=== LoRa Sensor-Sender (Debug) ==="
    echo "Beenden mit Strg+C"
    echo ""
    python3 lora_sensor_sender.py
    ;;
  receiver)
    echo "=== LoRa Receiver (Debug) ==="
    echo "Beenden mit Strg+C"
    echo ""
    python3 lora_image_receiver.py
    ;;
  image)
    echo "=== LoRa Bild-Sender (Debug) ==="
    echo "Beenden mit Strg+C"
    echo ""
    python3 lora_image_sender.py
    ;;
  *)
    echo "Verwendung: $0 {sender|receiver|image}"
    exit 1
    ;;
esac

echo ""
echo "Programm beendet. Drücke Enter zum Schließen."
read
