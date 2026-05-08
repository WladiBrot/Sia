# SIA – Wetterstation & LoRa-Bildübertragung

Zwei Raspberry Pis, die per LoRa (433 MHz) kommunizieren: der **Sender-Pi** misst
Temperatur, Luftfeuchte und Wind und schickt zusätzlich Kamerabilder. Der
**Empfänger-Pi** speichert alles und zeigt es in einem **Web-Dashboard im Browser**
live an – das Dashboard aktualisiert sich automatisch, sobald neue Daten oder
ein neues Bild eintreffen.

```
  [Sender-Pi]                              [Empfaenger-Pi]
 ┌──────────────┐     LoRa 433 MHz      ┌──────────────┐   Browser
 │ DHT22        │   ───────────────►    │ lora_image_  │  ┌────────┐
 │ KY-053       │                       │  receiver.py │◄─┤  HTML  │
 │ Pi-Kamera    │                       │              │  │ Dash-  │
 │ lora_*_sender│                       │ web_dash-    │──►  board │
 └──────────────┘                       │  board.py    │  └────────┘
                                        └──────────────┘
```

## Ordnerstruktur

```
sia/
├── Sender/              ← auf den Sender-Pi kopieren
│   ├── dht22.py
│   ├── ky053.py
│   ├── lora_sensor_sender.py
│   ├── lora_image_sender.py
│   ├── lora_config.py
│   ├── arduino/
│   │   ├── nurwindsensor.ino
│   │   └── WindSensorundTempundFeuchtigkeit.ino
│   ├── requirements.txt
│   └── README.md
│
├── Empfaenger/          ← auf den Empfaenger-Pi kopieren
│   ├── lora_image_receiver.py
│   ├── web_dashboard.py
│   ├── lora_config.py
│   ├── templates/
│   │   └── index.html
│   ├── requirements.txt
│   └── README.md
│
├── guenterderhueter/    ← eigenständiger Arduino-Sketch (Relaissteuerung)
│   ├── guenterderhueter.ino
│   └── README.md
│
└── README.md            ← diese Datei
```

Jeder der beiden Pi-Ordner ist **vollständig autark**: er enthält alle Python-Skripte
und eine eigene `requirements.txt`. Auf dem jeweiligen Pi reicht es, nur den
passenden Ordner zu haben.

| Ordner | Wohin? | Eigenständige Anleitung |
|---|---|---|
| `Sender/` | Pi im Feld (mit Kamera, DHT22, Anemometer) | [Sender/README.md](Sender/README.md) |
| `Empfaenger/` | Pi zu Hause (mit Bildschirm / Browser) | [Empfaenger/README.md](Empfaenger/README.md) |
| `guenterderhueter/` | Standalone-Arduino | [guenterderhueter/README.md](guenterderhueter/README.md) |

## Schnellstart

### Sender-Pi

Für **`lora_image_sender.py`** (Picamera2) zuerst `sudo apt install python3-picamera2` (zieht libcamera nach) und das venv mit `--system-site-packages` anlegen (siehe [Sender/README.md](Sender/README.md)).

```bash
cd ~/sia/Sender
python3 -m venv venv --system-site-packages && source venv/bin/activate
pip install -r requirements.txt
python lora_config.py           # einmalig, gleiche Parameter wie Empfaenger

python lora_sensor_sender.py    # Terminal 1 – Sensordaten
python lora_image_sender.py     # Terminal 2 – Kamerabilder
```

### Empfaenger-Pi

```bash
cd ~/sia/Empfaenger
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python lora_config.py           # einmalig, gleiche Parameter wie Sender

python lora_image_receiver.py   # Terminal 1 – Empfang
python web_dashboard.py         # Terminal 2 – Web-Dashboard
```

Dashboard im Browser öffnen: **`http://<Empfaenger-Pi-IP>:5000`**

## Hardware-Übersicht

| Sensor / Modul | Pi-Pins (BCM) | Hinweis |
|---|---|---|
| DHT22 VCC / GND / DATA | 3,3 V / GND / **GPIO 7** (Pin 26) | `DHT_PIN` in `dht22.py` anpassbar |
| KY-053 (ADS1115) I²C | SDA GPIO 2, SCL GPIO 3 | Adresse 0x48 |
| Anemometer-Signal | → A0 am KY-053 | – |
| SX1268 LoRa HAT (UART) | `/dev/ttyS0`, 9600 Baud | Jumper M0=M1=GND |

Details zur Verdrahtung findet ihr in den jeweiligen Ordner-READMEs.

## Sendeintervalle

| Wert | Datei | Default |
|---|---|---|
| Sensordaten | `Sender/lora_sensor_sender.py` → `SEND_INTERVAL` | 30 s |
| Bilder | `Sender/lora_image_sender.py` → `IMAGE_SEND_INTERVAL_MINUTES` | 10 min |
| Dashboard-Polling | `Empfaenger/templates/index.html` → `POLL_MS` | 3 s |


# Sensordaten-Sender bei Boot starten
@reboot /home/pi/sia/Sender/venv/bin/python /home/pi/sia/Sender/lora_sensor_sender.py >> /home/pi/sia/Sender/sensor.log 2>&1

# Kamera-Sender bei Boot starten
@reboot /home/pi/sia/Sender/venv/bin/python /home/pi/sia/Sender/lora_image_sender.py >> /home/pi/sia/Sender/image.log 2>&1
