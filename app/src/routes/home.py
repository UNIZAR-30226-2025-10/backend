from flask import Blueprint

home_bp = Blueprint('home', __name__)

"""Home de la API"""
@home_bp.route('/')
def home():
    return "Bienvenido a la API de Noizz"
