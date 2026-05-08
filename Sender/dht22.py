import time
import board
import adafruit_dht

# DHT22 an GPIO4 (physischer Pin 7)
dhtDevice = adafruit_dht.DHT22(board.D7, use_pulseio=False)

try:
    time.sleep(2)
    while True:
        try:
            temperature_c = dhtDevice.temperature
            humidity = dhtDevice.humidity

            if temperature_c is not None and humidity is not None:
                temperature_f = temperature_c * 9 / 5 + 32
                print(f"Temp: {temperature_f:.1f} F / {temperature_c:.1f} C  Luftfeuchtigkeit: {humidity:.1f}%")
            else:
                print("Kein gültiger Messwert, nächster Versuch...")

        except RuntimeError as error:
            print(f"Lese-Fehler: {error}")

        time.sleep(2.0)

except KeyboardInterrupt:
    pass
finally:
    dhtDevice.exit()
