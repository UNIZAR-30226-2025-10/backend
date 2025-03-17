from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import Playlist, Oyente
from db.db import get_db
from utils.decorators import roles_required, tokenVersion_required
from utils.fav import fav

playlist_bp = Blueprint('playlist', __name__)

"""Devuelve los datos de una playlist, en concreto la lista de canciones de la playlist ordenada según el criterio especificado"""
@playlist_bp.route("/get-datos-playlist", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def get_datos_playlist():
    id = request.args.get("id")
    orden = request.args.get("orden")

    if not id:
        return jsonify({"error": "Falta el ID de la playlist."}), 400
    correo = get_jwt_identity()

    if not orden:
        orden = "fecha"

    with get_db() as db:
        playlist_entry = db.get(Playlist, id)

        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
 
        creador_entry = db.get(Oyente, playlist_entry.Oyente_correo)
        participantes = [p.nombreUsuario for p in playlist_entry.participantes]

        canciones_entry = [(ep.cancion, ep.fecha) for ep in playlist_entry.esParteDePlaylist]

        if orden == "fecha":
            canciones_entry = sorted(canciones_entry, key=lambda x: x[1])
        elif orden == "nombre":
            canciones_entry = sorted(canciones_entry, key=lambda x: x[0].nombre.lower())
        elif orden == "reproducciones":
            canciones_entry = sorted(canciones_entry, key=lambda x: x[0].reproducciones, reverse=True)

        canciones_entry = [c[0] for c in canciones_entry]

        duracion_total = sum(c.duracion for c in canciones_entry)

        respuesta = {
            "playlist": {
                "duracion": duracion_total,
                "creador": creador_entry.nombreUsuario if creador_entry else None,
                "colaboradores": participantes,
            },
            "canciones": [
                {
                    "nombre": c.nombre,
                    "nombreArtisticoArtista": c.artista.nombreArtistico,
                    "reproducciones": c.reproducciones,
                    "duracion": c.duracion,
                    "fav": fav(c.id, correo, db),
                    "nombreUsuarioArtista": c.artista.nombreUsuario,
                    "fotoPortada": c.album.fotoPortada,
                }
                for c in canciones_entry
            ],
        }

    return jsonify(respuesta)

"""Cambia la privacidad de una playlist del usuario logueado"""
@playlist_bp.route("/change-privacidad", methods=["PATCH"])
@jwt_required()
def change_privacidad():
    data = request.get_json()
    if not data or "id" not in data or "privacidad" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    id = data.get("id")
    privacidad = data.get("privacidad")

    correo = get_jwt_identity()

    with get_db() as db:
        playlist = db.get(Playlist, id)
        if not playlist:
            return jsonify({"error": "La playlist no existe."}), 404
        if playlist.Oyente_correo != correo:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        # Cambiar privacidad y guardar cambios
        playlist.privacidad = privacidad
        db.commit()

    return jsonify({"message": "Privacidad actualizada correctamente."}), 200
