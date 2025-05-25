from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from email_utils import send_email
from .auth import login_required
import random
from config import Config
from datetime import datetime
import sqlite3
import re

admin_bp = Blueprint('admin', __name__)

def is_password_strong(password):
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une lettre majuscule."
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une lettre minuscule."
    if not re.search(r'\d', password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r'[@$!%*?&]', password):
        return False, "Le mot de passe doit contenir au moins un symbole (@$!%*?&)."
    return True,""

def get_user_by_email(email):
    # Exemple avec SQLite et flask g.db ou autre méthode d'accès à la DB
    cursor = get_db_connection().execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    cursor.close()
    return user


@admin_bp.route('/change_role_page')
@login_required
def change_role_page():
    if session.get('role') != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard.dashboard'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()

    return render_template('change_role.html', users=users)

@admin_bp.route('/change_role', methods=['POST'])
@login_required
def change_role():
    if session.get('role') != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard.dashboard'))

    try:
        user_id = request.form.get('user_id')
        master_password_input = request.form.get('master_password')
        new_role = request.form.get('new_role')  # Changé ici

        # Validation des données
        if not all([user_id, master_password_input, new_role]):
            flash("Tous les champs sont requis", "danger")
            return redirect(url_for('admin.change_role_page'))

        if new_role not in ['admin', 'user']:
            flash("Rôle invalide", "danger")
            return redirect(url_for('admin.change_role_page'))

        conn = get_db_connection()
        try:
            # Vérification du mot de passe master
            cur = conn.cursor()
            cur.execute("SELECT master_password FROM admin_master WHERE id = 1")
            row = cur.fetchone()

            if not row:
                flash("Erreur interne: mot de passe admin non trouvé", "danger")
                return redirect(url_for('admin.change_role_page'))

            if not check_password_hash(row['master_password'], master_password_input):
                flash("Mot de passe admin incorrect", "danger")
                return redirect(url_for('admin.change_role_page'))

            # Vérification que l'utilisateur existe
            cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cur.fetchone():
                flash("Utilisateur non trouvé", "danger")
                return redirect(url_for('admin.change_role_page'))

            # Mise à jour du rôle
            cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            conn.commit()

            flash(f"Rôle modifié avec succès pour l'utilisateur ID {user_id}", "success")
            return redirect(url_for('admin.change_role_page'))

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Erreur base de données: {str(e)}")
            flash("Erreur lors de la modification du rôle", "danger")
            return redirect(url_for('admin.change_role_page'))

        finally:
            conn.close()

    except Exception as e:
        current_app.logger.error(f"Erreur inattendue: {str(e)}")
        flash("Une erreur inattendue est survenue", "danger")
        return redirect(url_for('admin.change_role_page'))

@admin_bp.route('/master_password_forgot', methods=['GET', 'POST'])
def master_password_forgot():
    if request.method == 'POST':
        user_email = request.form.get('email')
        user = get_user_by_email(user_email)
        if not user:
            flash("Email non trouvé.", "danger")
            return redirect(url_for('admin.master_password_forgot'))

        otp_code = str(random.randint(100000, 999999))
        session['master_password_reset_code'] = otp_code
        session['master_password_reset_email'] = user_email

        if send_email("Code de réinitialisation", f"Votre code : {otp_code}", Config.EMAIL_RECEIVER):
            flash("Code envoyé à votre email.", "success")
            return redirect(url_for('admin.master_password_reset_verify'))
        else:
            flash("Erreur lors de l'envoi de l'email.", "danger")
            return redirect(url_for('admin.master_password_forgot'))

    return render_template('master_password_forgot.html')

@admin_bp.route('/master_password_reset_verify', methods=['GET', 'POST'])
def master_password_reset_verify():
    if request.method == 'POST':
        code = request.form.get('code')
        if code == session.get('master_password_reset_code'):
            session['master_password_verified'] = True
            return redirect(url_for('admin.master_password_reset_form'))
        else:
            flash("Code incorrect.", "danger")
            return redirect(url_for('admin.master_password_reset_verify'))
    return render_template('master_password_reset_verify.html')

@admin_bp.route('/master_password_reset_form', methods=['GET', 'POST'])
def master_password_reset_form():
    # Vérifier que l'utilisateur a bien vérifié le code OTP avant d'accéder à ce formulaire
    if not session.get('master_password_verified'):
        flash("Veuillez vérifier le code d'abord.", "warning")
        return redirect(url_for('admin.master_password_reset_verify'))

    if request.method == 'POST':
        # Récupérer les mots de passe saisis dans le formulaire
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Vérifier que les deux mots de passe correspondent
        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('admin.master_password_reset_form'))

        # Vérifier la robustesse du mot de passe avec une fonction personnalisée
        valid, message = is_password_strong(new_password)
        if not valid:
            flash(f"❌ {message}", "danger")
            return redirect(url_for('admin.master_password_reset_form'))

        # Hacher le nouveau mot de passe avant de le stocker en base de données
        hashed_password = generate_password_hash(new_password)
        email = session.get('master_password_reset_email')

        # Mise à jour du mot de passe dans la table admin_master pour l'email donné
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE admin_master SET master_password = ?, updated_at = ? WHERE email = ?", 
            (hashed_password, datetime.utcnow(), email)
        )
        conn.commit()
        conn.close()

        # Nettoyage des variables de session liées à la réinitialisation
        session.pop('master_password_reset_code', None)
        session.pop('master_password_reset_email', None)
        session.pop('master_password_verified', None)

        # Message de succès et redirection vers la page de connexion admin
        flash("Mot de passe master modifié avec succès.", "success")
        return redirect(url_for('auth.login'))

    # Affichage du formulaire de réinitialisation du mot de passe
    return render_template('master_password_reset_form.html')
@admin_bp.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    # Vérifier que l'utilisateur connecté est admin
    if session.get('role') != 'admin':
        flash("Accès refusé", "danger")
        return redirect(url_for('dashboard.dashboard'))

    user_id = request.form.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor()

    # Exemple de protection : empêcher la suppression de l'admin principal (id=1)
    if user_id == '1':
        flash("Vous ne pouvez pas supprimer l'administrateur principal.", "danger")
        conn.close()
        return redirect(url_for('admin.change_role_page'))

    try:
        # Suppression de l'utilisateur en base de données
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash("Utilisateur supprimé avec succès.", "success")
    except Exception as e:
        # Gestion des erreurs éventuelles lors de la suppression
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    finally:
        conn.close()

    # Redirection vers la page de gestion des rôles après suppression
    return redirect(url_for('admin.change_role_page'))
