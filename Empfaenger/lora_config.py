"""
SX1268 LoRa HAT Konfigurationsskript
Konfiguriert das LoRa-Modul mit den richtigen Parametern für die Bildübertragung

WICHTIG: Beide Raspberry Pis müssen mit den GLEICHEN Parametern konfiguriert werden!
"""

import serial
import time

# --- Serielle Schnittstelle ---
LORA_PORT = '/dev/ttyS0'
LORA_BAUDRATE = 9600

# --- LoRa-Parameter (MÜSSEN auf beiden Geräten identisch sein!) ---
# Diese Parameter bestimmen Reichweite, Geschwindigkeit und Zuverlässigkeit

FREQUENCY = 433.0  # Frequenz in MHz (433 MHz für Europa, 868 MHz auch möglich)
SPREADING_FACTOR = 7  # Spreading Factor (7-12, niedriger = schneller, weniger Reichweite)
BANDWIDTH = 125  # Bandbreite in kHz (125, 250, 500)
CODING_RATE = 5  # Coding Rate (5-8, höher = mehr Fehlerkorrektur)
TX_POWER = 14  # Sendeleistung in dBm (2-14, höher = mehr Reichweite, mehr Strom)
PREAMBLE_LENGTH = 8  # Präambel-Länge (typisch 8)
SYNC_WORD = 0x12  # Sync Word (0x12 ist Standard, muss identisch sein)
CRC_ENABLED = True  # CRC (Cyclic Redundancy Check) aktivieren

# --- AT-Befehle für SX1268 (abhängig vom HAT-Hersteller) ---
# Hinweis: Verschiedene HATs verwenden unterschiedliche AT-Befehle
# Dies ist ein generisches Beispiel - passen Sie es an Ihr HAT an


def send_at_command(ser, command, expected_response=None, timeout=2):
    """
    Sendet einen AT-Befehl und wartet auf Antwort.
    
    Args:
        ser: Serielle Schnittstelle
        command: AT-Befehl als String
        expected_response: Erwartete Antwort (optional)
        timeout: Timeout in Sekunden
        
    Returns:
        Antwort vom Modul oder None bei Fehler
    """
    try:
        # Sende Befehl
        cmd = (command + '\r\n').encode('utf-8')
        ser.write(cmd)
        ser.flush()
        print(f"→ Gesendet: {command}")
        
        # Warte auf Antwort
        time.sleep(0.1)
        response = b''
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                response += ser.read(ser.in_waiting)
                if b'\r\n' in response or b'\n' in response:
                    break
            time.sleep(0.01)
        
        response_str = response.decode('utf-8', errors='ignore').strip()
        print(f"← Empfangen: {response_str}")
        
        if expected_response and expected_response not in response_str:
            print(f"⚠ Warnung: Erwartete '{expected_response}', bekam '{response_str}'")
        
        return response_str
        
    except Exception as e:
        print(f"✗ Fehler beim Senden von '{command}': {e}")
        return None


def configure_lora_module():
    """
    Konfiguriert das LoRa-Modul mit den definierten Parametern.
    
    HINWEIS: Die genauen AT-Befehle hängen vom HAT-Hersteller ab.
    Dies ist ein Beispiel für Waveshare SX1268 HAT.
    """
    print("\n" + "="*60)
    print("SX1268 LoRa HAT Konfiguration")
    print("="*60 + "\n")
    
    print("WICHTIG: Stelle sicher, dass:")
    print("  1. Die Jumper korrekt gesetzt sind (siehe LORA_SETUP.md)")
    print("  2. Das Modul im Konfigurationsmodus ist (falls erforderlich)")
    print("  3. Beide Raspberry Pis die GLEICHEN Parameter verwenden!\n")
    
    try:
        # Serielle Schnittstelle öffnen
        ser = serial.Serial(
            port=LORA_PORT,
            baudrate=LORA_BAUDRATE,
            timeout=2,
            write_timeout=2
        )
        time.sleep(1)  # Warte auf Initialisierung
        
        print(f"✓ Serielle Schnittstelle {LORA_PORT} geöffnet\n")
        
        # Test: AT-Befehl senden (falls unterstützt)
        print("Teste Verbindung zum Modul...")
        response = send_at_command(ser, "AT", "OK")
        
        if response and "OK" in response:
            print("✓ Modul antwortet\n")
        else:
            print("⚠ Modul antwortet nicht auf AT - möglicherweise nicht AT-kompatibel")
            print("  Viele SX1268 HATs verwenden direkte Register-Konfiguration\n")
        
        # Konfiguration anzeigen
        print("Aktuelle Konfiguration:")
        print(f"  Frequenz: {FREQUENCY} MHz")
        print(f"  Spreading Factor: {SPREADING_FACTOR}")
        print(f"  Bandbreite: {BANDWIDTH} kHz")
        print(f"  Coding Rate: {CODING_RATE}")
        print(f"  TX Power: {TX_POWER} dBm")
        print(f"  Sync Word: 0x{SYNC_WORD:02X}")
        print(f"  CRC: {'Aktiviert' if CRC_ENABLED else 'Deaktiviert'}\n")
        
        # Beispiel-Konfiguration (Waveshare SX1268)
        # HINWEIS: Passen Sie diese Befehle an Ihr spezifisches HAT an!
        
        print("Konfiguriere Modul...")
        print("(Hinweis: Die genauen Befehle hängen vom HAT-Hersteller ab)\n")
        
        # Beispiel-Befehle für Waveshare SX1268:
        # Diese müssen möglicherweise angepasst werden!
        
        # Frequenz setzen
        freq_cmd = f"AT+FREQ={FREQUENCY}"
        send_at_command(ser, freq_cmd)
        time.sleep(0.2)
        
        # Spreading Factor
        sf_cmd = f"AT+SF={SPREADING_FACTOR}"
        send_at_command(ser, sf_cmd)
        time.sleep(0.2)
        
        # Bandbreite
        bw_cmd = f"AT+BW={BANDWIDTH}"
        send_at_command(ser, bw_cmd)
        time.sleep(0.2)
        
        # Coding Rate
        cr_cmd = f"AT+CR={CODING_RATE}"
        send_at_command(ser, cr_cmd)
        time.sleep(0.2)
        
        # TX Power
        tx_cmd = f"AT+POWER={TX_POWER}"
        send_at_command(ser, tx_cmd)
        time.sleep(0.2)
        
        # Sync Word
        sync_cmd = f"AT+SYNC={SYNC_WORD}"
        send_at_command(ser, sync_cmd)
        time.sleep(0.2)
        
        # CRC
        crc_cmd = f"AT+CRC={'ON' if CRC_ENABLED else 'OFF'}"
        send_at_command(ser, crc_cmd)
        time.sleep(0.2)
        
        # Parameter speichern (falls unterstützt)
        send_at_command(ser, "AT+SAVE")
        time.sleep(0.5)
        
        print("\n" + "="*60)
        print("Konfiguration abgeschlossen!")
        print("="*60)
        print("\nWICHTIG:")
        print("  - Führe dieses Skript auf BEIDEN Raspberry Pis aus")
        print("  - Stelle sicher, dass alle Parameter identisch sind")
        print("  - Setze die Jumper auf Übertragungsmodus (M0=GND, M1=GND)")
        print("\n")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"✗ Fehler: Kann serielle Schnittstelle nicht öffnen: {e}")
        print(f"  Prüfe, ob {LORA_PORT} existiert und berechtigt ist.")
        return False
    except Exception as e:
        print(f"✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_communication():
    """
    Testet die Kommunikation zwischen zwei Modulen.
    Führe dies auf beiden Raspberry Pis aus (einer sendet, einer empfängt).
    """
    print("\n" + "="*60)
    print("LoRa Kommunikationstest")
    print("="*60 + "\n")
    
    try:
        ser = serial.Serial(
            port=LORA_PORT,
            baudrate=LORA_BAUDRATE,
            timeout=5
        )
        time.sleep(1)
        
        print("Wähle Modus:")
        print("  1. Sender (sendet Testpakete)")
        print("  2. Empfänger (empfängt Testpakete)")
        
        mode = input("Modus (1/2): ").strip()
        
        if mode == "1":
            print("\nSende Testpakete...")
            for i in range(5):
                message = f"TEST_{i+1}"
                ser.write(message.encode('utf-8'))
                ser.flush()
                print(f"✓ Gesendet: {message}")
                time.sleep(2)
            print("\n✓ Test abgeschlossen")
            
        elif mode == "2":
            print("\nWarte auf Testpakete (10 Sekunden)...")
            start_time = time.time()
            while (time.time() - start_time) < 10:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"✓ Empfangen: {data.decode('utf-8', errors='ignore')}")
                time.sleep(0.1)
            print("\n✓ Test abgeschlossen")
        
        ser.close()
        
    except Exception as e:
        print(f"✗ Fehler: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_communication()
    else:
        configure_lora_module()

