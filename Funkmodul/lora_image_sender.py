"""
LoRa Bild-Sender für Raspberry Pi mit SX1268 HAT
Nimmt ein Foto mit der Kamera auf und sendet es über LoRa an einen Empfänger
"""

import time
import serial
from picamera2 import Picamera2
from PIL import Image
import io
import os
import base64

# --- LoRa-Konstanten ---
LORA_PORT = '/dev/ttyS0'
LORA_BAUDRATE = 9600
# Hinweis: Da wir jetzt Base64 (ASCII, zeilenbasiert) nutzen, wird jedes Paket ~33% größer.
# Daher MAX_PAYLOAD_SIZE etwas kleiner wählen, damit das LoRa-Paket nicht zu groß wird.
MAX_PAYLOAD_SIZE = 200  # Nutzdaten vor Base64; Base64 wird größer. Bei Bedarf weiter senken (120).
CHUNK_DELAY = 2  # Wartezeit zwischen Paketen in Sekunden (Duty Cycle)
START_DELAY = 1  # Wartezeit nach START-Nachricht
RESPONSE_TIMEOUT = 30.0  # Timeout für Antworten vom Receiver (Sekunden)
MAX_RETRANSMISSION_ROUNDS = 10  # Maximale Anzahl von Retransmission-Runden

# Bild-Komprimierungseinstellungen
IMAGE_SIZE = (460, 259)  # Zielgröße in Pixeln
JPEG_QUALITY = 100  # Qualität (1-100, niedriger = kleinere Datei)

# Intervall: Nach wie vielen Minuten das nächste Bild gesendet wird
IMAGE_SEND_INTERVAL_MINUTES = 10


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


def capture_image(picam2, output_filename):
    """
    Nimmt ein Foto mit der Kamera auf.
    
    Args:
        picam2: Picamera2-Instanz
        output_filename: Pfad zum Speichern des Fotos
        
    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        print("Initialisiere Kamera...")
        camera_config = picam2.create_still_configuration()
        picam2.configure(camera_config)
        picam2.start()
        time.sleep(2)  # Kamera-Warmlaufzeit
        
        print(f"Nehme Foto auf...")
        picam2.capture_file(output_filename)
        picam2.stop()
        
        print(f"✓ Foto aufgenommen: {output_filename}")
        return True
    except Exception as e:
        print(f"✗ Fehler beim Aufnehmen des Fotos: {e}")
        return False


def compress_image(input_filename):
    """
    Komprimiert das Bild stark für LoRa-Übertragung.
    
    Args:
        input_filename: Pfad zum Eingabebild
        
    Returns:
        Byte-Array mit komprimierten Bilddaten oder None bei Fehler
    """
    try:
        img = Image.open(input_filename)
        original_size = img.size
        print(f"Originalbildgröße: {original_size}")
        
        # Bild verkleinern
        img_resized = img.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
        print(f"Bild verkleinert auf: {IMAGE_SIZE}")
        
        # In Byte-Array komprimieren
        byte_arr = io.BytesIO()
        img_resized.save(byte_arr, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        compressed_data = byte_arr.getvalue()
        
        print(f"✓ Bild komprimiert: {len(compressed_data)} Bytes (Original: {os.path.getsize(input_filename)} Bytes)")
        return compressed_data
        
    except FileNotFoundError:
        print(f"✗ Datei nicht gefunden: {input_filename}")
        return None
    except Exception as e:
        print(f"✗ Fehler bei der Bildverarbeitung: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_chunk(lora_serial, chunk_data, index, total_chunks):
    """Sendet ein einzelnes Datenpaket."""
    # Metadaten für das Paket: CHUNK:<Index>/<Total>:
    metadata = f"CHUNK:{index}/{total_chunks}:".encode('utf-8')
    
    # Base64 encodieren
    chunk_b64 = base64.b64encode(chunk_data)
    packet = metadata + chunk_b64 + b"\n"
    
    # Senden über UART an das LoRa HAT
    lora_serial.write(packet)
    lora_serial.flush()
    
    print(f"✓ Gesendet: Paket {index+1}/{total_chunks} ({len(packet)} Bytes, Daten roh: {len(chunk_data)} Bytes, b64: {len(chunk_b64)} Bytes)")
    
    # WICHTIG: LoRa benötigt eine Wartezeit zwischen den Paketen (Duty Cycle)
    if index < total_chunks - 1:  # Keine Wartezeit nach dem letzten Paket
        time.sleep(CHUNK_DELAY)


def wait_for_response(lora_serial):
    """Wartet auf eine Antwort vom Receiver (ACK oder MISSING)."""
    start_time = time.time()
    
    while (time.time() - start_time) < RESPONSE_TIMEOUT:
        if lora_serial.in_waiting > 0:
            response = lora_serial.readline().strip()
            if response:
                if response.startswith(b"ACK:"):
                    return "ACK"
                elif response.startswith(b"MISSING:"):
                    # Parse fehlende Indizes
                    try:
                        # Format: MISSING:<Index1>,<Index2>,...:
                        missing_str = response.split(b":")[1].rstrip(b":")
                        missing_indices = [int(idx) for idx in missing_str.split(b",") if idx]
                        return ("MISSING", missing_indices)
                    except (IndexError, ValueError) as e:
                        print(f"✗ Fehler beim Parsen der MISSING-Nachricht: {e}")
                        return None
        time.sleep(0.1)
    
    return None  # Timeout


def send_data_via_lora(lora_serial, data):
    """
    Teilt die Bilddaten in LoRa-Pakete auf und sendet sie nacheinander.
    Wiederholt fehlende Pakete basierend auf Receiver-Feedback.
    
    Args:
        lora_serial: Serielle Schnittstelle zum LoRa HAT
        data: Byte-Array mit den Bilddaten
    """
    if not lora_serial or not data:
        print("✗ Senden fehlgeschlagen: Serielle Schnittstelle nicht bereit oder keine Daten.")
        return False

    total_chunks = (len(data) + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE

    # Geschätzte Dauer: START_DELAY + (Pakete × CHUNK_DELAY) + Ende/ACK
    estimated_seconds = START_DELAY + total_chunks * CHUNK_DELAY + 10
    if estimated_seconds >= 60:
        estimated_str = f"ca. {estimated_seconds // 60} Min. {estimated_seconds % 60} Sek."
    else:
        estimated_str = f"ca. {estimated_seconds} Sek."

    print(f"\n{'='*50}")
    print(f"Beginne Übertragung:")
    print(f"  - Gesamtgröße: {len(data)} Bytes")
    print(f"  - Anzahl Pakete: {total_chunks}")
    print(f"  - Paketgröße: max. {MAX_PAYLOAD_SIZE} Bytes")
    print(f"  - Geschätzte Dauer: {estimated_str}")
    print(f"{'='*50}\n")

    try:
        # START-Nachricht senden: START:<Gesamt-Bytes>:<Total-Pakete>:
        start_message = f"START:{len(data)}:{total_chunks}:".encode('utf-8') + b"\n"
        lora_serial.write(start_message)
        lora_serial.flush()
        print(f"✓ START-Nachricht gesendet: {start_message.decode('utf-8').strip()}")
        time.sleep(START_DELAY)

        # Alle Datenpakete senden (erste Runde)
        print("\n--- Erste Übertragung ---")
        for i in range(total_chunks):
            start = i * MAX_PAYLOAD_SIZE
            end = min((i + 1) * MAX_PAYLOAD_SIZE, len(data))
            chunk = data[start:end]
            send_chunk(lora_serial, chunk, i, total_chunks)

        # Abschlussmeldung senden
        end_message = b"ENDE_BILDUPLOAD\n"
        lora_serial.write(end_message)
        lora_serial.flush()
        print(f"✓ ENDE-Nachricht gesendet")
        
        # Warte auf Antwort vom Receiver
        retransmission_round = 0
        while retransmission_round < MAX_RETRANSMISSION_ROUNDS:
            print(f"\nWarte auf Antwort vom Receiver... (Runde {retransmission_round + 1})")
            response = wait_for_response(lora_serial)
            
            if response == "ACK":
                print(f"\n{'='*50}")
                print("✓ Übertragung erfolgreich abgeschlossen! Alle Pakete wurden empfangen.")
                print(f"{'='*50}\n")
                return True
            elif isinstance(response, tuple) and response[0] == "MISSING":
                missing_indices = response[1]
                retransmission_round += 1
                print(f"\n--- Retransmission Runde {retransmission_round} ---")
                print(f"  Fehlende Pakete: {missing_indices}")
                
                # Sende nur die fehlenden Pakete
                for idx in missing_indices:
                    if 0 <= idx < total_chunks:
                        start = idx * MAX_PAYLOAD_SIZE
                        end = min((idx + 1) * MAX_PAYLOAD_SIZE, len(data))
                        chunk = data[start:end]
                        send_chunk(lora_serial, chunk, idx, total_chunks)
                
                # Sende erneut ENDE-Nachricht
                lora_serial.write(end_message)
                lora_serial.flush()
                print(f"✓ ENDE-Nachricht erneut gesendet")
            else:
                print(f"✗ Timeout oder ungültige Antwort vom Receiver")
                print(f"  Versuche erneut...")
                retransmission_round += 1
                if retransmission_round < MAX_RETRANSMISSION_ROUNDS:
                    # Sende ENDE-Nachricht erneut
                    lora_serial.write(end_message)
                    lora_serial.flush()
                    time.sleep(1)
        
        print(f"\n✗ Maximale Anzahl von Retransmission-Runden erreicht ({MAX_RETRANSMISSION_ROUNDS})")
        return False

    except serial.SerialTimeoutException:
        print("✗ Timeout beim Senden über serielle Schnittstelle")
        return False
    except Exception as e:
        print(f"✗ Fehler beim Senden: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Hauptfunktion: Foto aufnehmen, senden, warten, wiederholen."""
    print("\n" + "="*50)
    print("LoRa Bild-Sender")
    print(f"Intervall: alle {IMAGE_SEND_INTERVAL_MINUTES} Minuten")
    print("="*50 + "\n")

    # Kamera und LoRa einmal initialisieren
    picam2 = Picamera2()
    temp_filename = "/tmp/lora_temp_foto.jpg"
    lora_serial = setup_lora_serial()
    if not lora_serial:
        print("✗ Programm beendet: LoRa-Schnittstelle konnte nicht geöffnet werden.")
        return

    try:
        while True:
            # Foto aufnehmen
            if not capture_image(picam2, temp_filename):
                print("✗ Foto konnte nicht aufgenommen werden. Nächster Versuch nach Intervall.")
            else:
                # Bild komprimieren
                image_bytes = compress_image(temp_filename)
                if image_bytes is not None:
                    success = send_data_via_lora(lora_serial, image_bytes)
                    if success:
                        print("✓ Bild erfolgreich übertragen!")
                    else:
                        print("✗ Fehler beim Übertragen des Bildes.")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            # Warten bis zum nächsten Bild
            wait_seconds = IMAGE_SEND_INTERVAL_MINUTES * 60
            print(f"\nNächstes Bild in {IMAGE_SEND_INTERVAL_MINUTES} Minuten...")
            time.sleep(wait_seconds)
    finally:
        lora_serial.close()
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        print("✓ Serielle Verbindung geschlossen")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgramm durch Benutzer beendet (Strg+C).")
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()

