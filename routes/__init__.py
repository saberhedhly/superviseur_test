# routes/__init__.py

from .auth import auth_bp
from .dashboard import dashboard_bp
from .instruments import instruments_bp
from .machines import machines_bp
from .alerts import alerts_bp
from .api import api_bp
from .admin import admin_bp

blueprints = [
    auth_bp,
    dashboard_bp,
    instruments_bp,
    machines_bp,
    alerts_bp,
    api_bp,
    admin_bp
]
