from flask import Blueprint, render_template
from database import get_db_connection
from .auth import login_required
from datetime import datetime
from config import Config
from email_utils import send_email
import sqlite3
alerts_bp = Blueprint('alerts', __name__)

def count_alerts_today(alert_type=None):
    conn = get_db_connection()
    cur = conn.cursor()
    today = datetime.now().date()
    count = 0
    if alert_type and alert_type in Config.MAX_ALERTS_PER_DAY:
        cur.execute("""
            SELECT COUNT(*) FROM alerts
            WHERE date(alert_date) = ? AND alert_type = ?
        """, (today.isoformat(), alert_type))
        count = cur.fetchone()[0]
    conn.close()
    return count

def add_alert(instrument_name, alert_type, message):
    from datetime import datetime
    if alert_type in Config.MAX_ALERTS_PER_DAY and count_alerts_today(alert_type) >= Config.MAX_ALERTS_PER_DAY[alert_type]:
        print("⚠️ Limite d'alertes atteinte pour aujourd'hui.")
        return

    date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO alerts (instrument_name, alert_type, date, message, alert_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (instrument_name, alert_type, date_now, message, date_now))
    conn.commit()
    conn.close()
    print("✅ Alerte enregistrée.")

    subject = f"Alerte : {alert_type} - {instrument_name}"
    body = f"{message}\n\nDate : {date_now}"
    send_email(subject, body, Config.EMAIL_RECEIVER)

def check_alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.*, m.machine_name, m.localisation 
        FROM instruments i
        LEFT JOIN machines m ON i.machine_id = m.id
    """)
    instruments = cur.fetchall()
    today = datetime.now().date()
    for inst in instruments:
        date_str = inst['date_prochain_etalonnage']
        date_prochain = None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                date_prochain = datetime.strptime(date_str, fmt).date()
                break
            except Exception:
                continue
        if not date_prochain:
            continue

        days_diff = (date_prochain - today).days

        if 0 <= days_diff <= 5:
            msg = f"⚠️ Prochain étalonnage '{inst['instrument_name']}' dans {days_diff} jour(s) (le {date_prochain})."
            add_alert(inst['instrument_name'], "Prochain Étalonnage", msg)

        if (not inst['machine_name'] or 
            not inst['localisation'] or 
            inst['localisation'].strip().lower() in ['inconnue', '']):
            msg = f"⚠️ Localisation incorrecte pour '{inst['instrument_name']}'"
            add_alert(inst['instrument_name'], "Position Incorrecte", msg)
    conn.close()

@alerts_bp.route('/alerts')
@login_required
def alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts ORDER BY alert_date DESC LIMIT 100")
    alerts = cur.fetchall()
    conn.close()
    return render_template('alerts.html', alerts=alerts)