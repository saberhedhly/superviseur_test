from flask import Blueprint, request, flash, redirect, url_for, render_template
from database import get_db_connection
from routes.auth import login_required
import sqlite3
machines_bp = Blueprint('machines', __name__)

@machines_bp.route('/add_machine', methods=['POST'])
@login_required
def add_machine():
    data = request.form
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO machines (machine_name, localisation, mac_address)
        VALUES (?, ?, ?)
    """, (data.get('machine_name'), data.get('localisation'), data.get('mac_address')))
    conn.commit()
    conn.close()
    flash("✅ Machine ajoutée", "success")
    return redirect(url_for('dashboard.dashboard'))

@machines_bp.route('/edit_machine/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_machine(id):
    with get_db_connection() as conn:
        cur = conn.cursor()

        if request.method == 'POST':
            data = request.form
            cur.execute("""
                UPDATE machines SET machine_name=?, localisation=?, mac_address=?
                WHERE id=?
            """, (data.get('machine_name'), data.get('localisation'), data.get('mac_address'), id))
            conn.commit()
            flash("✅ Machine modifiée", "success")
            return redirect(url_for('dashboard.dashboard'))

        cur.execute("SELECT * FROM machines WHERE id=?", (id,))
        machine = cur.fetchone()

    return render_template('edit_machine.html', machine=machine)
@machines_bp.route('/delete_machine/<int:id>', methods=['POST'])
@login_required
def delete_machine(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM machines WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("✅ Machine supprimée", "success")
    return redirect(url_for('dashboard.dashboard'))