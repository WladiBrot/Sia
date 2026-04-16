# Empfaenger-Pi – LoRa-Empfang & Web-Dashboard

Dieser Ordner gehört auf den **Empfänger-Raspberry-Pi** (z. B. zu Hause).
Er empfängt Sensordaten + Kamerabilder per LoRa und stellt sie in einem
Web-Dashboard live im Browser dar.

## Inhalt

| Datei | Zweck |
|---|---|
| `lora_image_receiver.py` | **Hauptskript 1** – empfängt kontinuierlich LoRa-Daten:<br>• Sensordaten → `latest_sensor.json`, `sensor_history.json`, `sensor_data_<ts>.txt`<br>• Bilder → `received_image_<ts>.jpg` + `latest_image.jpg` |
| `web_dashboard.py` | **Hauptskript 2** – Flask-Webserver, serviert Dashboard auf Port 5000. |
| `templates/index.html` | Dashboard-Oberfläche. Pollt alle 3 s `/api/latest`, aktualisiert Messwerte und Bild automatisch. |
| `lora_config.py` | Einmalige Konfiguration des SX1268-HAT (gleiche Parameter wie Sender!). |
| `requirements.txt` | Python-Abhängigkeiten für den Empfänger. |

## Hardware

- Raspberry Pi (jedes Modell reicht)
- Waveshare **SX1268 LoRa HAT** auf UART (`/dev/ttyS0`, 9600 Baud), Jumper M0=M1=GND

## System vorbereiten (einmalig)

```bash
sudo raspi-config
# Interface Options → Serial Port : Login-Shell = NO, Serial Hardware = YES
```

## Installation

```bash
cd ~/sia/Empfaenger
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# LoRa-HAT einmalig konfigurieren (gleiche Parameter wie beim Sender!)
python lora_config.py
```

## Start

```bash
cd ~/sia/Empfaenger
source venv/bin/activate

# Terminal 1: LoRa-Empfang (schreibt Dateien für das Dashboard)
python lora_image_receiver.py

# Terminal 2: Web-Dashboard
python web_dashboard.py
```

Dann im Browser öffnen: **`http://<Pi-IP>:5000`**

Das Dashboard zeigt:

- aktuelle **Temperatur**, **Luftfeuchte** und **Windgeschwindigkeit** als Kacheln
- das zuletzt empfangene **Kamerabild** (wird automatisch ausgetauscht, sobald ein neues eintrifft)
- einen **Verlauf** der letzten ~30 Messungen
- einen Live-Indikator (grün = Daten jünger als 90 s)

## API-Endpunkte des Dashboards

| URL | Inhalt |
|---|---|
| `/` | HTML-Dashboard |
| `/api/latest` | JSON mit letztem Sensordatensatz + Bild-URL |
| `/api/history` | JSON-Array mit bis zu 200 Einträgen Verlauf |
| `/latest_image.jpg` | Das zuletzt empfangene Kamerabild |

## Vom Receiver erzeugte Dateien

Alle im gleichen Ordner wie das Skript:

| Datei | Beschreibung |
|---|---|
| `latest_sensor.json` | Letzter Sensordatensatz (Dashboard-Eingabe) |
| `latest_image.jpg` | Zuletzt empfangenes Bild (Dashboard-Eingabe) |
| `sensor_history.json` | Rollender Verlauf, max. 200 Einträge |
| `sensor_data_YYYYmmdd_HHMMSS.txt` | Archivdatei je Datensatz |
| `received_image_YYYYmmdd_HHMMSS.jpg` | Archivdatei je Bild |

## LoRa-Protokoll (zur Info)

| Nachricht | Richtung | Bedeutung |
|---|---|---|
| `START:<bytes>:<total>:` | Sender → Empfänger | Ankündigung eines Bilds |
| `CHUNK:<i>/<total>:<base64>` | Sender → Empfänger | Einzelpaket Bilddaten |
| `ENDE_BILDUPLOAD` | Sender → Empfänger | Ende des Bilds |
| `ACK:` | Empfänger → Sender | Alles empfangen |
| `MISSING:<i1>,<i2>,…:` | Empfänger → Sender | Fehlende Pakete nachsenden |
| `SENSOR_DATA:{json}` | Sender → Empfänger | Wetterdaten |
