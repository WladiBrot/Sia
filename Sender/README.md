# Sender-Pi – Wetterstation & Kamera

Dieser Ordner gehört auf den **Sender-Raspberry-Pi** im Feld.
Er liest Temperatur, Luftfeuchte und Windgeschwindigkeit und schickt sie
zusammen mit Kamerabildern über LoRa an den Empfänger-Pi.

## Inhalt

| Datei | Zweck |
|---|---|
| `lora_sensor_sender.py` | **Hauptskript 1** – liest DHT22 + Eltako-WS-Anemometer direkt und sendet alle 30 s `SENSOR_DATA:{json}` per LoRa. Alle Sensor-Routinen sind bereits integriert. |
| `lora_image_sender.py` | **Hauptskript 2** – nimmt alle 10 min ein Foto auf, komprimiert & sendet es paketweise per LoRa. |
| `lora_config.py` | Einmalige Konfiguration des SX1268-HAT (Frequenz, SF, Bandbreite …). |
| `dht22.py` | Optional – kleines Standalone-Testskript für den DHT22 allein. |
| `ky053.py` | Optional – kleines Standalone-Testskript für das Anemometer allein. |
| `arduino/` | Arduino-Referenz-Sketches (Standalone-Betrieb ohne Pi). |
| `requirements.txt` | Python-Abhängigkeiten für den Sender. |

## Hardware

- Raspberry Pi (4 empfohlen) mit Pi-Kamera
- DHT22 (AM2302) → **DATA an GPIO 7** (physisch Pin 26), VCC 3,3 V, GND
- Anemometer → **A0 des KY-053** (I²C auf GPIO 2/3, Adresse 0x48)
- Waveshare **SX1268 LoRa HAT** auf UART (`/dev/ttyS0`, 9600 Baud), Jumper M0=M1=GND

Details zur Verdrahtung findest du im Repo-Root-README.

## System vorbereiten (einmalig)

```bash
sudo raspi-config
# Interface Options → I2C           : Enable
# Interface Options → Serial Port   : Login-Shell = NO, Serial Hardware = YES
# Interface Options → Camera        : Enable
```

## Installation

Picamera2 baut auf **libcamera** auf; die Python-Anbindung kommt unter Raspberry Pi OS per **`apt`**,
nicht zuverlässig allein durch `pip`. Zuerst Systempakete:

```bash
sudo apt update
sudo apt install -y python3-picamera2
```

Virtuelles Environment **mit Zugriff auf die apt-Python-Module** (sonst „libcamera nicht gefunden“):

```bash
cd ~/sia/Sender
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt

# LoRa-HAT einmalig konfigurieren (gleiche Parameter wie beim Empfänger!)
python lora_config.py
```

Optional prüfen, ob die Kamera-Imports funktionieren:

```bash
python3 -c "import libcamera; from picamera2 import Picamera2"
```

## Start

```bash
cd ~/sia/Sender
source venv/bin/activate

# Terminal 1: Sensordaten alle 30 s
python lora_sensor_sender.py

# Terminal 2: Kamerabild alle 10 min
python lora_image_sender.py
```

## Einzelne Sensoren testen

```bash
python dht22.py        # einmal messen
python dht22.py loop   # Dauerbetrieb
python ky053.py        # Windgeschwindigkeit live
```

## Intervalle anpassen

| Wert | Datei | Default |
|---|---|---|
| `SEND_INTERVAL` | `lora_sensor_sender.py` | 30 s |
| `IMAGE_SEND_INTERVAL_MINUTES` | `lora_image_sender.py` | 10 min |
| `IMAGE_SIZE`, `JPEG_QUALITY` | `lora_image_sender.py` | 460×259, Q=100 |


Eltako WS Ader 1 ──────── GND
Eltako WS Ader 2 ──┬───── A0 (KY-053)
                   │
                  10 kΩ
                   │
                   └───── 3V3 (KY-053 VDD)