from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
import heapq
from utils.recommendation import obtener_recomendaciones

user_home_bp = Blueprint('user_home', __name__)

"""Devuelve una lista con el historial de canciones del usuario"""
@user_home_bp.route('/get-historial-canciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_canciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion historial
        historial = [s.to_dict_home() for s in oyente_entry.historial] 
    
    return jsonify({"historial_canciones": historial[:30]}), 200

"""Devuelve una lista con los seguidos del usuario"""
@user_home_bp.route('/get-seguidos', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_seguidos():
    correo = get_jwt_identity()  

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion historial
        seguidos = [s.to_dict_home() for s in oyente_entry.seguidos]
    
    return jsonify({"seguidos": seguidos[:30]}), 200

"""Devuelve una lista con las playlists del usuario"""
@user_home_bp.route('/get-playlists', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_playlists():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion con playlists creadas
        mis_playlists = [s.to_dict_home() for s in oyente_entry.playlists]

        # Accede directamente a la relacion con playlists en las que se participa
        participando_playlists = [s.to_dict_home() for s in oyente_entry.participantes]

        # Ordena ambos vectores por orden alfabetico en uno solo
        playlists = list(heapq.merge(mis_playlists, participando_playlists, key=lambda x: x["nombre"]))
        
    return jsonify({"playlists": playlists[:30]}), 200


"""Devuelve una lista con las canciones recomendadas para el usuario"""
@user_home_bp.route('/get-recomendaciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_recomendaciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 400
        
        canciones_recomendadas = obtener_recomendaciones(oyente_entry, db)

    return jsonify({"canciones_recomendadas": canciones_recomendadas}), 200

