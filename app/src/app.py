#from gevent import monkey
#monkey.patch_all()

from flask import Flask
from flask_jwt_extended import JWTManager
from utils.mail import init_mail
from routes import register_routes
from flask_cors import CORS
from routes.websocket import socketio
import os

# Instanciar app Flask
app = Flask(__name__)
CORS(app)

# Instanciar WebSockets
socketio.init_app(app)

# Clave secreta para firmar los tokens JWT
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Inicializar Flask-Mail en la app
init_mail(app) 

# Registras rutas API
register_routes(app)

#if __name__ == '__main__':
#    socketio.run(app, debug=True, host='0.0.0.0', port=5000)