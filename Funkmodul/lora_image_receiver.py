"""
LoRa Bild- und Sensor-Empfänger für Raspberry Pi mit SX1268 HAT
Empfängt Bildpakete über LoRa und setzt sie zu einem vollständigen Bild zusammen.
Empfängt außerdem SENSOR_DATA (DHT22 + Anemometer) vom lora_sensor_sender.
"""

import serial
import time
import json
from PIL import Image
import os
import base64
from datetime import datetime

# --- LoRa-Konstanten ---
LORA_PORT = '/dev/ttyS0'
LORA_BAUDRATE = 9600
TIMEOUT_SECONDS = 1500  # Timeout für den Empfang aller Pakete
RECEIVE_DELAY = 0.1  # Wartezeit zwischen Leseversuchen
AUTO_SAVE_DELAY = 2.0  # Sekunden nach letztem Paket, bevor automatisch gespeichert wird
RESPONSE_TIMEOUT = 30  # Timeout für Antworten vom Sender (Sekunden)
# Für Dauer-Schätzung (muss mit Sender übereinstimmen)
CHUNK_DELAY_ESTIMATE = 2  # Sekunden zwischen Paketen (Duty Cycle)
START_DELAY_ESTIMATE = 1  # Sekunden nach START-Nachricht

# Empfangs-Status
received_chunks = {}
total_chunks = None
image_size_expected = 0
last_packet_time = None
start_time = None
waiting_for_retransmission = False  # Flag: Warten wir auf Retransmission-Pakete?


def setup_lora_serial():
    """Initialisiert die serielle Schnittstelle für das LoRa HAT."""
    try:
        lora_serial = serial.Serial(
            port=LORA_PORT,
            baudrate=LORA_BAUDRATE,
            timeout=1,
            write_timeout=5
        )
        print(f"✓ LoRa-Schnittstelle auf {LORA_PORT} geöffnet (Baudrate: {LORA_BAUDRATE})")
        time.sleep(0.5)  # Kurze Initialisierungszeit
        return lora_serial
    except serial.SerialException as e:
        print(f"✗ FEHLER: Kann serielle Schnittstelle nicht öffnen: {e}")
        print(f"  Stelle sicher, dass {LORA_PORT} existiert und berechtigt ist.")
        return None
    except Exception as e:
        print(f"✗ Unerwarteter Fehler beim Öffnen der seriellen Schnittstelle: {e}")
        return None


def reset_reception_state():
    """Setzt den Empfangsstatus zurück."""
    global received_chunks, total_chunks, image_size_expected, last_packet_time, start_time, waiting_for_retransmission
    received_chunks = {}
    total_chunks = None
    image_size_expected = 0
    last_packet_time = None
    start_time = None
    waiting_for_retransmission = False


def process_start_message(packet):
    """Verarbeitet eine START-Nachricht."""
    global total_chunks, image_size_expected, start_time
    
    try:
        # Format: START:<Gesamt-Bytes>:<Total-Pakete>:
        parts = packet.split(b":")
        if len(parts) >= 3:
            # Erst Zustand zurücksetzen, dann neue Werte setzen
            reset_reception_state()  # Alte Daten löschen
            image_size_expected = int(parts[1])
            total_chunks = int(parts[2])
            start_time = time.time()
            
            # Geschätzte Dauer bis Bild komplett (Sender braucht START_DELAY + Pakete×CHUNK_DELAY + Ende/ACK)
            estimated_seconds = START_DELAY_ESTIMATE + total_chunks * CHUNK_DELAY_ESTIMATE + 10
            if estimated_seconds >= 60:
                estimated_str = f"ca. {estimated_seconds // 60} Min. {estimated_seconds % 60} Sek."
            else:
                estimated_str = f"ca. {estimated_seconds} Sek."

            print(f"\n{'='*50}")
            print(f"✓ START-Nachricht empfangen:")
            print(f"  - Erwartete Pakete: {total_chunks}")
            print(f"  - Erwartete Gesamtgröße: {image_size_expected} Bytes")
            print(f"  - Geschätzte Dauer bis Bild komplett: {estimated_str}")
            print(f"{'='*50}\n")

            return True
        else:
            print(f"✗ Ungültige START-Nachricht: {packet}")
            return False
    except (IndexError, ValueError) as e:
        print(f"✗ Fehler beim Parsen der START-Nachricht: {e}")
        print(f"  Paket: {packet}")
        return False


def process_chunk_message(packet):
    """Verarbeitet eine CHUNK-Nachricht."""
    global received_chunks, total_chunks, last_packet_time
    
    try:
        # Format: CHUNK:<Index>/<Total>:<Daten>
        first_colon = packet.find(b":")
        second_colon = packet.find(b":", first_colon + 1)
        
        if first_colon == -1 or second_colon == -1:
            print(f"✗ Ungültiges CHUNK-Format: Konnte Doppelpunkte nicht finden")
            return False
        
        # Extrahiere Metadaten und Daten (Daten sind Base64-kodiert und enden mit \n)
        meta_data = packet[first_colon + 1:second_colon]
        data_chunk = packet[second_colon + 1:]
        
        # Parse Index und Total
        index_str, total_str = meta_data.split(b'/')
        index = int(index_str)
        total = int(total_str)
        
        # Base64 dekodieren (vorher Zeilenende entfernen)
        data_chunk = data_chunk.rstrip(b"\r\n")
        try:
            decoded_bytes = base64.b64decode(data_chunk, validate=True)
        except Exception as e:
            print(f"✗ Base64-Dekodierung fehlgeschlagen für Paket {index}: {e}")
            return False

        # Speichere das dekodierte Paket (Rohdaten)
        received_chunks[index] = decoded_bytes
        total_chunks = total
        last_packet_time = time.time()
        
        # Fortschrittsanzeige
        progress = len(received_chunks)
        percentage = (progress / total) * 100 if total > 0 else 0
        print(f"✓ Empfangen: Paket {progress}/{total} ({percentage:.1f}%) - Rohdaten {len(decoded_bytes)} Bytes")
        
        return True
        
    except (ValueError, IndexError) as e:
        print(f"✗ Fehler beim Parsen des CHUNK-Pakets: {e}")
        print(f"  Paket (erste 100 Bytes): {packet[:100]}")
        return False


def check_missing_packets():
    """Prüft, welche Pakete fehlen und gibt eine Liste zurück."""
    global received_chunks, total_chunks
    
    if total_chunks is None:
        return None
    
    missing = sorted(set(range(total_chunks)) - set(received_chunks.keys()))
    return missing


def send_missing_packets_request(lora_serial, missing_indices):
    """Sendet eine MISSING-Nachricht mit den fehlenden Paket-Indizes."""
    try:
        # Format: MISSING:<Index1>,<Index2>,...:
        missing_str = ",".join(str(idx) for idx in missing_indices)
        missing_message = f"MISSING:{missing_str}:".encode('utf-8') + b"\n"
        lora_serial.write(missing_message)
        lora_serial.flush()
        print(f"✓ MISSING-Nachricht gesendet: {len(missing_indices)} fehlende Pakete")
        print(f"  Fehlende Indizes: {missing_indices}")
        return True
    except Exception as e:
        print(f"✗ Fehler beim Senden der MISSING-Nachricht: {e}")
        return False


def send_ack_message(lora_serial):
    """Sendet eine ACK-Nachricht, wenn alle Pakete empfangen wurden."""
    try:
        ack_message = b"ACK:\n"
        lora_serial.write(ack_message)
        lora_serial.flush()
        print(f"✓ ACK-Nachricht gesendet (alle Pakete empfangen)")
        return True
    except Exception as e:
        print(f"✗ Fehler beim Senden der ACK-Nachricht: {e}")
        return False


# Verzeichnis für Sensordaten-TXT-Dateien (gleicher Ordner wie Skript)
SENSOR_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SENSOR_DATA_FILENAME = "sensor_data.txt"


def process_sensor_data(packet):
    """Verarbeitet SENSOR_DATA-Nachrichten (DHT22 + Anemometer vom lora_sensor_sender).
    Schreibt die Daten in eine TXT-Datei und benennt sie mit Zeitstempel um.
    """
    try:
        # Format: SENSOR_DATA:{"temp_c":23.5,"humidity":65,"wind_kmh":12.3,"timestamp":"..."}
        json_str = packet.split(b"SENSOR_DATA:", 1)[1].rstrip(b"\r\n").decode("utf-8")
        data = json.loads(json_str)

        parts = []
        if "temp_c" in data:
            parts.append(f"Temperatur: {data['temp_c']} °C")
        if "humidity" in data:
            parts.append(f"Luftfeuchtigkeit: {data['humidity']} %")
        if "wind_kmh" in data:
            parts.append(f"Wind: {data['wind_kmh']} km/h")
        ts = data.get("timestamp", "")
        if ts:
            parts.append(f"({ts})")

        print(f"\n✓ Sensordaten empfangen: {' | '.join(parts)}\n")

        # In TXT-Datei schreiben
        filepath = os.path.join(SENSOR_DATA_DIR, SENSOR_DATA_FILENAME)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"sensor_data_{timestamp_str}.txt"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Sensordaten vom {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 40 + "\n")
            if "temp_c" in data:
                f.write(f"Temperatur:      {data['temp_c']} °C\n")
            if "humidity" in data:
                f.write(f"Luftfeuchtigkeit: {data['humidity']} %\n")
            if "wind_kmh" in data:
                f.write(f"Wind:           {data['wind_kmh']} km/h\n")
            f.write(f"Zeitstempel:    {ts}\n")

        # Datei mit Zeitstempel umbenennen
        new_filepath = os.path.join(SENSOR_DATA_DIR, new_filename)
        os.rename(filepath, new_filepath)
        print(f"✓ Gespeichert: {new_filename}\n")

        return True
    except (IndexError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"✗ Fehler beim Parsen der SENSOR_DATA: {e}")
        return False
    except OSError as e:
        print(f"✗ Fehler beim Schreiben der Sensordaten: {e}")
        return False


def process_end_message(lora_serial):
    """Verarbeitet eine ENDE-Nachricht, prüft fehlende Pakete und sendet entsprechende Antwort."""
    global received_chunks, total_chunks, image_size_expected, waiting_for_retransmission
    
    print(f"\n✓ ENDE-Nachricht empfangen")
    print(f"  Empfangene Pakete: {len(received_chunks)}/{total_chunks}")
    
    # Prüfen, ob alle Pakete empfangen wurden
    if total_chunks is None:
        print("✗ Keine START-Nachricht empfangen!")
        return False
    
    missing = check_missing_packets()
    
    if missing:
        # Es fehlen noch Pakete - sende MISSING-Nachricht
        print(f"✗ Fehlende Pakete: {missing}")
        send_missing_packets_request(lora_serial, missing)
        waiting_for_retransmission = True  # Wir warten jetzt auf Retransmission
        return False  # Noch nicht fertig
    else:
        # Alle Pakete sind da - sende ACK und erstelle Bild
        print(f"✓ Alle Pakete empfangen!")
        waiting_for_retransmission = False
        send_ack_message(lora_serial)
        return create_image_from_chunks()


def create_image_from_chunks():
    """Setzt das Bild aus den empfangenen Chunks zusammen und speichert es."""
    global received_chunks, total_chunks, image_size_expected
    
    try:
        print("\nSetze Bild zusammen...")
        
        # Bild zusammensetzen in der richtigen Reihenfolge
        sorted_chunks = []
        for i in range(total_chunks):
            if i in received_chunks:
                sorted_chunks.append(received_chunks[i])
            else:
                print(f"✗ FEHLER: Paket {i} fehlt trotz Prüfung!")
                return False
        
        full_image_data = b"".join(sorted_chunks)
        
        print(f"✓ Zusammengesetzt: {len(full_image_data)} Bytes (erwartet: {image_size_expected})")
        
        # Validierung
        if len(full_image_data) != image_size_expected:
            print(f"⚠ Größenabweichung: {abs(len(full_image_data) - image_size_expected)} Bytes")
        
        # Bild speichern mit Zeitstempel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"received_image_{timestamp}.jpg"
        
        # Vollständiger Pfad für bessere Sichtbarkeit
        output_path = os.path.abspath(output_filename)
        
        with open(output_filename, "wb") as f:
            f.write(full_image_data)
        
        print(f"✓ Bild erfolgreich gespeichert:")
        print(f"  Dateiname: {output_filename}")
        print(f"  Vollständiger Pfad: {output_path}")
        print(f"  Größe: {len(full_image_data)} Bytes")
        
        # Bild validieren und anzeigen
        try:
            img = Image.open(output_filename)
            print(f"✓ Bild validiert: Größe {img.size}, Format: {img.format}")
            # img.show()  # Auskommentieren, wenn X11 verfügbar ist
        except Exception as e:
            print(f"⚠ Bild gespeichert, aber Validierung fehlgeschlagen: {e}")
            print(f"  Möglicherweise ist das Bild beschädigt.")
        
        return True
        
    except Exception as e:
        print(f"✗ Fehler beim Zusammensetzen des Bildes: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_timeout():
    """Prüft, ob ein Timeout beim Empfang aufgetreten ist."""
    global start_time, last_packet_time, TIMEOUT_SECONDS
    
    if start_time is None:
        return False
    
    current_time = time.time()
    
    # Timeout, wenn seit Start zu viel Zeit vergangen ist
    if (current_time - start_time) > TIMEOUT_SECONDS:
        return True
    
    # Timeout, wenn seit letztem Paket zu viel Zeit vergangen ist (und wir bereits Pakete haben)
    if last_packet_time is not None and len(received_chunks) > 0:
        if (current_time - last_packet_time) > (TIMEOUT_SECONDS / 2):
            return True
    
    return False


def check_all_packets_received():
    """Prüft, ob alle Pakete empfangen wurden und ob automatisch gespeichert werden soll."""
    global total_chunks, received_chunks, last_packet_time, AUTO_SAVE_DELAY
    
    if total_chunks is None or len(received_chunks) == 0:
        return False
    
    # Prüfe, ob alle Pakete empfangen wurden
    if len(received_chunks) >= total_chunks:
        # Warte eine kurze Zeit nach dem letzten Paket, falls noch Pakete kommen
        if last_packet_time is not None:
            current_time = time.time()
            if (current_time - last_packet_time) >= AUTO_SAVE_DELAY:
                return True
    
    return False


def reconnect_serial():
    """Versucht die serielle Schnittstelle neu zu verbinden."""
    try:
        lora = setup_lora_serial()
        if lora:
            print("✓ Serielle Verbindung wiederhergestellt")
            return lora
    except Exception as e:
        print(f"✗ Reconnect fehlgeschlagen: {e}")
    return None


def main():
    """Hauptfunktion: Empfängt kontinuierlich Bildpakete."""
    print("\n" + "="*50)
    print("LoRa Bild-Empfänger")
    print("="*50 + "\n")
    
    lora_serial = setup_lora_serial()
    if not lora_serial:
        print("✗ Programm beendet: LoRa-Schnittstelle konnte nicht geöffnet werden.")
        return
    
    print("Warte auf Bildpakete und Sensordaten...\n")
    
    try:
        while True:
            try:
                # in_waiting kann OSError [Errno 5] werfen bei getrennter/instabiler Hardware
                if lora_serial.in_waiting > 0:
                    # LoRa-Daten lesen (readline kann ebenfalls I/O-Fehler werfen)
                    received_packet = lora_serial.readline().strip()
                    
                    if received_packet:
                        
                        # START-Nachricht verarbeiten
                        if received_packet.startswith(b"START:"):
                            process_start_message(received_packet)

                        # SENSOR_DATA-Nachricht verarbeiten (DHT22 + Anemometer)
                        elif received_packet.startswith(b"SENSOR_DATA:"):
                            process_sensor_data(received_packet)
                        
                        # CHUNK-Nachricht verarbeiten
                        elif b"CHUNK:" in received_packet:
                            process_chunk_message(received_packet)
                            # Wenn wir auf Retransmission warten und jetzt alle Pakete haben, prüfe automatisch
                            if waiting_for_retransmission:
                                missing = check_missing_packets()
                                if not missing:
                                    # Alle Pakete sind jetzt da - sende ACK und erstelle Bild
                                    print(f"\n✓ Alle Pakete nach Retransmission empfangen!")
                                    waiting_for_retransmission = False
                                    send_ack_message(lora_serial)
                                    if create_image_from_chunks():
                                        print(f"\n{'='*50}")
                                        print("✓ Bild erfolgreich empfangen und gespeichert!")
                                        print(f"{'='*50}\n")
                                        reset_reception_state()
                                        print("Warte auf nächstes Bild...\n")
                        
                        # ENDE-Nachricht verarbeiten
                        elif received_packet.startswith(b"ENDE_BILDUPLOAD"):
                            if process_end_message(lora_serial):
                                print(f"\n{'='*50}")
                                print("✓ Bild erfolgreich empfangen und gespeichert!")
                                print(f"{'='*50}\n")
                                # Zurücksetzen für nächstes Bild
                                reset_reception_state()
                                print("Warte auf nächstes Bild...\n")
                            else:
                                # Es fehlen noch Pakete - warte auf erneute Übertragung
                                print("  Warte auf fehlende Pakete...\n")
                
                # Prüfe, ob alle Pakete empfangen wurden (automatisches Speichern ohne ENDE-Nachricht)
                # HINWEIS: Mit dem neuen Protokoll sollte immer eine ENDE-Nachricht kommen
                # Diese Funktion bleibt als Fallback, sendet aber keine ACK/MISSING
                if check_all_packets_received():
                    print(f"\n✓ Alle Pakete empfangen ({len(received_chunks)}/{total_chunks})")
                    print("  Warte auf ENDE-Nachricht für Protokoll...")
                    # Nicht automatisch speichern, sondern auf ENDE-Nachricht warten
                
                # Timeout-Prüfung
                elif check_timeout():
                    if start_time is not None:
                        # Wenn wir Pakete haben, versuche trotzdem zu speichern
                        if len(received_chunks) > 0 and total_chunks is not None:
                            print(f"\n⚠ Timeout erreicht, aber {len(received_chunks)}/{total_chunks} Pakete empfangen")
                            print("  Versuche Bild trotzdem zu speichern...")
                            if process_end_message(lora_serial):
                                print(f"\n{'='*50}")
                                print("✓ Bild gespeichert (möglicherweise unvollständig)")
                                print(f"{'='*50}\n")
                            else:
                                print("\n✗ Konnte Bild nicht speichern.\n")
                        else:
                            print(f"\n✗ Timeout: Keine vollständige Übertragung innerhalb von {TIMEOUT_SECONDS} Sekunden")
                            print(f"  Empfangene Pakete: {len(received_chunks)}/{total_chunks if total_chunks else '?'}")
                        reset_reception_state()
                        print("Warte auf neues Bild...\n")
                
                time.sleep(RECEIVE_DELAY)
                
            except KeyboardInterrupt:
                print("\n\nProgramm durch Benutzer beendet.")
                break
            except (OSError, serial.SerialException) as e:
                # I/O-Fehler (z.B. Errno 5) bei getrennter/instabiler Hardware
                print(f"\n⚠ I/O-Fehler bei serieller Schnittstelle: {e}")
                print("  Versuche Verbindung wiederherzustellen...")
                try:
                    lora_serial.close()
                except Exception:
                    pass
                lora_serial = None
                for attempt in range(1, 6):
                    print(f"  Reconnect-Versuch {attempt}/5...")
                    lora_serial = reconnect_serial()
                    if lora_serial:
                        break
                    time.sleep(3)
                if not lora_serial:
                    print("✗ Konnte Verbindung nicht wiederherstellen. Beende Programm.")
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"✗ Ein Fehler ist aufgetreten: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)  # Kurze Pause vor erneutem Versuch
                
    finally:
        if lora_serial:
            lora_serial.close()
        print("✓ Serielle Verbindung geschlossen")


if __name__ == "__main__":
    main()

