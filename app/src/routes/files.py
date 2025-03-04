import os
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

## Función para obtener un paquete canción-imagen por sus nombres
def get_song_and_album(song_name, artist_mail):
    try:
        with get_db() as session:
            # Obtener la canción
            cancion = session.query(Cancion).filter_by(nombre=song_name, Artista_correo=artist_mail).first()

            if not cancion:
                return f"No se encontró la canción '{song_name}' del artista con correo '{artist_mail}'."

            # Acceder al álbum relacionado para obtener la fotoPortada
            album = session.query(Album).filter_by(
                nombre=cancion.Album_nombre,
                Artista_correo=cancion.Album_Artista_correo
            ).first()

            if not album:
                return f"No se encontró el álbum '{cancion.Album_nombre}' asociado a la canción."

            # Devolver los valores requeridos
            return {
                "audio": cancion.audio,
                "fotoPortada": album.fotoPortada
            }

    except Exception as e:
        return f"Error al encontrar la información en la base de datos: {e}"


## Función para obtener la lista de tags
def get_tags():
    try:
        with get_db() as session:
            tags = session.query(GeneroMusical).all()
            return [tag.nombre for tag in tags]
    except Exception as e:
        return f"Error al obtener los tags: {e}"
