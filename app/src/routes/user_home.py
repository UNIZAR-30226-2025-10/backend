from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
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

        # Construir el diccionario con las canciones escuchadas
        historial = {
            h.cancion.id: {
                "nombreArtista" : h.cancion.artista.nombreArtistico,
                "nombreCancion": h.cancion.nombre,
                "fotoPortada": h.cancion.album.fotoPortada
            }
            for h in oyente_entry.historialCancion
        }
    
    return jsonify({"historial_canciones": dict(list(historial.items())[:30])}), 200

"""Devuelve una lista con el historial de albumes y playlists del usuario"""
@user_home_bp.route('/get-historial-colecciones', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_colecciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        historial = {
            h.coleccion.id: {
                "nombreColeccion": h.coleccion.nombre,
                "fotoPortada": h.coleccion.fotoPortada,
                "autor": (
                    h.coleccion.oyente.nombreUsuario if isinstance(h.coleccion, Playlist)
                    else h.coleccion.artista.nombreArtistico if isinstance(h.coleccion, Album)
                    else "Desconocido"
                )
            }
            for h in oyente_entry.historialColeccion
        }
    
    return jsonify({"historial_colecciones": dict(list(historial.items())[:30])}), 200

"""Devuelve una lista con el historial de artistas del usuario"""
@user_home_bp.route('/get-historial-artistas', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_historial_artistas():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Construir el diccionario con los artistas escuchados
        artistas = {
            h.cancion.artista.correo: {
                "nombreArtista" : h.cancion.artista.nombreArtistico,
                "fotoPerfil": h.cancion.artista.fotoPerfil
            }
            for h in oyente_entry.historialCancion
        }
    
    return jsonify({"historial_artistas": dict(list(artistas.items())[:30])}), 200

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

        seguidos = {
            s.correo: {
                "fotoPerfil": s.fotoPerfil,
                "nombre": s.nombreUsuario
            }
            for s in oyente_entry.seguidos
        }

    return jsonify({"seguidos": dict(list(seguidos.items())[:30])}), 200

"""Devuelve una lista con las playlists del usuario"""
@user_home_bp.route('/get-mis-playlists', methods=['GET'])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_mis_playlists():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion con playlists creadas
        mis_playlists = {
            s.id: {
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in oyente_entry.playlists
        }

        # Accede directamente a la relacion con playlists en las que se participa
        participando_playlists = {
            s.id: {
                "fotoPortada": s.fotoPortada,
                "nombre": s.nombre
            }
            for s in oyente_entry.participante
        }

        # Unimos ambos diccionarios
        playlists = {
            **mis_playlists,
            **participando_playlists
        }

        # Ordenamos el diccionario por el campo "nombre"
        playlists_ordenadas = sorted(playlists.items(), key=lambda x: x[1]["nombre"])

        # Convertimos la lista ordenada en un diccionario solo con el id como clave
        playlists_dict = {k: v for k, v in playlists_ordenadas}
        
    return jsonify({"playlists": dict(list(playlists_dict.items())[:30])}), 200


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
