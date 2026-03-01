"""
Anemometer-Geschwindigkeitsmessung für Raspberry Pi mit KY-053 / COM-KY053ADC

Modul: JOY-IT KY-053 bzw. COM-KY053ADC (ADS1115, 16-bit, 4 Kanäle, I2C).
Keine Unterstützung für andere ADC-Chips (z.B. MCP3008).

Hardware-Anforderungen:
- Raspberry Pi 4 (oder 3/Zero)
- KY-053 / COM-KY053ADC ADC-Modul (ADS1115)
- Anemometer-Signal an KY-053 Kanal A0
- Optional: Waveshare SX1268 LoRa HAT

Verdrahtung (Raspberry Pi 40-Pin-Header):
  Raspberry Pi          →   KY-053 / COM-KY053ADC
  -----------------------------------------------
  Pin 1  (3V3)          →   VDD / V+
  Pin 6  (GND)           →   GND / 0V
  Pin 3  (SDA, GPIO 2)   →   SDA
  Pin 5  (SCL, GPIO 3)   →   SCL
  Anemometer-Signal      →   A0 (Kanal 0)
  (Alert, ADDR-Pins am Modul unverbunden lassen)
"""

import time
import json
from datetime import datetime

# --- KY-053 ADC (ADS1115) via I2C ---
ADC_AVAILABLE = False
adc_channel = None

try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
    ADC_AVAILABLE = True
except ImportError:
    print("Warnung: KY-053-Bibliotheken nicht gefunden. Verwende Simulation.")
    import random

# LoRa SX1268 HAT Support
LORA_AVAILABLE = False
SX126X = None
try:
    from sx126x import SX126X
    LORA_AVAILABLE = True
except ImportError:
    try:
        import sx126x
        SX126X = sx126x.SX126X
        LORA_AVAILABLE = True
    except (ImportError, AttributeError):
        LORA_AVAILABLE = False
        print("Warnung: LoRa SX1268 HAT Bibliothek nicht gefunden.")
        print("LoRa-Funktionalität wird deaktiviert.")

# --- Globale Variablen ---
Geschwindigkeit = 0.0
timea = 0.0
timeb = 0.0
timec = 0.0
a = 0
b = 0

# Konstanten für die Berechnung (unverändert vom Original-Anemometer)
BERECHNUNGS_KONSTANTE = 1.326
SCHWELLENWERT = 800

# LoRa-Variablen
lora = None
last_send_time = 0
LORA_SEND_INTERVAL = 20 * 60  # 20 Minuten in Sekunden

# LoRa-Konfiguration
LORA_FREQUENCY = 433.0
LORA_POWER = 14
LORA_SPREADING_FACTOR = 7
LORA_BANDWIDTH = 125
LORA_CODING_RATE = 5
LORA_SYNC_WORD = 0x12

# KY-053 ADC-Konfiguration (nur für ADS1115)
KY053_I2C_ADDRESS = 0x48  # Standard-Adresse (ADDR-Pin an GND); 0x49-0x4B möglich
KY053_CHANNEL = 0  # A0 für Anemometer (A0-A3 verfügbar)


def setup_lora():
    """Initialisiert das LoRa-Modul (SX1268 HAT)."""
    global lora, last_send_time

    if not LORA_AVAILABLE:
        return False

    try:
        import RPi.GPIO as GPIO

        lora = SX126X(
            cs=8,
            rst=25,
            busy=24,
            freq=LORA_FREQUENCY,
            txPower=LORA_POWER,
            spreadingFactor=LORA_SPREADING_FACTOR,
            bandwidth=LORA_BANDWIDTH,
            codingRate=LORA_CODING_RATE,
            syncWord=LORA_SYNC_WORD
        )

        print("LoRa SX1268 HAT erfolgreich initialisiert!")
        print(f"Frequenz: {LORA_FREQUENCY} MHz")
        print(f"Sendeintervall: {LORA_SEND_INTERVAL / 60} Minuten")
        last_send_time = time.time()
        return True

    except Exception as e:
        print(f"Fehler beim Initialisieren des LoRa-Moduls: {e}")
        lora = None
        return False


def setup(use_lora=True):
    """Initialisiert den KY-053 ADC und die Variablen.
    use_lora: Wenn False, wird kein LoRa-Modul initialisiert (z.B. für lora_sensor_sender).
    """
    global timeb, timec, adc_channel, last_send_time

    print("=" * 50)
    print("Anemometer mit KY-053 ADC (ADS1115)")
    print("=" * 50)
    print("Starte Geschwindigkeits-Messung...")
    print()

    zeit_ms = int(time.perf_counter() * 1000)
    timeb = zeit_ms
    timec = zeit_ms
    last_send_time = time.time()

    # KY-053 (ADS1115) über I2C initialisieren
    if ADC_AVAILABLE:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS1115(i2c, address=KY053_I2C_ADDRESS)
            # Kanal 0 = A0 (Anemometer)
            adc_channel = AnalogIn(ads, getattr(ADS1115, f"P{KY053_CHANNEL}"))

            print("KY-053 ADC (ADS1115) erfolgreich initialisiert!")
            print(f"  I2C-Adresse: 0x{KY053_I2C_ADDRESS:02X}")
            print(f"  Kanal: A{KY053_CHANNEL}")
            print(f"  Referenzspannung: {adc_channel.reference_voltage}V")
            print()

        except Exception as e:
            print(f"Fehler beim Initialisieren des KY-053: {e}")
            print("Verwende Simulation statt Hardware...")
            adc_channel = None
    else:
        print("KY-053-Bibliotheken nicht verfügbar. Verwende Simulation.")
        adc_channel = None

    if use_lora:
        setup_lora()


def analogRead_ky053():
    """
    Liest einen Analogwert vom KY-053 (ADS1115).
    Gibt einen Wert zwischen 0 und 1023 zurück (wie Arduino analogRead).
    Skaliert den 16-bit-Wert des ADS1115 auf 0-1023 für Kompatibilität
    mit der bestehenden Anemometer-Logik.
    """
    global adc_channel

    if adc_channel is not None and ADC_AVAILABLE:
        try:
            # ADS1115: 16-bit (0-65535 für positive Spannung)
            raw_value = adc_channel.value
            # Skalieren auf 0-1023 (wie 10-bit Arduino/MCP3008)
            adc_10bit = int((raw_value / 65535.0) * 1023)
            return adc_10bit
        except Exception as e:
            print(f"Fehler beim Lesen vom KY-053: {e}")
            return 0
    else:
        return random.randint(0, 1023)


def send_lora_data():
    """Sendet die aktuellen Anemometer-Daten per LoRa."""
    global lora, last_send_time, Geschwindigkeit, b

    if lora is None:
        return False

    try:
        data = {
            "geschwindigkeit": Geschwindigkeit,
            "timestamp": datetime.now().isoformat(),
            "adc_wert": b
        }
        json_data = json.dumps(data)
        lora.send(json_data.encode("utf-8"))
        print(f"[LoRa] Daten gesendet: {json_data}")
        print(f"[LoRa] Nächster Sendevorgang in {LORA_SEND_INTERVAL / 60:.1f} Minuten")
        last_send_time = time.time()
        return True
    except Exception as e:
        print(f"[LoRa] Fehler beim Senden: {e}")
        return False


def loop(send_lora=True):
    """Hauptlogik der Geschwindigkeitsmessung.
    send_lora: Wenn False, wird nicht per SX126X gesendet (z.B. bei lora_sensor_sender).
    """
    global a, b, timea, timeb, timec, Geschwindigkeit, last_send_time

    a = b
    b = analogRead_ky053()

    if (b - a) > SCHWELLENWERT:
        timea = timeb
        timeb = int(time.perf_counter() * 1000)

        zeit_diff = timeb - timea
        if zeit_diff > 0:
            Geschwindigkeit = round((1000 / zeit_diff) * BERECHNUNGS_KONSTANTE)
        else:
            Geschwindigkeit = 0.0

        print(f"Geschwindigkeit: {Geschwindigkeit} km/h (ADC: {b})")

    timec = int(time.perf_counter() * 1000)
    if (timec - timeb) > 1000:
        print(0)

    if send_lora:
        current_time = time.time()
        if (current_time - last_send_time) >= LORA_SEND_INTERVAL:
            send_lora_data()

    time.sleep(0.005)


if __name__ == "__main__":
    setup()
    try:
        while True:
            loop()
    except KeyboardInterrupt:
        print("\nMessung beendet.")
