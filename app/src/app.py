from flask import Flask
from flask_jwt_extended import JWTManager
from utils.mail import init_mail
from routes import register_routes
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

# Instanciar app Flask
app = Flask(__name__)
CORS(app)

# Clave secreta para firmar los tokens JWT
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Inicializar Flask-Mail en la app
init_mail(app) 

# Registras rutas API
register_routes(app)
