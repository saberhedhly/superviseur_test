from flask import Blueprint, render_template, session, flash, redirect, url_for
from database import get_db_connection
from datetime import datetime
from .auth import login_required
from .alerts import check_alerts
import sqlite3


dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    check_alerts()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.*, m.machine_name, m.localisation FROM instruments i
        LEFT JOIN machines m ON i.machine_id = m.id
    """)
    instruments = cur.fetchall()
    cur.execute("SELECT * FROM machines")
    machines = cur.fetchall()
    cur.execute("SELECT * FROM alerts ORDER BY alert_date DESC LIMIT 100")
    alerts = cur.fetchall()
    conn.close()
    return render_template('dashboard.html', instruments=instruments, machines=machines, alerts=alerts)

@dashboard_bp.route('/dashboard_user')
@login_required
def dashboard_user():
    check_alerts()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.*, m.machine_name, m.localisation FROM instruments i
        LEFT JOIN machines m ON i.machine_id = m.id
    """)
    instruments = cur.fetchall()
    cur.execute("SELECT * FROM machines")
    machines = cur.fetchall()
    cur.execute("SELECT * FROM alerts ORDER BY alert_date DESC LIMIT 1000")
    alerts = cur.fetchall()
    conn.close()
    return render_template('dashboard_user.html', instruments=instruments, machines=machines, alerts=alerts)