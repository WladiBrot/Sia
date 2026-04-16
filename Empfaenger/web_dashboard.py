"""
Web-Dashboard für empfangene LoRa-Daten.

Zeigt in Echtzeit im Browser an:
- Temperatur, Luftfeuchtigkeit und Windgeschwindigkeit (aus latest_sensor.json)
- Das zuletzt empfangene Kamerabild (latest_image.jpg)
- Verlauf (letzte ~200 Messwerte aus sensor_history.json)

Die Seite pollt alle paar Sekunden neue Daten vom Server und aktualisiert
sich automatisch, sobald der Receiver neue Werte / ein neues Bild empfängt.

Start:
    cd ~/sia/Funkmodul
    python web_dashboard.py
Dann im Browser öffnen:  http://<Pi-IP>:5000
"""

import json
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_SENSOR_JSON = os.path.join(BASE_DIR, "latest_sensor.json")
LATEST_IMAGE_FILE = os.path.join(BASE_DIR, "latest_image.jpg")
HISTORY_JSON = os.path.join(BASE_DIR, "sensor_history.json")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))


def _read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/latest")
def api_latest():
    """Liefert die aktuellsten Sensordaten + Infos zum letzten Bild."""
    sensor = _read_json(LATEST_SENSOR_JSON) or {}

    image_info = None
    if os.path.exists(LATEST_IMAGE_FILE):
        mtime = os.path.getmtime(LATEST_IMAGE_FILE)
        image_info = {
            "url": f"/latest_image.jpg?v={int(mtime)}",
            "updated_at": datetime.fromtimestamp(mtime).isoformat(),
            "mtime": mtime,
        }

    return jsonify({
        "sensor": sensor,
        "image": image_info,
        "server_time": datetime.now().isoformat(),
    })


@app.route("/api/history")
def api_history():
    history = _read_json(HISTORY_JSON) or []
    return jsonify(history)


@app.route("/latest_image.jpg")
def latest_image():
    if not os.path.exists(LATEST_IMAGE_FILE):
        return ("Noch kein Bild empfangen.", 404)
    return send_from_directory(BASE_DIR, "latest_image.jpg")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("LoRa Web-Dashboard")
    print("=" * 50)
    print(f"Datenquelle: {BASE_DIR}")
    print("Öffne im Browser:  http://<Pi-IP>:5000")
    print("Beenden mit Strg+C\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
