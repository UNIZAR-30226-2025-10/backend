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

# Función para subir una imagen
def upload_image(image_path, folder="images"):
    try:
        response = cloudinary.uploader.upload(image_path, folder=folder)
        return response.get("url")
    except Exception as e:
        return f"Error al subir la imagen: {e}"

# Función para subir un video
def upload_video(video_path, name, folder="canciones"):
    try:
        response = cloudinary.uploader.upload(video_path, public_id=name, resource_type="video", folder=folder)
        return response.get("url")
    except Exception as e:
        return f"Error al subir el video: {e}"

# Función para obtener una imagen por su nombre
def get_image_by_name(public_id):
    try:
        response = cloudinary.api.resource(public_id)
        return response.get("url")
    except Exception as e:
        return f"Error al recuperar la imagen: {e}"

# Función para obtener un video por su nombre
def get_video_by_name(public_id):
    try:
        response = cloudinary.api.resource(public_id, resource_type="video")
        return response.get("url")
    except Exception as e:
        return f"Error al recuperar el video: {e}"

