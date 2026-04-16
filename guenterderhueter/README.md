# Günter der Hüter – Relais-Steuerung

Kleiner Arduino-Sketch („Günter"), der anhand einer analog gemessenen Spannung
ein Relais schaltet. Schwellenwert: **4,15 V**.

## Datei

| Datei | Beschreibung |
|---|---|
| `guenterderhueter.ino` | Arduino-Sketch: misst Spannung an `A0`, schaltet Relais an `D7`. |

## Hardware / Verdrahtung

| Arduino | Bauteil |
|---|---|
| `A0` | Spannungseingang (0 – 5 V, z. B. Solarpanel / Spannungsteiler) |
| `D7` | Relais-Signal (IN) |
| `5V` | VCC Relaismodul |
| `GND` | GND Relaismodul / Spannungsquelle |

> **Achtung:** `A0` misst maximal 5 V. Höhere Spannungen unbedingt über einen
> Spannungsteiler auf diesen Bereich herunterteilen.

## Verhalten

```
Spannung = analogRead(A0) * (5.0 / 1023.0)

Spannung ≥ 4,15 V  → Relais EIN
Spannung  < 4,15 V → Relais AUS
```

Ausgabe über `Serial.println(...)` mit 9600 Baud (Spannung und Zustandswechsel).

Nach jedem Schaltvorgang wartet der Sketch 2 s, um Kontakt-Flattern zu vermeiden.

## Upload

1. Arduino IDE öffnen
2. Board & Port auswählen
3. `guenterderhueter.ino` öffnen und hochladen
4. Seriellen Monitor auf 9600 Baud öffnen, um die Spannung mitzulesen
