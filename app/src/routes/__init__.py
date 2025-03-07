from .swagger import swagger_bp, SWAGGER_URL
from .admin import admin_bp
from .auth import auth_bp 
from .home import home_bp
from .search import search_bp
from .files import files_bp

"""Registra las rutas de la API en la app"""
def register_routes(app):
    app.register_blueprint(swagger_bp, url_prefix=SWAGGER_URL)
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(files_bp)