import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Configura Cloudinary con las variables de entorno
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_NAME'),
  api_key = os.getenv('CLOUDINARY_KEY'),
  api_secret = os.getenv('CLOUDINARY_SECRET'),
  secure = True
)

#############################################

## UPLOAD ##
# Función para subir una imagen
def upload_image(image_path, name):
    try:
        response = cloudinary.uploader.upload(image_path, public_id=name, resource_type="image", folder="imagenes")
        return response.get("url")
    except Exception as e:
        return f"Error al subir la imagen: {e}"

# Función para subir una cancion
def upload_video(song_path, name):
    try:
        response = cloudinary.uploader.upload(song_path, public_id=name, resource_type="video", folder="canciones")
        return response.get("url")
    except Exception as e:
        return f"Error al subir la canción: {e}"
    
## GET ##
# Función para obtener una imagen por su nombre
def get_image_by_name(public_id):
    try:
        response = cloudinary.api.resource("imagenes/"+public_id)
        return response.get("url")
    except Exception as e:
        return f"Error al recuperar la imagen: {e}"

# Función para obtener una canción por su nombre
def get_song_by_name(public_id):
    try:
        response = cloudinary.api.resource("canciones/"+public_id, resource_type="video")
        return response.get("url")
    except Exception as e:
        return f"Error al recuperar la canción: {e}"
    
# Función para obtener un paquete cancion-imagen por sus nombres
def get_both_by_name(song_public_id, image_public_id):
    try:
        response = cloudinary.api.resource(song_public_id, resource_type="image")
        response2 = cloudinary.api.resource(image_public_id, resource_type="video")
        return response.get("url"), response2.get("url")
    except Exception as e:
        return f"Error al recuperar el paquete: {e}"
    
## DELETE ##
# Función para eliminar una imagen por su nombre
def delete_image_by_name(public_id):
    try:
        response = cloudinary.uploader.destroy("imagenes/"+public_id, resource_type="image")
        return response.get("result")
    except Exception as e:
        return f"Error al eliminar la imagen: {e}"
    
# Función para eliminar una canción por su nombre
def delete_song_by_name(public_id):
    try:
        response = cloudinary.uploader.destroy("canciones/"+public_id, resource_type="video")
        return response.get("result")
    except Exception as e:
        return f"Error al eliminar la canción: {e}"
