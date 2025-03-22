from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from db.db import get_db
from db.models import *
from utils.decorators import roles_required, tokenVersion_required
import pytz

album_bp = Blueprint('album', __name__)


"""Devuelve informacion de un album"""
@album_bp.route("/get-datos-album", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente", "artista")
def get_datos_album():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta el id del álbum."}), 400

    with get_db() as db:     
        album = db.get(Album, id)
        if not album:
            return jsonify({"error": "El álbum no existe."}), 401
        canciones = [
            {
                "id": cancion.id,
                "fotoPortada": album.fotoPortada,
                "nombre": cancion.nombre,
                "duracion": cancion.duracion,
                "fechaPublicacion": cancion.fecha.date().isoformat(),
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
            "canciones": canciones
            }), 200
    
"""Crea un album del artista logueado con mínimo 1 canción"""
@album_bp.route("/create-album", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def create_album():
    data = request.get_json()

    nombre_album = data.get("nombre_album")
    foto_portada_url = data.get("fotoPortada")

    nombre_cancion = data.get("nombre_cancion")
    cancion_url = data.get("cancion")
    cancion_duracion = data.get("duracion")
    tags = data.get("tags")

    if not data or not nombre_album or not foto_portada_url or not nombre_cancion or not cancion_url or not cancion_duracion or len(tags) > 3 or len(tags) < 1:
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

        nueva_cancion = Cancion(
            nombre=nombre_cancion,
            duracion=cancion_duracion,
            audio=cancion_url,
            fecha=datetime.now(pytz.timezone('Europe/Madrid')),
            reproducciones=0,
            Album_id=nuevo_album.id,
            Artista_correo=correo_artista,
            puesto=0
        )
        db.add(nueva_cancion)

        for tag in tags:
            genero = db.query(GeneroMusical).filter_by(nombre=tag).first()
            nueva_cancion.generosMusicales.append(genero)

        db.commit()

    return jsonify({"message": "Álbum creado exitosamente."}), 201