import os
from flask import Blueprint, request, jsonify
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
import pytz
from db.models import *
from db.db import get_db
from utils.decorators import roles_required, tokenVersion_required
from flask_jwt_extended import jwt_required



#############################################################
## CONF ##
##########

files_bp = Blueprint('files', __name__)

# Configura Cloudinary con las variables de entorno QUITAR
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

#############################################################    
## GET ##
#########

"""Devuelve informacion de una cancion"""
@files_bp.route("/get-cancion", methods=["GET"])
@jwt_required()
@tokenVersion_required()
@roles_required("oyente","artista")
def get_cancion():
    id = request.args.get("id")
    if not id:
        return jsonify({"error": "Falta la cancion."}), 400
    
    with get_db() as db:
        # Obtener la canción
        cancion = db.get(Cancion, id)
        if not cancion:
            return jsonify({"error": "La canción no existe."}), 401
        
        return jsonify({
            "nombre":cancion.nombre,
            "artista":cancion.Artista_correo,
            "audio": cancion.audio,
            "fotoPortada": cancion.album.fotoPortada
            }), 200

@files_bp.route('/get-tags', methods=['GET'])
def get_tags():
    try:
        with get_db() as session:
            tags = session.query(GeneroMusical).all()
            return jsonify([tag.nombre for tag in tags]), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener los tags: {e}"}), 500
    
#############################################################    
## UPLOAD ##
############

"""Sube una nueva cancion"""
@files_bp.route("/upload-cancion", methods=["POST"])
@jwt_required()
@tokenVersion_required()
@roles_required("artista")
def upload_cancion():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos incorrectos."}), 400
    
    artista = data.get("artista")
    nombre = data.get("nombre")
    duracion = data.get("duracion")
    audio_url = data.get("audio_url")
    album_id = data.get("album_id")
    tags = data.get("tags")

    if not nombre or not artista or not album_id:
        return jsonify({
        "error": "Faltan datos de la cancióno.",
        "nombre": nombre,
        "artista": artista,
        "album_id": album_id
    }), 400
    
    # Funcion auxiliar para obtener el último puesto de un album
    def obtener_ultimo_puesto(session, album_id, artista_correo):
        # Obtener todas las canciones del álbum del artista
        canciones = session.query(Cancion).filter_by(Album_id=album_id, Artista_correo=artista_correo).all()
        
        if not canciones:
            return 0  # Si no hay canciones, devolver 0

        ultimo_puesto = max(cancion.puesto for cancion in canciones)
        return ultimo_puesto

    try:

        # Guardar la información de la canción en la base de datos
        with get_db() as db:
            nueva_cancion = Cancion(
                Artista_correo=artista,
                nombre=nombre,
                duracion=duracion,
                audio=audio_url,
                fecha=datetime.now(pytz.timezone('Europe/Madrid')),
                reproducciones=0,
                Album_id=album_id,
                puesto=obtener_ultimo_puesto(db, album_id, artista) + 1
            )

            db.add(nueva_cancion)

            # Añadir los tags
            for tag in tags:
                genero = db.get(GeneroMusical, tag)
                nueva_cancion.generosMusicales.append(genero)

            db.commit()

        return jsonify({"message": "Canción subida exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": f"Error al subir la canción: {e}"}), 500
    
