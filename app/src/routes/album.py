from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
from utils.estadisticas import estadisticas_song
import pytz
import cloudinary.uploader
import os
from sqlalchemy import select, and_, func

album_bp = Blueprint('album', __name__)

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)


"""Devuelve informacion de un album"""
@album_bp.route("/get-datos-album", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_datos_album():
    id = request.args.get("id")
    correo = get_jwt_identity()
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:     
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 401
        
        stmt_fav = select(EsParteDePlaylist.Cancion_id).join(Playlist
            ).where(and_(
                Playlist.nombre == "Favoritos",
                Playlist.Oyente_correo == correo
            )
        )
        favoritos_set = {row[0] for row in db.execute(stmt_fav).all()}

        stmt = (
            select(func.count(EsParteDePlaylist.Cancion_id))
            .join(Playlist)
            .where(
                and_(
                    Playlist.nombre == "Favoritos",
                    EsParteDePlaylist.Cancion_id.in_([c.id for c in album.canciones])
                )
            )
        )

        total_favoritas = db.execute(stmt).scalar()

        canciones = [
            {
                "id": cancion.id,
                "fotoPortada": album.fotoPortada,
                "nombre": cancion.nombre,
                "duracion": cancion.duracion,
                "fechaPublicacion": cancion.fecha.date().isoformat(),
                "fav": cancion.id in favoritos_set,
                "featuring": [f.nombreArtistico for f in cancion.featuring],
                "puesto": cancion.puesto
            }
            for cancion in album.canciones
        ]

        return jsonify({
            "nombre": album.nombre,
            "fotoPortada": album.fotoPortada,
            "nombreArtisticoArtista": album.artista.nombreArtistico, 
            "fechaPublicacion": album.fecha.date().isoformat(),
            "duracion": sum(cancion.duracion for cancion in album.canciones),
            "canciones": canciones,
            "favs": total_favoritas
            }), 200
    

"""Crea un album del artista logueado con mínimo 1 canción"""
@album_bp.route("/create-album", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente, artista")
def create_album():
    data = request.get_json()

    nombre_album = data.get("nombre_album")
    foto_portada_url = data.get("fotoPortada")

    if not data or not nombre_album or not foto_portada_url:
        return jsonify({"error": "Faltan datos del álbum o la canción, o el álbum debe tener al menos una canción."}), 400

    with get_db() as db:
        correo_artista = get_jwt_identity()

        if not correo_artista:
            return jsonify({"error": "El artista no existe."}), 401

        nuevo_album = Album(
            nombre=nombre_album,
            fotoPortada=foto_portada_url,
            Artista_correo=correo_artista,
            fecha=datetime.now(pytz.timezone('Europe/Madrid')),
        )
        db.add(nuevo_album)
        db.commit()


    return jsonify({"message": "Álbum creado exitosamente."}), 201


"""Elimina un álbum por ID"""
@album_bp.route("/delete-album", methods=["DELETE"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def delete_album():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 401

        # Verificar que el artista logueado es el dueño del álbum
        correo_artista = get_jwt_identity()
        if album.Artista_correo != correo_artista:
            return jsonify({"error": "No tienes permiso para eliminar este álbum."}), 403

        db.delete(album)

        fotoPortada = album.fotoPortada
        public_id = fotoPortada.split('/')[-2] + '/' + fotoPortada.split('/')[-1].split('.')[0]

        try:
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception as e:
            return f"Error al eliminar el album de Cloudinary: {e}"
        
        for cancion in album.canciones:
            print(cancion.nombre)
            audio_url = cancion.audio
            public_id = audio_url.split('/')[-2] + '/' + audio_url.split('/')[-1].split('.')[0]

            try:
                cloudinary.uploader.destroy(public_id, resource_type="video")
            except Exception as e:
                return f"Error al eliminar la cancion de Cloudinary: {e}"
            
        db.commit()

    return jsonify({"message": "Álbum eliminado exitosamente."}), 200


"""Actualiza el nombre y foto de un album"""
@album_bp.route("/change-album", methods=["PATCH"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def change_album():
    data = request.get_json()
    album_id = request.args.get("id")

    if not album_id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    nombre = data.get("nombre")
    foto_portada = data.get("fotoPortada")

    if not nombre and not foto_portada:
        return jsonify({"error": "Faltan datos para actualizar el álbum."}), 400

    with get_db() as db:
        album = db.get(Album, album_id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 401

        correo_artista = get_jwt_identity()
        if album.Artista_correo != correo_artista:
            return jsonify({"error": "No tienes permiso para actualizar este álbum."}), 403

        if nombre:
            album.nombre = nombre
        if foto_portada:
            fotoPortadaAntigua = album.fotoPortada
            public_id = fotoPortadaAntigua.split('/')[-2] + '/' + fotoPortadaAntigua.split('/')[-1].split('.')[0]

            try:
                cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception as e:
                return f"Error al eliminar el album de Cloudinary: {e}"
            
            album.fotoPortada = foto_portada

        db.commit()

    return jsonify({"message": "Álbum actualizado exitosamente."}), 200


"""Devuelve los oyentes que han dado me gusta a una canción del álbum para su artista"""
@album_bp.route("/get-estadisticas-album-favs", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_estadisticas_album_favs():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:     
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 404
        
        correo_artista = get_jwt_identity()
        if album.Artista_correo != correo_artista:
            return jsonify({"error": "No tienes permiso para consultar las estadísticas de este álbum."}), 403

        personas_fav = []
        for cancion in album.canciones:
            stmt_likes = (
                select(Oyente)
                .join(Playlist, Playlist.Oyente_correo == Oyente.correo)
                .join(EsParteDePlaylist, EsParteDePlaylist.Playlist_id == Playlist.id)
                .where(
                    Playlist.nombre == "Favoritos",
                    EsParteDePlaylist.Cancion_id == cancion.id
                )
                .distinct()
            )
            personas_fav.extend([row[0] for row in db.execute(stmt_likes).all()])

        oyentes_favs = [
            {
                "nombreUsuario": oyente.nombreUsuario,
                "fotoPerfil": oyente.fotoPerfil
            }
            for oyente in personas_fav
        ]
        
    return jsonify({"oyentes_favs": oyentes_favs}), 200
    

"""Devuelve las estadísticas de un album para su artista"""
@album_bp.route("/get-estadisticas-album", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def get_estadisticas_album():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:     
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 404
        
        correo_artista = get_jwt_identity()
        if album.Artista_correo != correo_artista:
            return jsonify({"error": "No tienes permiso para consultar las estadísticas de este álbum."}), 403
        
        total_reproducciones = 0
        total_nPlaylists = 0
        total_favs = 0

        canciones = []
        for cancion in album.canciones:
            n_playlists, favs = estadisticas_song(cancion, db) 
            total_nPlaylists += n_playlists
            total_favs += favs
            total_reproducciones += cancion.reproducciones

            canciones.append({
                "id": cancion.id,
                "fotoPortada": album.fotoPortada,
                "nombre": cancion.nombre,
                "duracion": cancion.duracion,
                "fechaPublicacion": cancion.fecha.date().isoformat(),
                "reproducciones": cancion.reproducciones,
                "puesto": cancion.puesto,
                "nPlaylists": n_playlists,
                "favs": favs
            })

        return jsonify({
            "nombre": album.nombre,
            "fotoPortada": album.fotoPortada,
            "nombreArtisticoArtista": album.artista.nombreArtistico,
            "fechaPublicacion": album.fecha.date().isoformat(),
            "duracion": sum(c.duracion for c in album.canciones),
            "reproducciones": total_reproducciones,
            "nPlaylists": total_nPlaylists,
            "favs": total_favs,
            "canciones": canciones
        }), 200
    