import sqlite3
from config import Config

def get_db_connection():
    # Timeout en secondes pour éviter "database is locked"
    conn = sqlite3.connect(Config.DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """
    Fonction utilitaire pour exécuter une requête SELECT
    et retourner un résultat ou une liste.
    """
    with get_db_connection() as conn:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """
    Fonction utilitaire pour exécuter une requête INSERT/UPDATE/DELETE
    avec commit automatique.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()

def get_user_by_email(email):
    return query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)
