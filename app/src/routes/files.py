import os
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine
from contextlib import contextmanager
from datetime import date

from db.models import Base, Usuario, Artista, Album, Cancion, GeneroMusical, Oyente
from db.db import get_db
from utils.hash import hash

files_bp = Blueprint('files', __name__)

#############################################################
## CONF ##
##########

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Configura Cloudinary con las variables de entorno
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

#############################################################    
## GET ##
#########

@files_bp.route('/get-song-and-album', methods=['POST'])
def get_song_and_album():
    data = request.get_json()
    song_name = data.get('song_name')
    artist_mail = data.get('artist_mail')

    try:
        with get_db() as session:
            # Obtener la canción
            cancion = session.query(Cancion).filter_by(nombre=song_name, Artista_correo=artist_mail).first()

            if not cancion:
                return jsonify({"error": f"No se encontró la canción '{song_name}' del artista con correo '{artist_mail}'."}), 404

            # Acceder al álbum relacionado para obtener la fotoPortada
            album = session.query(Album).filter_by(
                nombre=cancion.Album_nombre,
                Artista_correo=cancion.Album_Artista_correo
            ).first()

            if not album:
                return jsonify({"error": f"No se encontró el álbum '{cancion.Album_nombre}' asociado a la canción."}), 404

            # Devolver los valores requeridos
            return jsonify({
                "audio": cancion.audio,
                "fotoPortada": album.fotoPortada
            }), 200

    except Exception as e:
        return jsonify({"error": f"Error al encontrar la información en la base de datos: {e}"}), 500


@files_bp.route('/get-tags', methods=['GET'])
def get_tags():
    try:
        with get_db() as session:
            tags = session.query(GeneroMusical).all()
            return jsonify([tag.nombre for tag in tags]), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener los tags: {e}"}), 500
