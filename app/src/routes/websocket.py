from flask import request
from flask_socketio import join_room, leave_room
from flask_jwt_extended import decode_token
from app import socketio

"""Valida el token JWT y une el socket de un usuario a su room"""
@socketio.on("connect")
def handle_connect():
    token = request.args.get("token")
    if not token:
        return False

    try:
        decoded_token = decode_token(token)
        correo = decoded_token["sub"]
        join_room(correo)  # Los sockets de un mismo usuario se guardan en la misma room
        print(f"Usuario {correo} conectado en {request.sid}")
    except Exception as e:
        print("Token inválido o expirado")
        return False  

"""Elimina el socket de un usuario de su room al desconectarse"""
@socketio.on("disconnect")
def handle_disconnect():
    token = request.args.get("token")
    if not token:
        return False

    try:
        decoded_token = decode_token(token)
        correo = decoded_token["sub"]
        leave_room(correo)
        print(f"Usuario {correo} desconectado de {request.sid}")
    except Exception as e:
        print("Token inválido o expirado")
        return False  
