"""
LoRa Sensor-Sender für Raspberry Pi mit SX1268 HAT (serielle Schnittstelle)
Sendet DHT22 (Temperatur, Luftfeuchtigkeit) und Anemometer (Windgeschwindigkeit)
als JSON-Zeile "SENSOR_DATA:{...}" an den Empfänger-Pi.

Alles in einer Datei – keine externen Sensor-Module nötig.

Hardware:
- Raspberry Pi
- DHT22 (AM2302)  → DATA an GPIO 4 (phys. Pin 7), VCC 3V3, GND
- Eltako WS Anemometer (Reedkontakt, 2 Adern)
      Ader 1 → GND
      Ader 2 → A0 am KY-053   +  Pull-Up 10 kΩ zwischen A0 und 3V3 !
- KY-053 / ADS1115 auf I²C (SDA = GPIO 2, SCL = GPIO 3, Adresse 0x48)
- Waveshare SX1268 LoRa HAT auf UART /dev/ttyS0 (9600 Baud), Jumper M0=M1=GND

Start: python lora_sensor_sender.py
"""

import time
import json
from datetime import datetime

import serial
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ============================================================
#  Konfiguration
# ============================================================

# --- LoRa ---
LORA_PORT = '/dev/ttyS0'
LORA_BAUDRATE = 9600
SEND_INTERVAL = 30  # Sekunden zwischen Sendevorgängen

# --- DHT22 ---
DHT22_PIN = board.D7  # GPIO 4, physischer Pin 7

# --- KY-053 / Eltako WS ---
ADS_I2C_ADDRESS = 0x48
# Kanal A0 des ADS1115. Neuere Versionen der Adafruit-Bibliothek haben die
# Konstante ADS.P0 entfernt – der nackte Index 0 funktioniert in allen Versionen.
ADS_KANAL_A0 = 0
# Schwellen für Hysterese-Flankenerkennung (Rohwerte ADS1115, 0..32767)
# Bei Gain=1 entspricht 32767 ≈ 4,096 V.
SCHWELLE_HIGH = 20000   # Signal gilt ab hier als HIGH (~2,5 V)
SCHWELLE_LOW = 8000     # Signal gilt erst darunter wieder als LOW (~1,0 V)
BERECHNUNGS_KONSTANTE = 1.326   # km/h pro Hz (1 Puls = 1 Umdrehung)
WIND_TIMEOUT_MS = 3000  # ohne Puls → Wind = 0


# ============================================================
#  DHT22
# ============================================================

_dht_device = None


def dht22_setup():
    global _dht_device
    try:
        _dht_device = adafruit_dht.DHT22(DHT22_PIN, use_pulseio=False)
        print("✓ DHT22 bereit (GPIO 4)")
        return True
    except Exception as e:
        print(f"⚠ DHT22 konnte nicht initialisiert werden: {e}")
        _dht_device = None
        return False


def dht22_read():
    """Liefert (temp_c, humidity) oder (None, None) bei Lesefehler."""
    if _dht_device is None:
        return None, None
    try:
        return _dht_device.temperature, _dht_device.humidity
    except RuntimeError:
        return None, None


# ============================================================
#  Anemometer (KY-053 + Eltako WS)
# ============================================================

_adc_channel = None
_wind_state_high = True
_wind_last_edge_ms = 0.0
geschwindigkeit = 0.0  # öffentlicher Windwert in km/h


def _now_ms():
    return time.perf_counter() * 1000.0


def anemometer_setup():
    global _adc_channel, _wind_state_high, _wind_last_edge_ms

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=ADS_I2C_ADDRESS)
    ads.gain = 1        # ±4,096 V – passt zu 3,3 V-Pulsen
    ads.data_rate = 860
    _adc_channel = AnalogIn(ads, ADS_KANAL_A0)

    _wind_state_high = True
    _wind_last_edge_ms = _now_ms()
    print("✓ KY-053 ADC bereit (A0, Gain=1, 860 SPS)")


def anemometer_tick():
    """
    Eine Messiteration. Aktualisiert `geschwindigkeit` auf Basis der
    Reedkontakt-Flanken. Nicht blockierend – in der Hauptschleife
    regelmäßig aufrufen.
    """
    global _wind_state_high, _wind_last_edge_ms, geschwindigkeit

    if _adc_channel is None:
        return

    raw = _adc_channel.value  # 0..32767 bei positivem Single-Ended

    if _wind_state_high and raw < SCHWELLE_LOW:
        # fallende Flanke – Reed geschlossen (eine Umdrehung)
        t = _now_ms()
        diff = t - _wind_last_edge_ms
        _wind_last_edge_ms = t
        _wind_state_high = False
        if diff > 0:
            geschwindigkeit = round((1000.0 / diff) * BERECHNUNGS_KONSTANTE, 1)

    elif not _wind_state_high and raw > SCHWELLE_HIGH:
        _wind_state_high = True

    # Kein Wind / Sensor steht: nach Timeout auf 0 zurücksetzen
    if (_now_ms() - _wind_last_edge_ms) > WIND_TIMEOUT_MS:
        geschwindigkeit = 0.0


# ============================================================
#  LoRa
# ============================================================

def setup_lora_serial():
    """Initialisiert die serielle Schnittstelle für das LoRa HAT."""
    try:
        lora_serial = serial.Serial(
            port=LORA_PORT,
            baudrate=LORA_BAUDRATE,
            timeout=1,
            write_timeout=5,
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


# ============================================================
#  Hauptprogramm
# ============================================================

def main():
    print("\n" + "=" * 50)
    print("LoRa Sensor-Sender (DHT22 + Eltako WS)")
    print("=" * 50 + "\n")

    anemometer_setup()
    dht22_ok = dht22_setup()

    lora_serial = setup_lora_serial()
    if not lora_serial:
        print("✗ Programm beendet: LoRa-Schnittstelle konnte nicht geöffnet werden.")
        return

    last_send_time = 0.0
    # Letzte gültige DHT22-Werte cachen, damit ein einzelner Fehlschlag
    # nicht dazu führt, dass Temp/Feuchte im Paket fehlen.
    last_temp_c = None
    last_humidity = None

    print(f"\nSende alle {SEND_INTERVAL} Sekunden. Beenden mit Strg+C.\n")

    try:
        while True:
            # Schnelle Schleife: fängt alle Reedkontakt-Flanken des Anemometers
            anemometer_tick()

            current_time = time.time()
            if (current_time - last_send_time) >= SEND_INTERVAL:
                # DHT22 nur beim Senden lesen (braucht ≥2 s zwischen Messungen)
                if dht22_ok:
                    temp_c, humidity = dht22_read()
                    if temp_c is not None:
                        last_temp_c = temp_c
                    if humidity is not None:
                        last_humidity = humidity

                data = {
                    "wind_kmh": round(geschwindigkeit, 1),
                    "timestamp": datetime.now().isoformat(),
                }
                if last_temp_c is not None:
                    data["temp_c"] = round(last_temp_c, 1)
                if last_humidity is not None:
                    data["humidity"] = round(last_humidity, 1)

                send_sensor_data(lora_serial, data)
                last_send_time = current_time

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n\nProgramm durch Benutzer beendet.")
    finally:
        try:
            lora_serial.close()
        except Exception:
            pass
        if _dht_device is not None:
            try:
                _dht_device.exit()
            except Exception:
                pass
        print("✓ Verbindungen geschlossen")


if __name__ == "__main__":
    main()
