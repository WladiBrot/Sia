"""
Windgeschwindigkeitsmessung – Python-Port des Arduino-Sketches nurwindsensor.ino
Für Raspberry Pi mit KY-053 ADC (ADS1115), Anemometer an A0.

Verdrahtung:
  Raspberry Pi    →   KY-053
  Pin 1 (3V3)     →   VDD
  Pin 6 (GND)     →   GND
  Pin 3 (SDA)     →   SDA
  Pin 5 (SCL)     →   SCL
  Anemometer      →   A0
"""

import time

# Konstanten (wie Arduino)
SCHWELLENWERT = 800
BERECHNUNGS_KONSTANTE = 1.326

# Variablen
geschwindigkeit = 0.0
timea = 0.0
timeb = 0.0
timec = 0.0
a = 0
b = 0

adc_channel = None

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    ADC_AVAILABLE = True
except ImportError:
    ADC_AVAILABLE = False
    import random


def setup():
    """Initialisiert den ADC (KY-053 / ADS1115)."""
    global timeb, timec, adc_channel

    if ADC_AVAILABLE:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c, address=0x48)
            adc_channel = AnalogIn(ads, ADS.P0)
            print("KY-053 ADC initialisiert (Kanal A0)")
        except Exception as e:
            print(f"ADC-Fehler: {e}. Verwende Simulation.")
            adc_channel = None
    else:
        print("Bibliotheken fehlen. Verwende Simulation.")
        adc_channel = None

    timeb = time.perf_counter() * 1000
    timec = timeb


def analog_read():
    """Liest Analogwert 0–1023 (wie Arduino analogRead)."""
    if adc_channel:
        raw = adc_channel.value
        return int((raw / 65535.0) * 1023)
    return random.randint(0, 1023)


def loop():
    """Hauptlogik – entspricht Arduino loop()."""
    global a, b, timea, timeb, timec, geschwindigkeit

    a = b
    b = analog_read()

    if (b - a) > SCHWELLENWERT:
        timea = timeb
        timeb = time.perf_counter() * 1000
        diff = timeb - timea
        if diff > 0:
            geschwindigkeit = round((1000 / diff) * BERECHNUNGS_KONSTANTE)
        else:
            geschwindigkeit = 0.0
        print(f"Geschwindigkeit: {geschwindigkeit} km/h")

    timec = time.perf_counter() * 1000
    if (timec - timeb) > 1000:
        print(0)

    time.sleep(0.005)


if __name__ == "__main__":
    setup()
    print("Windgeschwindigkeit (Strg+C zum Beenden)\n")
    try:
        while True:
            loop()
    except KeyboardInterrupt:
        print("\nBeendet.")
