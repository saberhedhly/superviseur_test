import smtplib
from email.mime.text import MIMEText
from config import Config
import random
import string
import sqlite3
def send_email(subject, body, to_email):
    if not Config.EMAIL_PASSWORD:
        print("⚠️ Mot de passe email non configuré")
        return False
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = Config.EMAIL_SENDER
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.set_debuglevel(1)
        server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
        server.sendmail(Config.EMAIL_SENDER, [to_email], msg.as_string())
        server.quit()
        print("✅ Email envoyé avec succès")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Échec d'authentification SMTP : vérifie ton mot de passe d'application")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {e}")
        return False

def generate_activation_code(length=6):
    return ''.join(random.choices(string.digits, k=length))