from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import Playlist, Oyente, Cancion, EsParteDePlaylist, Usuario, participante_table
from db.db import get_db
from sqlalchemy import select, exists, delete
from utils.decorators import roles_required, tokenVersion_required
from utils.fav import fav
from datetime import datetime
import pytz

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

    return jsonify(respuesta), 201

"""Cambia la privacidad de una playlist del usuario logueado"""
@playlist_bp.route("/change-privacidad", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
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

    return jsonify(""), 200

"""Añade una cancion a una playlist del usuario logueado"""
@playlist_bp.route("/add-to-playlist", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def add_to_playlist():
    data = request.get_json()
    if not data or "cancion" not in data or "playlist" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    cancion = data.get("cancion")
    playlist = data.get("playlist")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        participantes = [p.correo for p in playlist_entry.participantes]
        if playlist_entry.Oyente_correo != correo or correo not in participantes:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        cancion_entry = db.get(Cancion, cancion)
        if not cancion_entry:
            return jsonify({"error": "La cancion no existe."}), 404
        
        EsParteDePlaylist_entry = db.get(EsParteDePlaylist, (cancion, playlist))
        if EsParteDePlaylist_entry:
            return jsonify({"error": "La cancion ya es parte de la playlist."}), 409

        new_entry = EsParteDePlaylist(Cancion_id=cancion, Playlist_id=playlist, fecha=datetime.now(pytz.timezone('Europe/Madrid')))
        db.add(new_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 201

"""Elimina una cancion de una playlist del usuario logueado"""
@playlist_bp.route("/delete-from-playlist", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def delete_from_playlist():
    data = request.get_json()
    if not data or "cancion" not in data or "playlist" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    cancion = data.get("cancion")
    playlist = data.get("playlist")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404

        esParteDePlaylist_entry = db.get(EsParteDePlaylist, (cancion, playlist))
        if not esParteDePlaylist_entry:
            return jsonify({"error": "La cancion no pertenece a la playlist."}), 404
        
        participantes = [p.correo for p in playlist_entry.participantes]
        if playlist_entry.Oyente_correo != correo or correo not in participantes:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        db.delete(esParteDePlaylist_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204

"""Añade un usuario (ni participante ni creador) a una playlist como invitado"""
@playlist_bp.route("/invite-to-playlist", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def invite_to_playlist():
    data = request.get_json()
    if not data or "nombreUsuario" not in data or "playlist" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    nombreUsuario = data.get("nombreUsuario")
    playlist = data.get("playlist")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        if playlist_entry.Oyente_correo != correo:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        usuario_entry = db.execute(select(Usuario).where(Usuario.nombreUsuario == nombreUsuario)).scalar_one_or_none()
        if not usuario_entry:
            return jsonify({"error": "El usuario no existe."}), 404
        
        if usuario_entry in playlist_entry.participantes or usuario_entry in playlist_entry.invitados:
            return jsonify({"error": "El usuario ya ha sido invitado a participar en la playlist."}), 409
        
        playlist.invitados.append(usuario_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 201

    
"""Elimina al usuario logueado de participante de una playlist"""
@playlist_bp.route("/leave-playlist", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def leave_playlist():
    data = request.get_json()
    if not data or "playlist" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    playlist = data.get("playlist")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        exists_stmt = select(exists().where(
            participante_table.c.Oyente_correo == correo,
            participante_table.c.Playlist_id == playlist
        ))
        participa = db.execute(exists_stmt).scalar()

        if not participa:
            return jsonify({"error": "No participas en la playlist."}), 404
        
        delete_stmt = delete(participante_table).where(
            participante_table.c.Oyente_correo == correo,
            participante_table.c.Playlist_id == playlist
        )
        db.execute(delete_stmt)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204


"""Elimina a un usuario de participante de una playlist del usuario logueado"""
@playlist_bp.route("/expel-from-playlist", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def expel_from_playlist():
    data = request.get_json()
    if not data or "nombreUsuario" not in data or "playlist" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    nombreUsuario = data.get("nombreUsuario")
    playlist = data.get("playlist")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        if playlist_entry.Oyente_correo != correo:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        usuario_entry = db.execute(select(Usuario).where(Usuario.nombreUsuario == nombreUsuario)).scalar_one_or_none()
        if not usuario_entry:
            return jsonify({"error": "El usuario no existe."}), 404
        
        if usuario_entry not in playlist_entry.participantes:
            return jsonify({"error": "El usuario no participa en la playlist."}), 404
        
        playlist.participantes.remove(usuario_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204