from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime
from .alerts import add_alert
import sqlite3
api_bp = Blueprint('api', __name__)

@api_bp.route('/add_data', methods=['POST'])
def add_data():
    data = request.get_json()
    if not data:
        return jsonify({"status": "Erreur", "message": "Données JSON manquantes"}), 400

    instrument_name = data.get('instrument_name')
    rssi = data.get('rssi')
    esp_mac = data.get('mac_address')

    if not all([instrument_name, rssi, esp_mac]):
        return jsonify({"status": "Erreur", "message": "Champs manquants"}), 400

    print(f"🔧 Reçu => Tag: {instrument_name}, RSSI: {rssi}, MAC ESP32: {esp_mac}")

    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            machine = conn.execute("SELECT * FROM machines WHERE mac_address = ?", (esp_mac,)).fetchone()
            if not machine:
                try:
                    add_alert(instrument_name, "Machine Inconnue", f"Machine avec MAC {esp_mac} inconnue.")
                except Exception as e:
                    print(f"Erreur lors de l'ajout d'une alerte: {e}")
                return jsonify({"status": "Erreur", "message": "Machine inconnue"}), 200

            machine_id = machine["id"]
            machine_name = machine["machine_name"]
            localisation = machine["localisation"]

            instrument = conn.execute("SELECT * FROM instruments WHERE instrument_name = ?", (instrument_name,)).fetchone()
            if not instrument:
                try:
                    add_alert(instrument_name, "Instrument Introuvable", f"L'instrument '{instrument_name}' n'existe pas.")
                except Exception as e:
                    print(f"Erreur lors de l'ajout d'une alerte: {e}")
                return jsonify({"status": "Erreur", "message": "Instrument non trouvé"}), 200

            instrument_machine_id = instrument["machine_id"]

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            alert_triggered = False

            if instrument_machine_id != machine_id:
                true_machine = conn.execute("SELECT machine_name FROM machines WHERE id = ?", (instrument_machine_id,)).fetchone()
                true_machine_name = true_machine["machine_name"] if true_machine else "inconnue"
                msg = (f"L'instrument '{instrument_name}' est détecté par '{machine_name}', "
                       f"mais il est associé à '{true_machine_name}'.")
                try:
                    add_alert(instrument_name, "Position Incorrecte", msg)
                except Exception as e:
                    print(f"Erreur lors de l'ajout d'une alerte: {e}")
                alert_triggered = True

            date_prochain_etalonnage = instrument['date_prochain_etalonnage']
            if date_prochain_etalonnage:
                try:
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                        try:
                            date_etal = datetime.strptime(date_prochain_etalonnage, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError("Format de date invalide")

                    if (date_etal - datetime.now()).days <= 5:
                        msg = f"⚠ Prochain étalonnage de '{instrument_name}' prévu pour le {date_prochain_etalonnage}"
                        try:
                            add_alert(instrument_name, "Prochain Étalonnage", msg)
                        except Exception as e:
                            print(f"Erreur lors de l'ajout d'une alerte: {e}")
                        alert_triggered = True
                except Exception as e:
                    print(f"❌ Erreur parsing date: {e}")

            conn.execute(
                'UPDATE instruments SET rssi = ?, last_seen = ? WHERE id = ?',
                (rssi, now_str, instrument['id'])
            )

            conn.execute(
                '''INSERT INTO detections (device_name, rssi, mac_address, timestamp, machine_id, location)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (instrument_name, rssi, esp_mac, now_str, machine_id, localisation)
            )

            conn.commit()

    except sqlite3.OperationalError as e:
        print(f"❌ SQLite OperationalError: {e}")
        return jsonify({"status": "Erreur", "message": "Base de données occupée ou inaccessible."}), 500

    if alert_triggered:
        return jsonify({"status": "Alerte déclenchée", "instrument": instrument_name}), 200
    else:
        return jsonify({"status": "OK", "instrument": instrument_name}), 200
