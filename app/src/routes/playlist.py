from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import Playlist, Oyente, Cancion, EsParteDePlaylist, Usuario, participante_table, invitado_table
from db.db import get_db
from sqlalchemy import select, exists, delete, insert
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
    if not id:
        return jsonify({"error": "Falta el ID de la playlist."}), 400
    correo = get_jwt_identity()

    with get_db() as db:
        playlist_entry = db.get(Playlist, id)

        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
 
        creador_entry = db.get(Oyente, playlist_entry.Oyente_correo)
        participantes = [p.nombreUsuario for p in playlist_entry.participantes]

        canciones_entry = [ep.cancion for ep in playlist_entry.esParteDePlaylist]

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
    if not data or "id" not in data or "privacidad" is None:
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
        if playlist_entry.Oyente_correo != correo and correo not in participantes:
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
        if playlist_entry.Oyente_correo != correo and correo not in participantes:
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
        
        playlist_entry.invitados.append(usuario_entry)
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
        
        playlist_entry.participantes.remove(usuario_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204

"""Cambia los datos de una playlist del usuario logueado"""
@playlist_bp.route("/change-playlist", methods=["PUT"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def change_playlist():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400

    correo = get_jwt_identity()
    playlist_id = data.get("id")
    nueva_foto = data.get("nuevaFoto")
    nuevo_nombre = data.get("nuevoNombre")

    if not playlist_id or not nueva_foto or not nuevo_nombre:
        return jsonify({"error": "Faltan campos en la peticion."}), 400 

    with get_db() as db:
        playlist = db.get(Playlist, playlist_id)

        if not playlist:
            return jsonify({"error": "Playlist no encontrada."}), 404

        if playlist.Oyente_correo != correo:
            return jsonify({"error": "No tienes permiso para modificar esta playlist."}), 403

        playlist.nombre = nuevo_nombre
        playlist.fotoPortada = nueva_foto

        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 200

"""Elimina una playlist del usuario logueado"""
@playlist_bp.route("/delete-playlist", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def delete_playlist():
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    playlist_id = data.get("id")

    with get_db() as db:
        playlist_entry = db.get(Playlist, playlist_id)
        if not playlist_entry:
            return jsonify({"error": "La playlist no existe."}), 404
        
        if correo != playlist_entry.Oyente_correo:
            return jsonify({"error": "La playlist solo puede ser eliminada por el creador."}), 403

        db.delete(playlist_entry)
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204

"""Crea una nueva playlist, vacía y sin participantes, para el usuario logueado"""
@playlist_bp.route("/create-playlist", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def create_playlist():
    data = request.get_json()
    if not data or "nombre" not in data or "fotoPortada" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    nombre = data.get("nombre")
    fotoPortada = data.get("fotoPortada")

    with get_db() as db:
        new_entry = Playlist(nombre=nombre, fotoPortada=fotoPortada, tipo="playlist", fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                              Oyente_correo=correo, privacidad=False)
        db.add(new_entry)
        try:
            db.commit()
            db.refresh(new_entry)

        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify({"id": new_entry.id}), 201

"""Elimina una invitación del usuario logueado para participar en una playlist"""
@playlist_bp.route("/delete-invitacion", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def delete_invitacion():
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    playlist_id = data.get("id")

    with get_db() as db:
        invitado_entry = db.query(invitado_table).filter_by(Oyente_correo=correo, Playlist_id=playlist_id).first()
        if not invitado_entry:
            return jsonify({"error": "El usuario no ha sido invitado a colaborar en la playlist."}), 404

        db.execute(invitado_table.delete().where(
                (invitado_table.c.Oyente_correo == correo) & (invitado_table.c.Playlist_id == playlist_id)))
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 204

"""Acepta una invitación del usuario logueado para participar en una playlist, haciendo que sea colaborador"""
@playlist_bp.route("/accept-invitacion", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def accept_invitacion():
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"error": "Faltan datos requeridos."}), 400

    correo = get_jwt_identity()
    playlist_id = data.get("id")

    with get_db() as db:
        invitado_entry = db.query(invitado_table).filter_by(Oyente_correo=correo, Playlist_id=playlist_id).first()
        if not invitado_entry:
            return jsonify({"error": "El usuario no ha sido invitado a colaborar en la playlist."}), 404

        db.execute(invitado_table.delete().where(
                (invitado_table.c.Oyente_correo == correo) & (invitado_table.c.Playlist_id == playlist_id)))
        db.execute(insert(participante_table).values(Oyente_correo=correo, Playlist_id=playlist_id))
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 201