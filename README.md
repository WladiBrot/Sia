# SIA – Sensor & Bildübertragung per LoRa

| Ordner | Inhalt |
|---|---|
| `Funkmodul/` | LoRa Sender (Bild + Sensor) und Empfänger |
| `Windradar/` | Anemometer mit KY-053 / ADS1115 |
| `sensor/` | DHT22 Temperatur & Luftfeuchtigkeit |

---

## 1. DHT22 Sensor

### Hardware

| Raspberry Pi | DHT22 (AM2302) |
|---|---|
| Pin 1 (3,3V) oder Pin 2 (5V) | VCC (Pin 1) |
| Pin 7 (GPIO 4) oder Pin 26 (GPIO 7) | DATA (Pin 2) |
| – | NC (Pin 3) – nicht verbinden |
| Pin 6 (GND) | GND (Pin 4) |

*BCM-Nummerierung: Pin 7 = GPIO 4, Pin 26 = GPIO 7. In `sensor/dht22_sensor.py` `DHT_PIN` anpassen (4 oder 7).*

Optional: 4,7–10 kΩ Pull-up zwischen DATA und VCC bei langen Kabeln.

### Starten

```bash
cd ~/sia/sensor
source venv/bin/activate
python dht22_sensor.py          # Einzelmessung
python dht22_sensor.py loop     # Dauerbetrieb
```

---

## 2. Anemometer (KY-053 / ADS1115)

### Hardware

| Raspberry Pi 4 | KY-053 / COM-KY053ADC |
|---|---|
| Pin 1 (3,3V) | VDD / V+ |
| Pin 6 (GND) | GND / 0V |
| Pin 3 (SDA, GPIO 2) | SDA |
| Pin 5 (SCL, GPIO 3) | SCL |
| – | A0 ← Anemometer-Signal |

I2C aktivieren: `sudo raspi-config` → Interface Options → I2C → Enable.

Alert/ADDR-Pins am Modul unverbunden lassen (Standard-Adresse 0x48).

### I2C prüfen

```bash
sudo apt-get install -y i2c-tools
sudo i2cdetect -y 1
# → 0x48 muss erscheinen
```

### Starten

```bash
cd ~/sia/Windradar
source venv/bin/activate
python anemometer_ky053.py
```

---

## 3. LoRa Funkmodul (SX1268 HAT)

### Manueller Start

```bash
cd ~/sia/Funkmodul

# Sensor-Sender (DHT22 + Anemometer):
./start.sh sender

# Bild-Sender (Kamera):
./start.sh image

# Empfänger (Bilder + Sensordaten):
./start.sh receiver
```

### Autostart mit Debug-Konsole

**Sender-Pi** (Sensor + Bild):
```bash
chmod +x install-autostart.sh
./install-autostart.sh sender
```

**Receiver-Pi**:
```bash
chmod +x install-autostart.sh
./install-autostart.sh receiver
```

Voraussetzung: `lxterminal` (meist vorinstalliert, sonst `sudo apt install lxterminal`).

Deaktivieren: `.desktop`-Dateien aus `~/.config/autostart/` entfernen.

Automatischer Desktop-Login: *Einstellungen → Raspberry Pi-Konfiguration → System* → „Automatisch als Benutzer anmelden" aktivieren.

### Sendeintervalle

- Sensordaten: alle 30 Sek. (`SEND_INTERVAL` in `lora_sensor_sender.py`)
- Bilder: alle 10 Min. (`IMAGE_SEND_INTERVAL_MINUTES` in `lora_image_sender.py`)

---

## Abhängigkeiten installieren

```bash
cd ~/sia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Wichtig:** Verwende **kein** `sudo` vor `pip` – sonst wird die System-Python-Umgebung genutzt und du erhältst den Fehler „externally-managed-environment“. In der aktivierten venv reicht `pip install` ohne sudo.

Falls `python3 -m venv venv` fehlschlägt, zuerst installieren:
```bash
sudo apt install python3-full
```

## Kurz-Checkliste

- [ ] I2C in `raspi-config` aktiviert
- [ ] DHT22 verdrahtet (GPIO 4)
- [ ] KY-053 verdrahtet (I2C + A0)
- [ ] `i2cdetect -y 1` zeigt 0x48
- [ ] SX1268 LoRa HAT aufgesteckt, Jumper korrekt
- [ ] venv aktiviert, Pakete installiert
