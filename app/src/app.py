from flask import Flask
from flask_jwt_extended import JWTManager
from utils.mail import init_mail
from routes import register_routes

# Instanciar app Flask
app = Flask(__name__)

# Clave secreta para firmar los tokens JWT
app.config["JWT_SECRET_KEY"] = "supersecreto"
jwt = JWTManager(app)

# Inicializar Flask-Mail en la app
init_mail(app) 

# Registras rutas API
register_routes(app)
