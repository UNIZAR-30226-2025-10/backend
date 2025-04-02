from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.models import Playlist, Oyente, Cancion, EsParteDePlaylist, Usuario, participante_table, invitado_table, Album, Artista
from db.db import get_db
from sqlalchemy import select, exists, delete, insert, and_
from utils.decorators import roles_required, tokenVersion_required
from datetime import datetime
import pytz
import cloudinary.uploader
import os

playlist_bp = Blueprint('playlist', __name__)


cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)


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
        
        if playlist_entry.privacidad and playlist_entry.Oyente_correo != correo:
            return jsonify({"error": "No tienes acceso a esta playlist."}), 403
 
        creador_entry = db.get(Oyente, playlist_entry.Oyente_correo)
        
        participantes = []
        participantes_correos = []
        for p in playlist_entry.participantes:
            participantes.append(p.nombreUsuario)
            participantes_correos.append(p.correo)

        canciones_stmt = select(Cancion, EsParteDePlaylist.fecha, Album.fotoPortada, Artista.nombreUsuario, Artista.nombreArtistico
            ).join(EsParteDePlaylist, EsParteDePlaylist.Cancion_id == Cancion.id
            ).join(Album, Album.id == Cancion.Album_id
            ).join(Artista, Artista.correo == Cancion.Artista_correo
            ).where(EsParteDePlaylist.Playlist_id == id)

        canciones_entry = db.execute(canciones_stmt).fetchall()

        duracion_total = sum(row[0].duracion for row in canciones_entry)

        stmt_fav = select(EsParteDePlaylist.Cancion_id).join(Playlist
            ).where(and_(
                Playlist.nombre == "Favoritos",
                Playlist.Oyente_correo == correo
            )
        )
        favoritos_set = {row[0] for row in db.execute(stmt_fav).all()}

        rol = ("creador" if creador_entry.correo == correo 
            else "participante" if correo in participantes_correos 
            else "nada")

        respuesta = {
            "playlist": {
                "nombrePlaylist": playlist_entry.nombre,
                "fotoPortada": playlist_entry.fotoPortada,
                "duracion": duracion_total,
                "creador": creador_entry.nombreUsuario if creador_entry else None,
                "colaboradores": participantes,
                "privacidad": playlist_entry.privacidad
            },
            "canciones": [
                {
                    "id": row[0].id,
                    "nombre": row[0].nombre,
                    "nombreArtisticoArtista": row[4],
                    "featuring": [f.nombreArtistico for f in row[0].featuring],
                    "reproducciones": row[0].reproducciones,
                    "duracion": row[0].duracion,
                    "fav": row[0].id in favoritos_set,
                    "nombreUsuarioArtista": row[3],
                    "fotoPortada": row[2],
                    "fecha": row[1].strftime("%d %m %Y"),
                    "album": row[0].Album_id
                }
                for row in canciones_entry
            ],
            "rol": rol
        }

    return jsonify(respuesta), 200

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
        if playlist.nombre == "Favoritos":
            return jsonify({"error": "La playlist 'Favoritos' no se puede modificar."}), 403

        # Cambiar privacidad y guardar cambios
        playlist.privacidad = privacidad
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500

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
        
        if playlist_entry.nombre == "Favoritos":
            return jsonify({"error": "La playlist 'Favoritos' no se puede compartir."}), 403

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

        if playlist.nombre == "Favoritos":
            return jsonify({"error": "La playlist 'Favoritos' no se puede modificar."}), 403

        playlist.nombre = nuevo_nombre

        if nueva_foto != playlist.fotoPortada:
            
            if playlist.fotoPortada != "DEFAULT":
                foto_antigua = playlist.fotoPortada
                public_id = foto_antigua.split('/')[-2] + '/' + foto_antigua.split('/')[-1].split('.')[0]

                try:
                    cloudinary.uploader.destroy(public_id, resource_type="image")
                except Exception as e:
                    return jsonify({"error": f"Error al eliminar la foto de perfil antigua de Cloudinary: {e}"}), 500
                
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
        
        if playlist_entry.nombre == "Favoritos":
            return jsonify({"error": "La playlist 'Favoritos' no se puede eliminar."}), 403

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
    if (nombre == "Favoritos"):
        return jsonify({"error": "El nombre 'Favoritos' no es valido."}), 403
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

"""Acepta una invitación del usuario logueado para participar en una playlist, haciendo que sea participante"""
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
            return jsonify({"error": "El usuario no ha sido invitado a participar en la playlist."}), 404

        db.execute(invitado_table.delete().where(
                (invitado_table.c.Oyente_correo == correo) & (invitado_table.c.Playlist_id == playlist_id)))
        db.execute(insert(participante_table).values(Oyente_correo=correo, Playlist_id=playlist_id))
        try:
            db.commit()              
        except Exception as e:
            return jsonify({"error": "Ha ocurrido un error inesperado.", "details": str(e)}), 500
    
    return jsonify(""), 201

"""Devuelve los datos de una playlist, en concreto la lista de canciones de la playlist ordenada según el criterio especificado"""
@playlist_bp.route("/get-invitaciones", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def get_invitaciones():
    correo = get_jwt_identity()

    with get_db() as db:
        oyente_entry = db.get(Oyente, correo)
        if not oyente_entry:
            return jsonify({"error": "Correo no existe."}), 401

        # Accede directamente a la relacion con playlists a las que esta invitado
        invitaciones = [
            {
                "id": p.id,
                "nombre": p.nombre,
                "nombreUsuario": p.oyente.nombreUsuario,
                "fotoPortada": p.fotoPortada
            } for p in oyente_entry.invitado]
    
    return jsonify({"invitaciones": invitaciones}), 200