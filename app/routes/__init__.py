from .auth import auth_bp 
from .home import home_bp

"""Registra las rutas de la API en la app"""
def register_routes(app):
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)