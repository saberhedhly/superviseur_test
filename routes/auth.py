from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, get_user_by_email
from email_utils import send_email, generate_activation_code
from functools import wraps
from config import Config
from datetime import datetime
import re
import sqlite3
auth_bp = Blueprint('auth', __name__)

def is_password_strong(password):
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une lettre majuscule."
    if not re.search(r"[a-z]", password):
        return False, "Le mot de passe doit contenir au moins une lettre minuscule."
    if not re.search(r"\d", password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Le mot de passe doit contenir au moins un caractère spécial."
    return True, ""


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            flash("⚠️ Veuillez vous connecter d'abord.", "warning")
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return redirect(url_for('auth.register'))

        # Vérification de la force du mot de passe
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            flash("❌ Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial.", "danger")
            return redirect(url_for('auth.register'))

        activation_code = generate_activation_code()
        print("Activation code generated:", activation_code)
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (username, email, password, activation_code, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, hashed_password, activation_code, 0))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("❌ Nom d'utilisateur déjà utilisé", "danger")
            return redirect(url_for('auth.register'))
        finally:
            conn.close()

        subject = "Code d'activation pour nouvel utilisateur"
        body = f"Bonjour {username},\n\nVoici votre code d'activation : {activation_code}\n\nMerci."

        send_email(subject, body, Config.EMAIL_RECEIVER)

        flash("✅ Inscription réussie. Le code d'activation a été envoyé par email.", "success")
        return redirect(url_for('auth.activate'))

    return render_template('register.html')

@auth_bp.route('/activate', methods=['GET', 'POST'])
def activate():
    if request.method == 'POST':
        username = request.form.get('username')
        code = request.form.get('code')

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT activation_code, is_active FROM users WHERE username = ?", (username,))
            user = cur.fetchone()

            if not user:
                flash("❌ Utilisateur introuvable.", "danger")
            elif user['is_active'] == 1:
                flash("ℹ Compte déjà activé.", "info")
                return redirect(url_for('auth.login'))
            elif user['activation_code'] == code:
                cur.execute("""
                    UPDATE users 
                    SET is_active = 1, activation_code = NULL, updated_at = ? 
                    WHERE username = ?
                """, (datetime.utcnow(), username))
                conn.commit()
                flash("✅ Compte activé avec succès. Vous pouvez maintenant vous connecter.", "success")
                return redirect(url_for('auth.login'))
            else:
                flash("❌ Code d'activation incorrect.", "danger")
        finally:
            conn.close()

    return render_template('activate.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username')  # Peut être soit le nom d'utilisateur ou l'email
        password = request.form.get('password')

        if not identifier or not password:
            flash("⚠ Veuillez remplir tous les champs", "warning")
            return redirect(url_for('auth.login'))

        conn = get_db_connection()
        cur = conn.cursor()
        # Recherche dans les colonnes username ou email pour correspondance
        cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            if user['is_active'] == 1:
                # Stockage des informations de session
                session['logged_in'] = True
                session['username'] = user['username']  # On garde le vrai nom d'utilisateur
                session['role'] = user['role']

                flash("✅ Connexion réussie", "success")

                # Redirection selon rôle
                if user['role'] == 'admin':
                    return redirect(url_for('dashboard.dashboard'))
                else:
                    return redirect(url_for('dashboard.dashboard_user'))
            else:
                flash("⚠ Compte non activé. Veuillez vérifier votre email.", "warning")
        else:
            flash("❌ Nom d'utilisateur, email ou mot de passe incorrect", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if user:
            new_code = generate_activation_code(8)
            cur.execute("UPDATE users SET new_code = ? WHERE email = ?", (new_code, email))
            conn.commit()
            conn.close()

            subject = "Code de réinitialisation de mot de passe"
            body = f"Bonjour {user['username']},\n\nVoici votre code pour réinitialiser votre mot de passe : {new_code}\n\nMerci."
            send_email(subject, body, email)
            flash("✅ Code de réinitialisation envoyé à votre email.", "success")
            return redirect(url_for('auth.reset_password'))
        else:
            conn.close()
            flash("❌ Email introuvable.", "danger")
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('code')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("❌ Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('auth.reset_password'))

        valid, message = is_password_strong(new_password)
        if not valid:
            flash(f"❌ {message}", "danger")
            return redirect(url_for('auth.reset_password'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT new_code FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

        if user and user['new_code'] == code:
            hashed_password = generate_password_hash(new_password)
            updated_at = datetime.utcnow()
            cur.execute("UPDATE users SET password = ?, new_code = NULL, updated_at = ? WHERE email = ?", 
                        (hashed_password, updated_at, email))
            conn.commit()
            conn.close()
            flash("✅ Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('auth.login'))
        else:
            conn.close()
            flash("❌ Code de réinitialisation incorrect ou expiré.", "danger")
            return redirect(url_for('auth.reset_password'))

    return render_template('reset_password.html')