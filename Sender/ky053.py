"""
Standalone-Testskript für das Eltako-WS-Anemometer am KY-053 (ADS1115).
Diese Version nutzt eine extrem robuste Import-Methode.
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Falls ADS.P0 fehlschlägt, definieren wir die Konstante manuell.
# Bei der Adafruit Bibliothek ist P0 intern einfach der Index 0.
PIN_A0 = 0 

# Konfiguration
SCHWELLE_HIGH = 20000   
SCHWELLE_LOW = 8000     
BERECHNUNGS_KONSTANTE = 1.326
TIMEOUT_MS = 3000

def now_ms():
    return time.perf_counter() * 1000.0

try:
    # Initialisierung I2C
    i2c = busio.I2C(board.SCL, board.SDA)
    
    # Initialisierung ADS1115
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.gain = 1
    ads.data_rate = 860

    # Hier nutzen wir direkt die 0 für den ersten Kanal (A0)
    # Das umgeht alle "AttributeError" Probleme mit P0
    adc = AnalogIn(ads, PIN_A0)

    print("KY-053 ADC bereit (A0, Gain=1, 860 SPS)")
    print("Windgeschwindigkeit (Strg+C zum Beenden)\n")

    state_high = True
    last_edge_ms = now_ms()
    geschwindigkeit = 0.0
    last_printed = None
    last_print_ms = 0.0

    while True:
        raw = adc.value

        # Flankenerkennung
        if state_high and raw < SCHWELLE_LOW:
            t = now_ms()
            diff = t - last_edge_ms
            last_edge_ms = t
            state_high = False
            if diff > 0:
                geschwindigkeit = round((1000.0 / diff) * BERECHNUNGS_KONSTANTE, 1)

        elif not state_high and raw > SCHWELLE_HIGH:
            state_high = True

        # Timeout
        if (now_ms() - last_edge_ms) > TIMEOUT_MS:
            geschwindigkeit = 0.0

        # Ausgabe
        t_now = now_ms()
        if geschwindigkeit != last_printed or (t_now - last_print_ms) > 1000:
            print(f"Geschwindigkeit: {geschwindigkeit} km/h (Rohwert: {raw})")
            last_printed = geschwindigkeit
            last_print_ms = t_now

        time.sleep(0.002)

except Exception as e:
    print(f"Fehler beim Starten: {e}")

except KeyboardInterrupt:
    print("\nTest beendet.")
