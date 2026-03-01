"""
LoRa Sensor-Sender für Raspberry Pi mit SX1268 HAT (serielle Schnittstelle)
Sendet DHT22 (Temperatur, Luftfeuchtigkeit) und Anemometer (Windgeschwindigkeit) an den Receiver.

Hardware:
- Raspberry Pi mit DHT22, KY-053 Anemometer, SX1268 LoRa HAT (UART auf /dev/ttyS0)
- Verdrahtung siehe sensor/INSTALL_DHT22.md und Windradar/INSTALL_ANEMOMETER.md

Start: python lora_sensor_sender.py
"""

import time
import serial
import json
import sys
import os
from datetime import datetime

# Pfad für Imports aus übergeordneten Ordnern (sensor, Windradar)
SIA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("Windradar", "sensor"):
    path = os.path.join(SIA_ROOT, sub)
    if path not in sys.path:
        sys.path.insert(0, path)

# --- LoRa-Konstanten (wie lora_image_sender) ---
LORA_PORT = '/dev/ttyS0'
LORA_BAUDRATE = 9600
SEND_INTERVAL = 30  # Sekunden zwischen Sendevorgängen


def setup_lora_serial():
    """Initialisiert die serielle Schnittstelle für das LoRa HAT."""
    try:
        lora_serial = serial.Serial(
            port=LORA_PORT,
            baudrate=LORA_BAUDRATE,
            timeout=1,
            write_timeout=5
        )
        print(f"✓ LoRa-Schnittstelle auf {LORA_PORT} geöffnet (Baudrate: {LORA_BAUDRATE})")
        time.sleep(0.5)
        return lora_serial
    except serial.SerialException as e:
        print(f"✗ FEHLER: Kann serielle Schnittstelle nicht öffnen: {e}")
        return None
    except Exception as e:
        print(f"✗ Unerwarteter Fehler: {e}")
        return None


def send_sensor_data(lora_serial, data):
    """Sendet Sensordaten als SENSOR_DATA:... Zeile über LoRa."""
    if not lora_serial:
        return False
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        packet = f"SENSOR_DATA:{json_str}\n".encode('utf-8')
        lora_serial.write(packet)
        lora_serial.flush()
        print(f"✓ Gesendet: {json_str}")
        return True
    except Exception as e:
        print(f"✗ Fehler beim Senden: {e}")
        return False


def main():
    print("\n" + "=" * 50)
    print("LoRa Sensor-Sender (DHT22 + Anemometer)")
    print("=" * 50 + "\n")

    # Anemometer initialisieren (ohne eigenes LoRa)
    try:
        import anemometer_ky053 as anemometer
        anemometer.setup(use_lora=False)
    except ImportError as e:
        print(f"✗ Anemometer-Modul nicht gefunden: {e}")
        print("  Stelle sicher, dass Windradar/anemometer_ky053.py existiert.")
        return

    # DHT22-Modul (wird bei Bedarf importiert)
    try:
        import dht22_sensor
    except ImportError:
        dht22_sensor = None
        print("⚠ DHT22-Modul nicht gefunden. Sende nur Anemometer-Daten.")

    # LoRa-Schnittstelle
    lora_serial = setup_lora_serial()
    if not lora_serial:
        print("✗ Programm beendet: LoRa-Schnittstelle konnte nicht geöffnet werden.")
        return

    last_send_time = 0

    print(f"Sende alle {SEND_INTERVAL} Sekunden. Beenden mit Strg+C.\n")

    try:
        while True:
            # Anemometer-Loop (aktualisiert Geschwindigkeit)
            anemometer.loop(send_lora=False)

            # DHT22 lesen (alle ~2,5 s sinnvoll, wir lesen bei jedem Sendevorgang)
            temp_c = None
            humidity = None
            if dht22_sensor:
                temp_c, humidity = dht22_sensor.read_dht22()
                if temp_c is None and humidity is None:
                    temp_c, humidity = dht22_sensor.read_dht22_legacy()

            current_time = time.time()
            if (current_time - last_send_time) >= SEND_INTERVAL:
                data = {
                    "wind_kmh": round(anemometer.Geschwindigkeit, 1),
                    "timestamp": datetime.now().isoformat(),
                }
                if temp_c is not None:
                    data["temp_c"] = temp_c
                if humidity is not None:
                    data["humidity"] = humidity

                send_sensor_data(lora_serial, data)
                last_send_time = current_time

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nProgramm durch Benutzer beendet.")
    finally:
        lora_serial.close()
        print("✓ Serielle Verbindung geschlossen")


if __name__ == "__main__":
    main()
