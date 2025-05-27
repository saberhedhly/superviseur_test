import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis un fichier .env s'il existe
load_dotenv()

class Config:
    # Clé secrète pour les sessions Flask
    SECRET_KEY = 'cle_secrete'

    # Chemin absolu vers la base de données SQLite
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, 'database.db')

    # Informations pour l'envoi d'e-mails (à adapter si besoin)
    EMAIL_SENDER = 'hedhlysaber@gmail.com'
    EMAIL_PASSWORD = 'kvqx osid ntqo dwxg'  # ⚠️ Utiliser une variable d'environnement est plus sûr
    EMAIL_RECEIVER = 'hedhlysaber@gmail.com'

    # Limites journalières d'alertes par type
    MAX_ALERTS_PER_DAY = {
        "Instrument Introuvable": 20,
        "Prochain Étalonnage": 20,
        "Position Incorrecte": 1000,
    }
