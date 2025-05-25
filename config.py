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
    EMAIL_SENDER = 'marwabenchaabene508@gmail.com'
    EMAIL_PASSWORD = 'npmp idbi rgnz ornr'  # ⚠️ Utiliser une variable d'environnement est plus sûr
    EMAIL_RECEIVER = 'marwabenchaabene508@gmail.com'

    # Limites journalières d'alertes par type
    MAX_ALERTS_PER_DAY = {
        "Instrument Introuvable": 100,
        "Prochain Étalonnage": 100,
        "Position Incorrecte": 100,
    }
