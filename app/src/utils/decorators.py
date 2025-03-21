from functools import wraps
from flask import jsonify, request, g
from flask_jwt_extended import get_jwt, get_jwt_identity
from flask_socketio import rooms
from db.db import get_db
from db.models import Usuario

"""Comprueba que un usuario es de un determinado tipo para poder utilizar la API"""
def roles_required(*tipos_permitidos):
    def wrapper(fn):
        @wraps(fn)
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            # Comprobar que el token es de los tipos permitidos
            if claims.get("tipo") not in tipos_permitidos:
                return jsonify({"error":"Acceso denegado"}), 403
            return fn(*args, **kwargs)
        return decorated_function
    return wrapper

"""Comprueba la validez (que no expiracion) del token"""
def tokenVersion_required():
    def wrapper(fn):
        @wraps(fn)
        def decorated_function(*args, **kwargs):
            correo = get_jwt_identity()
            claims = get_jwt()
            tokenVersion = claims.get("tokenVersion")

            with get_db() as db:
                usuario = db.get(Usuario, correo)
            
            # Comprobar correo
            if not usuario:
                return jsonify({"error": "Correo no existe."}), 401

            # Comprobar tokenVersion valida
            if usuario.tokenVersion != tokenVersion:
                return jsonify({"error": "Token inválido."}), 401

            return fn(*args, **kwargs)
        return decorated_function
    return wrapper

"""Comprueba la validez del sid"""
def sid_required():
    def wrapper(fn):
        @wraps(fn)
        def decorated_function(*args, **kwargs):
            sid = request.headers.get("sid")
            if not sid:
                return {"error": "Falta SID."}, 400 

            correo = get_jwt_identity()  
            # Verificar si el SID está en la sala del usuario
            if correo not in rooms(sid, namespace="/"):
                return {"error": "SID no valido."}, 403 

            return fn(*args, **kwargs)
        return decorated_function
    return wrapper