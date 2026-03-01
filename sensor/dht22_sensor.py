"""
DHT22 Temperatur- und Luftfeuchtigkeitssensor für Raspberry Pi 4 Model B
Sensor: SEN-DHT22 (AM2302)

Verdrahtung:
  - VCC (Pin 1)  → 3,3 V (Pin 1) oder 5 V (Pin 2) am Pi
  - DATA (Pin 2) → GPIO 4 (Pin 7) am Pi
  - NC   (Pin 3) → nicht verbinden
  - GND  (Pin 4) → GND (Pin 6) am Pi
  Optional: 4,7–10 kΩ Pull-up zwischen DATA und VCC (bei langen Kabeln empfohlen)

Installation auf dem Raspberry Pi (wenn pip nur in einer Umgebung funktioniert):
------------------------------------------------------------
  Option A – Virtual Environment (empfohlen):
     cd /pfad/zu/sia/sensor
     python3 -m venv venv
     source venv/bin/activate          # Linux/Pi
     pip install adafruit-circuitpython-dht adafruit-blinka
     # Skript starten mit:
     python dht22_sensor.py
     # Beenden der Umgebung: deactivate

  Option B – System-Pakete (ohne pip, manuell):
     sudo apt-get update
     sudo apt-get install -y python3-pip python3-venv python3-dev
     # Danach Option A (venv) nutzen, da pip systemweit oft Probleme macht.
------------------------------------------------------------
"""

import time
import sys

# GPIO-Pin für den DHT22 Datenpin (BCM-Nummer; z.B. 4 = Pin 7 auf dem Header)
DHT_PIN = 4

# Messintervall in Sekunden (DHT22: mind. 2 Sekunden zwischen Messungen)
MEASURE_INTERVAL = 2.5


def read_dht22():
    """
    Liest Temperatur und Luftfeuchtigkeit vom DHT22.
    Verwendet adafruit-circuitpython-dht (empfohlen für Pi 4).

    Returns:
        tuple: (temperatur_celsius, luftfeuchtigkeit_percent) oder (None, None) bei Fehler
    """
    try:
        import board
        import adafruit_dht
    except ImportError:
        print("✗ Bibliothek nicht gefunden. Mit Virtual Environment installieren:")
        print("  python3 -m venv venv && source venv/bin/activate")
        print("  pip install adafruit-circuitpython-dht adafruit-blinka")
        return None, None

    # GPIO-Pin zuordnen (BCM 4 = board.D4)
    pin_map = {
        4: getattr(board, "D4", None),
        17: getattr(board, "D17", None),
        27: getattr(board, "D27", None),
        22: getattr(board, "D22", None),
    }
    pin = pin_map.get(DHT_PIN)
    if pin is None:
        # Fallback: board.D4 ist bei den meisten Pis GPIO 4
        pin = board.D4

    try:
        dht = adafruit_dht.DHT22(pin)
    except Exception as e:
        print(f"✗ DHT22 konnte nicht initialisiert werden: {e}")
        return None, None

    try:
        temperatur = dht.temperature
        luftfeuchtigkeit = dht.humidity
        if temperatur is not None and luftfeuchtigkeit is not None:
            return round(temperatur, 1), round(luftfeuchtigkeit, 1)
        return None, None
    except RuntimeError as e:
        # "DHT sensor not found" oder Kommunikationsfehler
        return None, None
    finally:
        try:
            dht.exit()
        except Exception:
            pass


def read_dht22_legacy():
    """
    Fallback: Liest mit der älteren Adafruit_Python_DHT Bibliothek.
    Returns:
        tuple: (temperatur_celsius, luftfeuchtigkeit_percent) oder (None, None)
    """
    try:
        import Adafruit_DHT as dht
        humidity, temperature = dht.read_retry(dht.DHT22, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
    except ImportError:
        pass
    return None, None


def einmal_messen():
    """Führt eine einzelne Messung durch und gibt das Ergebnis aus."""
    temp, feuchte = read_dht22()
    if temp is None and feuchte is None:
        temp, feuchte = read_dht22_legacy()

    if temp is not None and feuchte is not None:
        print(f"Temperatur:    {temp} °C")
        print(f"Luftfeuchtigkeit: {feuchte} %")
        return True
    print("✗ Messung fehlgeschlagen (Kabel prüfen, Pin, Stromversorgung).")
    return False


def dauerbetrieb(intervall=MEASURE_INTERVAL):
    """Misst in einer Endlosschleife und gibt Werte aus."""
    print(f"DHT22 Dauerbetrieb (alle {intervall} s). Beenden mit Strg+C.\n")
    while True:
        temp, feuchte = read_dht22()
        if temp is None and feuchte is None:
            temp, feuchte = read_dht22_legacy()

        if temp is not None and feuchte is not None:
            zeit = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{zeit}]  {temp} °C  |  {feuchte} %")
        else:
            print("  (Messung fehlgeschlagen, nächster Versuch gleich)")

        time.sleep(intervall)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        dauerbetrieb()
    else:
        einmal_messen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBeendet.")
        sys.exit(0)
